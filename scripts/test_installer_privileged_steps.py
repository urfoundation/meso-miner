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
    def test_auto_start_refuses_when_linger_is_off(self):
        harness = r"""
pr_info() { :; }
pr_err() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
id() { echo alice; }
loginctl() { echo no; }
systemctl() { echo "$*" >> "$LOG"; return 1; }
""" + function("toggle_auto_start") + "\ntoggle_auto_start on\n"
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "calls"
            result = subprocess.run(["sh", "-c", harness], env=dict(os.environ, LOG=str(log)), text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("linger is not enabled for alice; run sudo loginctl enable-linger alice before enabling this unit", result.stdout)
            self.assertFalse(log.exists() and "--user enable urnetwork.service" in log.read_text())

    def test_initial_linger_attempt_does_not_prompt(self):
        harness = r"""
FORCE=1
pr_info() { :; }
pr_warn() { :; }
loginctl() { case "$1" in show-user) echo no;; *) echo "$*";; esac; }
""" + function("installer_enable_linger") + "\ninstaller_enable_linger alice install || :\n"
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertIn("--no-ask-password", result.stdout)

    def test_linger_interactive_answers(self):
        for answer in ("y", "n", ""):
            with self.subTest(answer=answer), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "answer").write_text(answer + "\n")
                harness = r"""
linger_tty="$ROOT/answer"
pr_info() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
loginctl() { case "$1" in show-user) [ -f "$ROOT/state" ] && echo yes || echo no;; enable-linger) echo user >> "$ROOT/log"; return 1;; esac; }
sudo() { echo "sudo $*" >> "$ROOT/log"; touch "$ROOT/state"; }
""" + function("installer_linger_tty_askable") + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install || :; installer_linger_summary alice\n"
                master, slave = pty.openpty()
                try:
                    result = subprocess.run(["sh", "-c", harness], stdin=slave, stdout=slave, stderr=slave, env=dict(os.environ, ROOT=tmp), timeout=10)
                    os.close(slave)
                    slave = -1
                    output = b""
                    while True:
                        try:
                            chunk = os.read(master, 4096)
                        except OSError:
                            break
                        if not chunk:
                            break
                        output += chunk
                finally:
                    if slave >= 0:
                        os.close(slave)
                    os.close(master)
                text = output.decode()
                self.assertEqual(result.returncode, 0, text)
                self.assertIn("Run it now? [y/N]", text)
                log = (root / "log").read_text().splitlines()
                if answer == "y":
                    self.assertEqual(log, ["user", "sudo loginctl enable-linger alice"])
                    self.assertIn("lingering is on for alice", text)
                else:
                    self.assertEqual(log, ["user"])
                    self.assertIn("WARNING: lingering is OFF for alice", text)

    def test_linger_piped_stdin_with_terminal_asks_and_obeys(self):
        for answer, wants_sudo in ((b"y\n", True), (b"n\n", False)):
            with self.subTest(answer=answer.decode().strip()), tempfile.TemporaryDirectory() as tmp:
                rc, out, log = self._run_linger_piped_with_terminal(tmp, answer)
                self.assertIn("Run it now? [y/N]", out)
                if wants_sudo:
                    self.assertEqual(log, ["user", "sudo loginctl enable-linger alice"], out)
                    self.assertIn("lingering is on for alice", out)
                else:
                    self.assertEqual(log, ["user"], out)
                    self.assertIn("WARNING: lingering is OFF for alice", out)

    def test_linger_piped_stdin_without_terminal_never_asks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = self._linger_stubs() + function("installer_linger_tty_askable") + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install || :; installer_linger_summary alice\n"
            result = subprocess.run(
                ["sh", "-c", harness],
                input="y\n",
                text=True,
                capture_output=True,
                preexec_fn=os.setsid,
                env=self._linger_env(tmp),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("Run it now?", result.stdout)
            self.assertEqual((root / "log").read_text().splitlines(), ["user"])
            self.assertIn("WARNING: lingering is OFF for alice", result.stdout)

    def _linger_stubs(self):
        return r"""
pr_info() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
loginctl() { case "$1" in show-user) [ -f "$ROOT/state" ] && echo yes || echo no;; enable-linger) echo user >> "$ROOT/log"; return 1;; esac; }
sudo() { echo "sudo $*" >> "$ROOT/log"; touch "$ROOT/state"; }
"""

    def _linger_env(self, tmp):
        env = {k: v for k, v in os.environ.items() if k not in ("FORCE", "URNET_INSTALL_LINGER")}
        env["ROOT"] = tmp
        return env

    def _run_linger_piped_with_terminal(self, tmp, answer: bytes):
        """Runs the lingering fix with piped stdin, a real controlling pty, and
        the answer typed on that pty, which is the curl | sh case."""
        root = Path(tmp)
        master, slave = pty.openpty()
        pipe_r, pipe_w = os.pipe()
        harness = self._linger_stubs() + function("installer_linger_tty_askable") + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install || :; installer_linger_summary alice\n"

        def preexec():
            os.setsid()
            fcntl.ioctl(slave, termios.TIOCSCTTY, 0)

        proc = subprocess.Popen(
            ["sh", "-c", harness],
            stdin=pipe_r,
            stdout=slave,
            stderr=slave,
            preexec_fn=preexec,
            close_fds=False,
            env=self._linger_env(tmp),
        )
        os.close(slave)
        os.close(pipe_r)
        os.write(pipe_w, b"piped stdin payload\n")
        os.close(pipe_w)
        os.write(master, answer)
        chunks = []
        while True:
            try:
                data = os.read(master, 1024)
                if not data:
                    break
                chunks.append(data)
            except OSError:
                break
        proc.wait()
        os.close(master)
        out = b"".join(chunks).decode(errors="replace").replace("\r\n", "\n")
        log = (root / "log").read_text().splitlines() if (root / "log").exists() else []
        return proc.returncode, out, log

    def test_linger_current_version_rerun_reports_the_summary(self):
        for state, want, unexpected in (
            ("no", "WARNING: lingering is OFF", "Systemd lingering is on"),
            ("yes", "Systemd lingering is on", "WARNING:"),
        ):
            with self.subTest(state=state):
                harness = '''
has_systemd=1
STATE_ONLY=1
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { case "$1" in show-user) echo "$LINGER_STATE";; *) echo ENABLE_CALLED;; esac; }
sudo() { echo SUDO_CALLED; }
''' + function("installer_linger_summary") + function("installer_linger_final_check") + '\ninstaller_linger_final_check\nexit $?\n'
                result = subprocess.run(["sh", "-c", harness], env=dict(os.environ, LINGER_STATE=state), text=True, capture_output=True)
                # The rerun keeps the exit status it had, and it never prompts,
                # never runs sudo and never changes the setting.
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(want, result.stdout)
                self.assertNotIn(unexpected, result.stdout)
                self.assertNotIn("SUDO_CALLED", result.stdout)
                self.assertNotIn("ENABLE_CALLED", result.stdout)

    def test_linger_final_check_uses_service_account(self):
        harness = """
has_systemd=1
logname() { echo login-user; }
id() { echo service-user; }
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { echo no; }
""" + function("installer_linger_summary") + function("installer_linger_final_check") + "\ninstaller_linger_final_check\n"
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertIn("lingering is OFF for service-user", result.stdout)
        self.assertNotIn("login-user", result.stdout)

    def test_linger_current_version_rerun_without_loginctl_or_systemd(self):
        harness = '''
has_systemd=1
command() { if [ "$1" = -v ] && [ "$2" = loginctl ]; then return 1; fi; builtin command "$@"; }
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
''' + function("installer_linger_summary") + function("installer_linger_final_check") + '\ninstaller_linger_final_check\nexit $?\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARNING: lingering is OFF", result.stdout)

        # No systemd means lingering does not apply, so a rerun says nothing.
        harness = '''
has_systemd=0
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { echo no; }
''' + function("installer_linger_summary") + function("installer_linger_final_check") + '\ninstaller_linger_final_check\nexit $?\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("lingering", result.stdout)

    def test_linger_current_version_exits_run_the_check(self):
        lines = INSTALLER.read_text().splitlines()
        calls = [i for i, line in enumerate(lines) if line.strip() == "installer_linger_final_check"]
        self.assertEqual(len(calls), 3, f"expected the check before each of the three no-op exits, found {len(calls)}")
        for i in calls:
            self.assertEqual(lines[i + 1].strip(), "exit 0", f"line {i + 2} does not exit after the check")

    def test_linger_without_sudo_gives_root_command(self):
        harness = r"""
command() { if [ "$1" = -v ] && [ "$2" = sudo ]; then return 1; fi; builtin command "$@"; }
pr_info() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\n" "$@"; }
loginctl() { [ "$1" = show-user ] && { echo no; return 0; }; return 1; }
""" + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install || :; installer_linger_summary alice\n"
        result = subprocess.run(["bash", "-c", harness], text=True, capture_output=True)
        self.assertIn("Run as root: loginctl enable-linger alice", result.stdout)
        self.assertIn("WARNING: lingering is OFF for alice", result.stdout)
        self.assertNotIn("Run it now?", result.stdout)

    def test_linger_already_enabled_is_not_changed(self):
        harness = """
pr_info() { printf '%s\\n' "$*"; }
pr_warn() { printf '%s\\n' "$*"; }
loginctl() { case "$1" in show-user) printf 'yes\\n';; *) echo ENABLE_CALLED;; esac; }
""" + function("installer_enable_linger") + "\ninstaller_enable_linger alice\n"
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("ENABLE_CALLED", result.stdout)
        self.assertIn("already enabled", result.stdout)

    def test_linger_noninteractive_and_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "loginctl").write_text("#!/bin/sh\ncase \"$1\" in show-user) [ -f \"$STATE\" ] && echo yes || echo no;; enable-linger) echo user >> \"$LOG\"; exit 1;; esac\n")
            (root / "sudo").write_text("#!/bin/sh\necho \"$*\" >> \"$LOG\"\n[ \"$1\" = -n ] && touch \"$STATE\"\n")
            for f in root.iterdir(): f.chmod(0o755)
            # The opt-in variable is set only for the opt-in case, so a runner
            # that exports it cannot change the default path.
            env = {k: v for k, v in os.environ.items() if k != "URNET_INSTALL_LINGER"}
            env.update(PATH=tmp + os.pathsep + os.environ["PATH"], LOG=str(root / "log"), STATE=str(root / "state"))
            harness = """FORCE=1
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
""" + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install || :; installer_linger_summary alice\n"
            for opt in (False, True):
                env.pop("URNET_INSTALL_LINGER", None)
                if opt: env["URNET_INSTALL_LINGER"] = "sudo"
                result = subprocess.run(["sh", "-c", harness], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0)
                log = (root / "log").read_text()
                if opt:
                    self.assertIn("-n loginctl enable-linger alice", log)
                    self.assertIn("lingering is on for alice", result.stdout)
                    self.assertNotIn("WARNING:", result.stdout)
                else:
                    self.assertEqual(log.strip(), "user")
                    self.assertIn("WARNING: lingering is OFF for alice", result.stdout)
                    self.assertNotIn("Run it now?", result.stdout)
                (root / "log").unlink()

    def test_linger_user_enable_is_verified(self):
        harness = """state=no
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { case "$1" in show-user) echo "$state";; enable-linger) state=yes;; esac; }
""" + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install; installer_linger_summary alice\n"
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("lingering is on for alice", result.stdout)
        self.assertNotIn("WARNING:", result.stdout)

    def test_linger_missing_loginctl_warns_in_summary(self):
        harness = """command() { [ "$1" != -v ] || [ "$2" != loginctl ]; }
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
""" + function("installer_enable_linger") + function("installer_linger_summary") + "\ninstaller_enable_linger alice install || :; installer_linger_summary alice\n"
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertIn("install it, then run: sudo loginctl enable-linger alice", result.stdout)
        self.assertIn("WARNING: lingering is OFF for alice", result.stdout)

    def test_linger_failure_prints_error_and_recovery(self):
        harness = '''
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { printf 'stub loginctl failure\\n' >&2; return 1; }
''' + function("installer_enable_linger") + '\ninstaller_enable_linger alice\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stub loginctl failure", result.stderr)
        self.assertIn("sudo loginctl enable-linger alice", result.stdout)
        self.assertIn("STOP when your last login session closes", result.stdout)

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

    def test_linger_success_is_verified(self):
        harness = '''
pr_warn() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
pr_info() { fmt="$1"; shift; printf "$fmt\\n" "$@"; }
loginctl() { [ "$1" != show-user ] || printf "yes\\n"; }
''' + function("installer_enable_linger") + '\ninstaller_enable_linger alice\n'
        result = subprocess.run(["sh", "-c", harness], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("already enabled", result.stdout)

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
