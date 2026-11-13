package urnettools

import (
	"errors"
	"io/fs"
	"os"
	"os/user"
	"strings"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

// OpenBSD ps ucomm identifies a process by name, not its executable path.
// A standard install path is only an on-disk candidate, not proof of the
// running image. Never derive a path from process arguments.
func discoverProcesses() []Provider {
	out, err := execWithTimeout(5*time.Second, "ps", "-A", "-o", "pid=,uid=,ucomm=")
	if err != nil {
		return nil
	}
	managedPID := openbsdServicePID()
	var providers []Provider
	for _, row := range parseOpenBSDProcesses(string(out)) {
		p := Provider{PID: row.pid, Running: true}
		if managedPID > 0 && row.pid == managedPID {
			p.Supervisor = "openbsd-rcd"
		}
		if u, err := user.LookupId(row.uid); err == nil {
			p.User = u.Username
			p.StateDir = resolveDiscoveredStateDir(u.HomeDir, "")
			if p.StateDir != "" {
				p.StateHome = u.HomeDir
				h, err := openStateDirIn(p.StateHome, p.StateDir)
				if err != nil {
					p.IdentityRestricted = errors.Is(err, fs.ErrPermission)
					p.StateDir = ""
				} else {
					raw, err := h.readFile("jwt", maxJWTBytes)
					h.Close()
					p.IdentityRestricted = errors.Is(err, fs.ErrPermission)
					if err == nil {
						p.Network, p.NetworkID, p.JWTExpires, _ = decodeJWTBytes(raw)
					}
				}
			}
		}
		providers = append(providers, p)
	}
	// Only an rc.d-managed process can be associated with the installed
	// binary; a matching ps command name alone is not evidence of its path.
	binary := installedOpenBSDProvider()
	if binary != "" && openbsdCheckScript(openbsdRcScriptPath(bsdRcServiceName(binary)), binary) == nil {
		for i := range providers {
			if providers[i].Supervisor == "openbsd-rcd" && providers[i].PID == managedPID {
				providers[i].Binary = binary
			}
		}
	}
	return providers
}

// openbsdLibexecProviderPath is the only binary path accepted. urnet-tools
// often runs as root, so a binary in a user-writable home must never be
// resolved and executed.
var openbsdLibexecProviderPath = "/usr/local/libexec/urnetwork-provider/bin/urnetwork"

// openbsdProviderOwnerUID is the uid that must own the provider binary. It is
// a var so tests, which cannot create root-owned files, can override it.
var openbsdProviderOwnerUID uint32 = 0

func installedOpenBSDProvider() string {
	path := openbsdLibexecProviderPath
	info, err := os.Stat(path)
	if err != nil || !info.Mode().IsRegular() {
		return ""
	}
	// Must be owned by root: a binary owned by another user could be swapped
	// by that user and then executed by root.
	if st, ok := info.Sys().(*syscall.Stat_t); !ok || st.Uid != openbsdProviderOwnerUID {
		return ""
	}
	// Must be executable by others and not writable by group or others.
	perm := info.Mode().Perm()
	if perm&0o001 == 0 || perm&0o022 != 0 {
		return ""
	}
	if unix.Access(path, unix.X_OK) == nil {
		return path
	}
	return ""
}

// stateDirIsSymlink reports whether dir itself is a symbolic link.
func stateDirIsSymlink(dir string) bool {
	if dir == "" {
		return false
	}
	fi, err := os.Lstat(dir)
	return err == nil && fi.Mode()&os.ModeSymlink != 0
}

func discoverStopped(running []Provider) []Provider {
	for _, p := range running {
		if p.Supervisor == "openbsd-rcd" {
			return nil
		}
	}
	bin := installedOpenBSDProvider()
	if bin == "" || openbsdCheckScript(openbsdRcScriptPath("urnetwork"), bin) != nil {
		return nil
	}
	data, err := os.ReadFile(openbsdRcScriptPath("urnetwork"))
	if err != nil {
		return nil
	}
	var name string
	for _, line := range strings.Split(string(data), "\n") {
		if v, ok := strings.CutPrefix(line, `daemon_user="`); ok {
			name, _ = strings.CutSuffix(v, `"`)
			break
		}
	}
	if name == "" || name == "root" {
		return nil
	}
	for i, r := range name {
		if !(r >= 'a' && r <= 'z' || r == '_' || i > 0 && (r >= '0' && r <= '9' || r == '-')) {
			return nil
		}
	}
	u, err := user.Lookup(name)
	if err != nil {
		return nil
	}
	dir := resolveDiscoveredStateDir(u.HomeDir, "")
	if dir == "" || stateDirIsSymlink(dir) {
		return nil
	}
	p := Provider{User: u.Username, StateDir: dir, StateHome: u.HomeDir, Binary: bin, Supervisor: "openbsd-rcd"}
	h, err := openStateDirIn(p.StateHome, p.StateDir)
	if err == nil {
		raw, readErr := h.readFile("jwt", maxJWTBytes)
		h.Close()
		err = readErr
		if err == nil {
			p.Network, p.NetworkID, p.JWTExpires, _ = decodeJWTBytes(raw)
		}
	}
	p.IdentityRestricted = errors.Is(err, fs.ErrPermission)
	return []Provider{p}
}

func currentUserName() string {
	if u, err := user.Current(); err == nil {
		return u.Username
	}
	return ""
}

func narrowToAccessible(providers []Provider) []Provider {
	name := currentUserName()
	var out []Provider
	for _, p := range providers {
		if name != "" && p.User == name {
			out = append(out, p)
		}
	}
	return out
}

func platformIsPrivileged() bool { return os.Geteuid() == 0 }
