package urnettools

import (
	"strings"
	"testing"
)

func TestExtenderHelpAndAboutDescribeManualRequirements(t *testing.T) {
	help := newExtenderCmd().Long
	for _, want := range []string{"UDP 53 is optional and user-managed", "FreeBSD extender setup is untested this release", "only prints manual instructions"} {
		if !strings.Contains(help, want) {
			t.Errorf("help missing %q", want)
		}
	}
	for _, want := range []string{"port or its firewall rules; free and open it yourself", "untested this release", "-p 53:53/udp", "Compose networks need IPv6 enabled", "hot swap can race", "Docker log follower"} {
		if !strings.Contains(extenderAboutText, want) {
			t.Errorf("about missing %q", want)
		}
	}
}
