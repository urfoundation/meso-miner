package urnettools

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestOpenBSDInstallServicePreservesAccount(t *testing.T) {
	skipWithoutPOSIXShell(t)
	b, err := os.ReadFile("../../scripts/Provider_Install_OpenBSD.sh")
	if err != nil {
		t.Fatal(err)
	}
	fn := extractShellFunc(t, string(b), "do_install_service")
	for _, tc := range []struct{ existing, want string }{{"alice", "alice"}, {"", "bob"}} {
		t.Run(tc.want, func(t *testing.T) {
			script := `id() { printf '0\n'; }
resolve_service_user() { printf 'bob\n'; }
write_rc_script() { printf '%s\n' "$1"; }
rcctl() { :; }
pr_info() { :; }
pr_err() { :; }
` + fn + "\nservice_user='" + tc.existing + "'\nrc_script='" + filepath.Join(t.TempDir(), "urnetwork") + "'\nservice_name=urnetwork\ndo_install_service\n"
			out, err := exec.Command("/bin/sh", "-c", script).CombinedOutput()
			if err != nil || strings.TrimSpace(string(out)) != tc.want {
				t.Fatalf("got %q, err %v; want %q", out, err, tc.want)
			}
		})
	}
}

func TestBSDCronSelectorPinsProvider(t *testing.T) {
	for _, tc := range []struct {
		p           Provider
		flag, value string
	}{
		{Provider{User: "alice", StateDir: "/home/alice/.urnetwork"}, "--state-dir", "/home/alice/.urnetwork"},
		{Provider{User: "bob"}, "--user", "bob"},
	} {
		selector, err := bsdUpdateSelector(tc.p)
		if err != nil || len(selector) != 2 || selector[0] != tc.flag || selector[1] != tc.value {
			t.Fatalf("selector %v: %v", selector, err)
		}
		line, err := bsdUpdateCronLine("/bin/tool", "/logs", "weekly", selector)
		if err != nil || !strings.Contains(line, "'"+tc.flag+"' '"+tc.value+"'") {
			t.Fatalf("line %q: %v", line, err)
		}
	}
	if _, err := bsdUpdateSelector(Provider{}); err == nil {
		t.Fatal("missing selector accepted")
	}
}
