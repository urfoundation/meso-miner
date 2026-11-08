package urnettools

import (
	"bytes"
	"os"
	"strings"
	"testing"
)

func TestFreeBSDSetupIsAlwaysPrintOnly(t *testing.T) {
	for _, root := range []bool{false, true} {
		for _, dry := range []bool{false, true} {
			var out bytes.Buffer
			called := false
			cfg := &SystemPlatformConfigurer{PlatformName: "freebsd", ExecCmd: func(string, ...string) ([]byte, error) { called = true; return nil, nil }, WriteFile: func(string, []byte, os.FileMode) error { called = true; return nil }}
			checker := &PortChecker{Platform: "freebsd", ExecCmd: func(string, ...string) ([]byte, error) { return nil, nil }}
			fw := &FirewallManager{Platform: "freebsd", LookPath: func(string) (string, error) { return "", os.ErrNotExist }, ExecCmd: func(string, ...string) ([]byte, error) { called = true; return nil, nil }}
			err := RunExtenderSetup(ExtenderSetupOptions{Platform: "freebsd", PlatformCfg: cfg, PortChecker: checker, FirewallMgr: fw, Stdout: &out, Stderr: &out, IsRoot: func() bool { return root }, DryRun: dry, Yes: true, ElevateFunc: func([]string) error { called = true; return nil }})
			if err != nil {
				t.Fatalf("root=%v dry=%v: %v", root, dry, err)
			}
			if called {
				t.Fatalf("root=%v dry=%v: attempted a change or elevation", root, dry)
			}
			for _, want := range []string{"untested this release", "sysctl -n net.inet.ip.portrange.reservedhigh > /root/urnetwork-extender-reservedhigh.before", "sysctl net.inet.ip.portrange.reservedhigh=0", "cp -p /etc/sysctl.conf /root/urnetwork-extender-sysctl.conf.before", `printf '\nnet.inet.ip.portrange.reservedhigh=0\n' >> /etc/sysctl.conf`, `sysctl net.inet.ip.portrange.reservedhigh="$(cat /root/urnetwork-extender-reservedhigh.before)"`, "cp -p /root/urnetwork-extender-sysctl.conf.before /etc/sysctl.conf", "Undo", "firewall"} {
				if !strings.Contains(out.String(), want) {
					t.Errorf("root=%v dry=%v: missing %q in %q", root, dry, want, out.String())
				}
			}
		}
	}
}

func TestFreeBSDPlatformApplyCannotWrite(t *testing.T) {
	called := false
	cfg := &SystemPlatformConfigurer{PlatformName: "freebsd", ExecCmd: func(string, ...string) ([]byte, error) { called = true; return nil, nil }, WriteFile: func(string, []byte, os.FileMode) error { called = true; return nil }, ReadFile: func(string) ([]byte, error) { called = true; return nil, nil }}
	applied, _, _ := cfg.ApplyRequirement("", "provider")
	if called || applied {
		t.Fatalf("called=%v applied=%v", called, applied)
	}
}
