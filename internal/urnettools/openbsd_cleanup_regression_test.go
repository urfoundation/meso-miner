package urnettools

import (
	"errors"
	"os"
	"testing"
)

func TestOpenBSDCleanupMissingScriptRegression(t *testing.T) {
	cronErr := errors.New("cron failure")
	for _, tc := range []struct {
		name                        string
		scriptErr, cronErr, wantErr error
		handled                     bool
		calls                       int
	}{
		{"missing", os.ErrNotExist, nil, nil, true, 1},
		{"cron failure", os.ErrNotExist, cronErr, cronErr, true, 1},
		{"permission", os.ErrPermission, nil, os.ErrPermission, false, 0},
		{"valid", nil, nil, nil, false, 0},
	} {
		t.Run(tc.name, func(t *testing.T) {
			calls := 0
			handled, err := openbsdCleanupMissingScript(tc.scriptErr, func() error { calls++; return tc.cronErr })
			if handled != tc.handled || !errors.Is(err, tc.wantErr) || calls != tc.calls {
				t.Fatalf("handled=%v err=%v calls=%d", handled, err, calls)
			}
		})
	}
}
