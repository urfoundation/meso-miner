#!/usr/bin/env python3
"""Exercise privileged installer helpers with shell stubs."""
import fcntl
import os
from pathlib import Path
import pty
import struct
import subprocess
import tempfile
import termios
import unittest

INSTALLER = Path(__file__).resolve().parent / "Provider_Install_Linux.sh"


def function(name):
    script = INSTALLER.read_text()
    marker = name + ("() {\n" if name == "firewall_hint" else " ()\n{\n")
    start = script.index(marker)
    if name == "openrc_finalize_root_paths":
        return script[start:script.index("\n# install_openrc_units:", start)]
    return script[start:script.index("\n}\n", start) + 3]


class PrivilegedSteps(unittest.TestCase):
    def test_linger_failure_prints_error_and_recovery(self):
        harness = '''
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { printf 'stub loginctl failure\\n' >&2; return 1; }
''' + function("installer_enable_linger") + '\ninstaller_enable_linger alice\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stub loginctl failure", result.stderr)
        self.assertIn("sudo loginctl enable-linger alice", result.stdout)
        self.assertIn("may stop on logout", result.stdout)

    def test_tool_copy_failure_preserves_backup_and_reports_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "bin/urnet-tools").write_text("old")
            source = root / "download"
            source.write_text("new")
            harness = '''
install_path="$1"
pr_err() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
cp() { printf 'copy denied\\n' >&2; return 1; }
''' + function("install_downloaded_tool") + '\ninstall_downloaded_tool "$1/download"\n'
            result = subprocess.run(["sh", "-c", harness, "sh", tmp], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((root / "bin/urnet-tools.old").read_text(), "old")
            self.assertTrue(source.exists())
            self.assertIn("copy denied", result.stderr)
            self.assertIn("provider binary is installed", result.stdout)
            self.assertIn("service may be stopped", result.stdout)
            self.assertIn("sudo cp", result.stdout)

    def test_firewall_queries_expose_failure_and_recovery(self):
        for name, expected in (("firewall-cmd", "sudo firewall-cmd --state"), ("nft", "sudo nft list tables")):
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    stub = Path(tmp) / name
                    stub.write_text("#!/bin/sh\nprintf 'query denied\\n' >&2\nexit 1\n")
                    stub.chmod(0o755)
                    harness = function("firewall_hint") + '\nfirewall_hint 443 tcp\n'
                    result = subprocess.run(["/bin/sh", "-c", harness], env={"PATH": tmp}, text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("query denied", result.stderr)
                    self.assertIn(expected, result.stderr)

    def test_sysctl_config_failure_does_not_claim_success(self):
        harness = '''
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
sysctl() { printf 'failed %s\\n' "$*" >&2; return 1; }
''' + function("installer_apply_sysctl_config") + '\ninstaller_apply_sysctl_config /etc/sysctl.d/99-urnetwork.conf\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed -p", result.stderr)
        self.assertIn("failed --system", result.stderr)
        self.assertIn("sudo sysctl -p '/etc/sysctl.d/99-urnetwork.conf'", result.stdout)
        self.assertNotIn("settings applied", result.stdout)

    def test_immediate_sysctls_report_each_failure_and_continue(self):
        harness = '''
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
sysctl() { printf 'denied %s\\n' "$2" >&2; return 1; }
''' + function("installer_apply_immediate_sysctls") + '\ninstaller_apply_immediate_sysctls\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        for setting in ("fs.inotify.max_user_watches=524288", "fs.inotify.max_user_instances=512", "fs.file-max=2097152"):
            self.assertIn("sudo sysctl -w " + setting, result.stdout)
            self.assertIn("denied " + setting, result.stderr)

    def test_openrc_staging_chown_failure_never_reports_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bin").mkdir()
            (root / "bin/urnet-tools").write_text("stub")
            harness = '''
install_path="$1"; openrc_root_tool_dir="$1/stage"; openrc_root_tool_path="$1/stage/urnet-tools"
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
id() { printf '0\\n'; }
mkdir() { :; }
chown() { printf 'chown denied\\n' >&2; return 1; }
cp() { printf 'unexpected copy\\n' >&2; return 1; }
''' + function("openrc_stage_root_owned_tool") + '\nopenrc_stage_root_owned_tool\n'
            result = subprocess.run(["sh", "-c", harness, "sh", tmp], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("chown denied", result.stderr)
            self.assertNotIn("unexpected copy", result.stderr)
            self.assertIn("sudo chown root:root", result.stdout)

    def test_openrc_log_chown_failure_prints_recovery(self):
        harness = '''
install_path=/stub; openrc_home=/stub; openrc_user=alice
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_err() { printf "$@\\n"; }
pr_info() { printf "$@\\n"; }
find() { :; }; mkdir() { :; }; chmod() { :; }; touch() { :; }; tee() { :; }
chown() { case "$*" in *urnetwork.log*) printf 'log denied\\n' >&2; return 1 ;; esac; }
openrc_stage_root_owned_tool() { return 1; }
''' + function("openrc_finalize_root_paths") + '\nopenrc_finalize_root_paths\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertIn("log denied", result.stderr)
        self.assertIn("sudo chown 'alice' /var/log/urnetwork.log /var/log/urnetwork.err", result.stdout)
        self.assertNotIn("Staged the auto-update tool", result.stdout)

    def test_linger_success_is_silent(self):
        harness = '''
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { return 0; }
''' + function("installer_enable_linger") + '\ninstaller_enable_linger alice\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def _run_logo(self, columns, force=False, use_tty=True):
        env = os.environ.copy()
        env["COLUMNS"] = columns
        env["FORCE"] = "1" if force else "0"
        script = '\n'.join((function("install_logo"),
                           function("install_logo_columns"),
                           "install_logo"))
        if not use_tty:
            result = subprocess.run(["sh", "-c", script], env=env, text=True,
                                    capture_output=True)
            return result.stdout
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, int(columns), 0, 0))
        proc = subprocess.Popen(["sh", "-c", script], stdout=slave, stderr=slave,
                                stdin=subprocess.DEVNULL, env=env)
        os.close(slave)
        chunks = []
        while True:
            try:
                data = os.read(master, 4096)
                if not data:
                    break
                chunks.append(data)
            except OSError:
                break
        proc.wait()
        os.close(master)
        return b"".join(chunks).decode(errors="replace").replace("\r\n", "\n")

    def test_logo_printed_on_a_wide_terminal(self):
        out = self._run_logo("120")
        self.assertIn("\u2597\u259f\u2588\u2588\u2588\u2584", out)
        self.assertNotIn("\x1b[", out, "the wordmark carries no color codes")
        rows = [line for line in out.splitlines() if line.strip()]
        self.assertEqual(len(rows), 6, f"wordmark rows: {rows}")

    def test_logo_hidden_below_its_width(self):
        out = self._run_logo("81")
        self.assertNotIn("\u2588", out)

    def test_logo_hidden_when_unattended(self):
        out = self._run_logo("120", force=True)
        self.assertNotIn("\u2588", out)

    def test_logo_hidden_when_output_is_piped(self):
        out = self._run_logo("120", use_tty=False)
        self.assertNotIn("\u2588", out)


if __name__ == "__main__":
    unittest.main()
