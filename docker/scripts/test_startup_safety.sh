#!/usr/bin/env bash
# Offline startup safety tests. The provider, curl and nightly update path
# are stubbed; no Docker image, network access or external process control is used.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${REPO_DIR:-$(cd "$HERE/../.." && pwd)}"
tmp="$(mktemp -d)" || exit 1
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/app" "$tmp/ip-tmp"

pass=0
fail=0
rc=0
out=""

ok() { pass=$((pass + 1)); printf 'PASS: %s\n' "$1"; }
bad() { fail=$((fail + 1)); printf 'FAIL: %s\n' "$1"; }
check() {
    name="$1"
    shift
    if "$@"; then ok "$name"; else bad "$name"; fi
}

# Extract the real functions; only redirect the container mount path for tests.
python3 - "$REPO" "$tmp" <<'PY'
import pathlib
import re
import sys

repo, tmp = map(pathlib.Path, sys.argv[1:])

def extract(source, function):
    text = source.read_text()
    match = re.search(r"^" + re.escape(function) + r"\(\)\s*\{.*?^}\n", text, re.M | re.S)
    if not match:
        raise SystemExit(f"missing {function} in {source}")
    return match.group(0)

common_path = repo / "docker/scripts/provider_common.sh"
common = common_path.read_text()
functions = (
    "func_check_proxy_import",
    "func_check_proxy",
    "func_ip_checker",
    "func_login_retry_loop",
    "func_start_provider_jwt",
)
blocks = [extract(common_path, function) for function in functions]
blocks[0] = blocks[0].replace('"/app/proxy.txt"', '"$TEST_APP/proxy.txt"')
bootstrap_start = common.index("func_bootstrap() {")
nightly_start = common.index("      nightly)" + chr(10), bootstrap_start)
sequence_end = common.index("        # Pass host's actual hostname", nightly_start)
nightly = common[nightly_start:sequence_end]
(tmp / "nightly-sequence.sh").write_text(
    'func_bootstrap_nightly_prelude() {' + chr(10)
    + '  case "$PROVIDER_MODE" in' + chr(10)
    + nightly
    + '        ;;' + chr(10) + '  esac' + chr(10) + '}' + chr(10)
)
(tmp / "common-functions.sh").write_text("\n".join(blocks))

panel_path = repo / "docker/scripts/pelican_panel.sh"
(tmp / "panel-function.sh").write_text(extract(panel_path, "func_do_login"))
PY
if [ "$?" -ne 0 ]; then printf 'FAIL: function extraction\n'; exit 1; fi

command -v jq >/dev/null || { printf 'FAIL: jq is required\n'; exit 1; }

cat > "$tmp/provider-stub" <<'SH'
#!/bin/sh
if [ -n "${CALL_LOG:-}" ]; then printf '%s\n' "$*" >> "$CALL_LOG"; fi
case "$1" in
  --version) printf '%s\n' 'v0.0.0-stub'; exit 0 ;;
  proxy)
    [ -z "${EVENT_LOG:-}" ] || printf '%s\n' proxy >> "$EVENT_LOG"
    python3 - "$HOME/.urnetwork/proxy" <<'PY' || exit 92
import json
import sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
assert data["servers"] == {}
PY
    if [ "${PROXY_FAIL:-no}" = yes ]; then
      printf '%s\n' partial > "$HOME/.urnetwork/proxy"
      exit 17
    fi
    # The real binary can return success without changing its seeded config.
    if [ "${PROXY_FAIL:-no}" = silent ]; then exit 0; fi
    proxy_file=""
    for arg in "$@"; do
      case "$arg" in --proxy_file=*) proxy_file=${arg#--proxy_file=} ;; esac
    done
    if ! rg -q '^[[:space:]]*[^[:space:]#]' "$proxy_file"; then exit 0; fi
    printf '%s\n' '{"auths":{"keep":{"user":"alice","password":"secret"}},"servers":{"new:1080":""}}' > "$HOME/.urnetwork/proxy"
    exit 0
    ;;
  auth)
    if [ "${JWT_CONTRACT_TEST:-no}" = yes ]; then
      if [ "$#" -ne 3 ] || [ -n "$2" ] || [ "$3" != -f ] || [ -z "${URNETWORK_AUTH_CODE:-}" ]; then
        exit 91
      fi
      printf '%s\n' 'empty positional code; environment fallback present' > "$AUTH_CONTRACT_LOG"
    fi
    mkdir -p "${JWT_FILE%/*}"
    printf '%s\n' test-jwt > "$JWT_FILE"
    printf 'Jwt written to %s\n' "$JWT_FILE"
    if [ "${AUTH_DIAGNOSTIC:-no}" = yes ]; then
      printf '%s\n' 'diagnostic: upstream message'
    elif [ "${AUTH_NORMALIZED:-no}" = yes ]; then
      # the server may echo the address normalized and nothing else; the
      # redaction must catch it on the address alone
      printf 'echoed %s\n' "$(printf '%s' "${USER_AUTH:-}" | tr '[:upper:]' '[:lower:]')"
    else
      printf 'echoed %s %s\n' "${USER_AUTH:-}" "${PASSWORD:-}"
    fi
    exit 0
    ;;
  *) exit 0 ;;
esac
SH
chmod +x "$tmp/provider-stub"
cp "$tmp/provider-stub" "$tmp/app/urnetwork_amd64_stable"
cp "$tmp/provider-stub" "$tmp/app/urnetwork_amd64_nightly"

cat > "$tmp/bin/curl" <<'SH'
#!/bin/sh
output=""
while [ "$#" -gt 0 ]; do
  if [ "$1" = -o ]; then output="$2"; shift 2; else shift; fi
done
case "${CURL_MODE:-fetch-fail}" in
  fetch-fail)
    printf '%s\n' 'printf executed > "$EXEC_MARKER"' > "$output"
    exit 22
    ;;
  script-fail) printf '%s\n' 'exit 9' > "$output" ;;
  success) printf '%s\n' 'printf executed > "$EXEC_MARKER"' > "$output" ;;
  *) exit 1 ;;
esac
SH
chmod +x "$tmp/bin/curl"

cat > "$tmp/proxy-driver" <<'SH'
#!/bin/sh
set -eu
. "$COMMON_FUNCTIONS"
APP_DIR="$TEST_APP"
A_SYS_ARCH=amd64
PROVIDER_FLAVOR="${PROXY_FLAVOR:-stable}"
log() { printf '%s\n' "$*"; }
func_check_proxy
SH

run_proxy() {
    env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" COMMON_FUNCTIONS="$tmp/common-functions.sh" \
        PROXY_FLAVOR="$flavor" PROXY_FAIL="$proxy_fail" CALL_LOG="$calls" TMPDIR="$tmp" \
        sh "$tmp/proxy-driver" > "$out" 2>&1
    rc=$?
}
no_staging_left() {
    for stage in "$state"/.proxy-import.*; do [ ! -e "$stage" ] || return 1; done
}
proxy_kept_without_mount() {
    [ "$rc" -eq 0 ] && cmp -s "$state/proxy" "$original" &&
        rg -Fq 'kept existing proxy configuration' "$out" && [ ! -e "$calls" ]
}
proxy_none_without_mount() {
    [ "$rc" -eq 0 ] && [ ! -e "$home/.urnetwork" ] &&
        rg -Fq 'none configured' "$out" && [ ! -e "$calls" ]
}
proxy_healed() {
    [ "$rc" -eq 0 ] && rg -Fq 'Proxy configuration replaced from proxy.txt' "$out" &&
        rg -Fq "$state/proxy" "$out" && no_staging_left || return 1
    backups=("$state"/proxy.corrupt.*)
    [ "${#backups[@]}" -eq 1 ] && [ -f "${backups[0]}" ] &&
        cmp -s "${backups[0]}" "$original" && rg -Fq "${backups[0]}" "$out" &&
        jq -e '.servers == {"new:1080":""}' "$state/proxy" >/dev/null
}
proxy_failed_kept() {
    [ "$rc" -eq 0 ] && cmp -s "$state/proxy" "$original" &&
        rg -Fq 'kept the existing configuration' "$out" && rg -Fq 'proxy add' "$calls" && no_staging_left
}

# A corrupt saved config is not a fallback: the provider cannot load it, so the
# container would end up sending traffic direct and must stop instead.
proxy_fatal() {
    [ "$rc" -ne 0 ] && rg -Fq 'refusing to start without the mounted proxy' "$out" && no_staging_left
}
proxy_imported() {
    [ "$rc" -eq 0 ] && rg -Fq 'Proxy configuration replaced from proxy.txt' "$out" &&
        rg -Fq 'proxy add --proxy_file=' "$calls" && rg -Fq ' -f' "$calls" &&
        [ "$(stat -c '%a' "$state/proxy")" = 600 ] && no_staging_left || return 1
    python3 - "$state/proxy" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
assert data["servers"] == {"new:1080": ""}
assert data["auths"]["keep"]["user"] == "alice"
PY
}

# No mounted list must never erase the operator's persisted proxy configuration.
home="$tmp/proxy-kept/home"; state="$home/.urnetwork"; mkdir -p "$state"
original="$tmp/proxy-kept/original"; out="$tmp/proxy-kept/out"; calls="$tmp/proxy-kept/calls"
mkdir -p "${out%/*}"
printf '%s\n' '{"auths":{"keep":{"user":"alice","password":"secret"}},"servers":{"old:1080":"keep"}}' > "$original"
cp "$original" "$state/proxy"; rm -f "$tmp/app/proxy.txt" "$calls"; flavor=stable; proxy_fail=no
run_proxy; check 'missing proxy mount preserves existing config' proxy_kept_without_mount

# With no prior config, a missing mount is a clean no-proxy startup.
home="$tmp/proxy-none/home"; state="$home/.urnetwork"; out="$tmp/proxy-none/out"; calls="$tmp/proxy-none/calls"
mkdir -p "${out%/*}"; rm -f "$tmp/app/proxy.txt" "$calls"; flavor=stable; proxy_fail=no
run_proxy; check 'missing proxy mount leaves absent config absent' proxy_none_without_mount

# Invalid saved JSON or a non-object must be preserved as a backup and healed.
for invalid in malformed null; do
    home="$tmp/proxy-$invalid/home"; state="$home/.urnetwork"; mkdir -p "$state"
    original="$tmp/proxy-$invalid/original"; out="$tmp/proxy-$invalid/out"; calls="$tmp/proxy-$invalid/calls"
    if [ "$invalid" = malformed ]; then printf '%s\n' '{not-json' > "$original"; else printf '%s\n' null > "$original"; fi
    cp "$original" "$state/proxy"
    printf '%s\n' 'new:1080:user:pass' > "$tmp/app/proxy.txt"; flavor=stable; proxy_fail=no
    run_proxy; check "$invalid saved config is backed up and healed" proxy_healed
done

# A failed provider import can partially write its staged file, never live state.
home="$tmp/proxy-failed/home"; state="$home/.urnetwork"; mkdir -p "$state"
original="$tmp/proxy-failed/original"; out="$tmp/proxy-failed/out"; calls="$tmp/proxy-failed/calls"
mkdir -p "${out%/*}"; printf '%s\n' '{"auths":{"keep":{"user":"alice","password":"secret"}},"servers":{"old:1080":"keep"}}' > "$original"
cp "$original" "$state/proxy"; printf '%s\n' 'new:1080:user:pass' > "$tmp/app/proxy.txt"; rm -f "$calls"; flavor=stable; proxy_fail=yes
run_proxy; check 'partial failed import preserves live config' proxy_failed_kept

# With no saved config there is nothing to fall back on, so a failed import stops startup.
home="$tmp/proxy-fatal/home"; state="$home/.urnetwork"; mkdir -p "$state"
original="$tmp/proxy-fatal/original"; out="$tmp/proxy-fatal/out"; calls="$tmp/proxy-fatal/calls"
mkdir -p "${out%/*}"; printf '%s\n' 'new:1080:user:pass' > "$tmp/app/proxy.txt"; rm -f "$calls"; flavor=stable; proxy_fail=yes
run_proxy; check 'a failed import with no saved config stops startup' proxy_fatal

# Silent write failures and files without proxies must not install the seed.
proxy_empty_rejected() {
    proxy_failed_kept && rg -Fq 'staged server list is empty or invalid' "$out" &&
        ! rg -Fq 'Proxy configuration replaced from proxy.txt' "$out"
}
for scenario in silent empty comments; do
    home="$tmp/proxy-$scenario/home"; state="$home/.urnetwork"; mkdir -p "$state"
    original="$tmp/proxy-$scenario/original"; out="$tmp/proxy-$scenario/out"; calls="$tmp/proxy-$scenario/calls"
    printf '%s\n' '{"auths":{"keep":{"user":"alice","password":"secret"}},"servers":{"old:1080":"keep"}}' > "$original"
    cp "$original" "$state/proxy"; flavor=stable; proxy_fail=no
    case "$scenario" in
      silent) proxy_fail=silent; printf '%s\n' 'new:1080:user:pass' > "$tmp/app/proxy.txt" ;;
      empty) : > "$tmp/app/proxy.txt" ;;
      comments) printf '%s\n' '# first comment' '  # second comment' > "$tmp/app/proxy.txt" ;;
    esac
    run_proxy; check "$scenario import preserves live config and reports failure" proxy_empty_rejected
done

# A successful import replaces servers while retaining named auth entries.
printf '%s\n' 'new:1080:user:pass' > "$tmp/app/proxy.txt"
home="$tmp/proxy-success/home"; state="$home/.urnetwork"; mkdir -p "$state"
original="$tmp/proxy-success/original"; out="$tmp/proxy-success/out"; calls="$tmp/proxy-success/calls"
mkdir -p "${out%/*}"; printf '%s\n' '{"auths":{"keep":{"user":"alice","password":"secret"}},"servers":{"old:1080":"keep"}}' > "$original"
cp "$original" "$state/proxy"; rm -f "$calls"; flavor=stable; proxy_fail=no
run_proxy; check 'successful import replaces servers and retains auth' proxy_imported

# A first import initializes a staged config before invoking the provider.
home="$tmp/proxy-first/home"; state="$home/.urnetwork"
out="$tmp/proxy-first/out"; calls="$tmp/proxy-first/calls"
mkdir -p "$home" "${out%/*}"; printf '%s' 'new:1080:user:pass' > "$tmp/app/proxy.txt"
rm -f "$calls"; flavor=stable; proxy_fail=no
run_proxy; check 'first import initializes config and installs proxies' proxy_imported

cat > "$tmp/ip-driver" <<'SH'
#!/bin/sh
set -eu
. "$COMMON_FUNCTIONS"
log() { printf '%s\n' "$*"; }
ENABLE_IP_CHECKER=true
IP_CHECKER_URL=https://invalid.example/check
func_ip_checker
SH
run_ip() {
    env PATH="$tmp/bin:$PATH" COMMON_FUNCTIONS="$tmp/common-functions.sh" ENABLE_IP_CHECKER=true \
        CURL_MODE="$curl_mode" EXEC_MARKER="$marker" TMPDIR="$ip_tmp" \
        sh "$tmp/ip-driver" > "$out" 2>&1
    rc=$?
}
no_ip_temp_left() {
    for file in "$ip_tmp"/urnetwork-ip-checker.*; do [ ! -e "$file" ] || return 1; done
}
ip_fetch_failed() {
    [ "$rc" -eq 0 ] && [ ! -e "$marker" ] && rg -Fq 'IP checker fetch failed' "$out" &&
        ! rg -Fq 'script ran successfully' "$out" && no_ip_temp_left
}
ip_script_failed() {
    [ "$rc" -eq 0 ] && [ ! -e "$marker" ] && rg -Fq 'IP checker script failed' "$out" &&
        ! rg -Fq 'fetch failed' "$out" && no_ip_temp_left
}
ip_script_succeeded() {
    [ "$rc" -eq 0 ] && [ -s "$marker" ] && rg -Fq 'IP checker script ran successfully' "$out" &&
        ! rg -Fq 'fetch failed' "$out" && no_ip_temp_left
}
ip_tmp="$tmp/ip-tmp"; out="$tmp/ip-fetch/out"; mkdir -p "${out%/*}"; marker="$tmp/ip-fetch/executed"; curl_mode=fetch-fail
run_ip; check 'failed fetch does not execute a partial checker script' ip_fetch_failed
out="$tmp/ip-script-fail/out"; mkdir -p "${out%/*}"; marker="$tmp/ip-script-fail/executed"; curl_mode=script-fail
run_ip; check 'fetched checker script failure is reported separately' ip_script_failed
out="$tmp/ip-success/out"; mkdir -p "${out%/*}"; marker="$tmp/ip-success/executed"; curl_mode=success
run_ip; check 'successful checker script executes and is reported' ip_script_succeeded

cat > "$tmp/login-driver" <<'SH'
#!/bin/sh
set -eu
. "$FUNCTIONS"
APP_DIR="$TEST_APP"
A_SYS_ARCH=amd64
PROVIDER_FLAVOR=stable
JWT_FILE="$HOME/.urnetwork/jwt"
export JWT_FILE
log() { printf '%s\n' "$*"; }
func_sleep() { :; }
func_exit_if_stopping() { :; }
case "$LOGIN_KIND" in
  shared) func_login_retry_loop ;;
  pelican) func_do_login ;;
esac
SH
login_safe() {
    [ "$rc" -eq 0 ] && ! rg -Fq 'fake-user-123' "$out" && ! rg -Fq 'fake-password-456' "$out" &&
        rg -Fqx 'DEBUG: USER_AUTH set=yes length=13' "$out" &&
        rg -Fqx 'DEBUG: PASSWORD set=yes length=17' "$out" &&
        rg -Fqx 'DEBUG: AUTH_EXIT_CODE=0' "$out" &&
        rg -Fqx 'DEBUG: AUTH_OUTPUT=[redacted]' "$out"
}
run_login() {
    env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" FUNCTIONS="$functions" \
        LOGIN_KIND="$kind" DEBUG=true USER_AUTH=fake-user-123 PASSWORD=fake-password-456 \
        sh "$tmp/login-driver" > "$out" 2>&1
    rc=$?
}
for kind in shared pelican; do
    home="$tmp/login-$kind/home"; mkdir -p "$home/.urnetwork"
    functions="$tmp/common-functions.sh"; [ "$kind" = pelican ] && functions="$tmp/panel-function.sh"
    out="$tmp/login-$kind/out"
    run_login; check "$kind login debug redacts credential values" login_safe
done

login_case_normalized() {
    env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" FUNCTIONS="$functions" \
        LOGIN_KIND="$kind" DEBUG=true USER_AUTH='Private-User-123' PASSWORD='private-password-456' AUTH_NORMALIZED=yes \
        sh "$tmp/login-driver" > "$out" 2>&1 || return 1
    rg -Fqx 'DEBUG: AUTH_OUTPUT=[redacted]' "$out" && ! rg -Fq 'private-user-123' "$out"
}
for kind in shared pelican; do
    home="$tmp/login-$kind/home"; mkdir -p "$home/.urnetwork"
    functions="$tmp/common-functions.sh"; [ "$kind" = pelican ] && functions="$tmp/panel-function.sh"
    out="$tmp/login-$kind/out"
    check "$kind login redacts a case-normalized credential echo" login_case_normalized
done

login_empty_credentials() {
    env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" FUNCTIONS="$functions" \
        LOGIN_KIND="$kind" DEBUG=true USER_AUTH="$test_user" PASSWORD="$test_password" AUTH_DIAGNOSTIC=yes \
        sh "$tmp/login-driver" > "$out" 2>&1 || return 1
    rg -Fq 'diagnostic: upstream message' "$out" && ! rg -Fq 'DEBUG: AUTH_OUTPUT=[redacted]' "$out" || return 1
    env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" FUNCTIONS="$functions" \
        LOGIN_KIND="$kind" DEBUG=true USER_AUTH="$test_user" PASSWORD="$test_password" \
        sh "$tmp/login-driver" > "$out" 2>&1 || return 1
    if [ -n "$test_user" ] || [ -n "$test_password" ]; then
        rg -Fqx 'DEBUG: AUTH_OUTPUT=[redacted]' "$out" &&
            ! rg -Fq 'fake-user-123' "$out" && ! rg -Fq 'fake-password-456' "$out"
    else
        ! rg -Fq 'DEBUG: AUTH_OUTPUT=[redacted]' "$out"
    fi
}
for kind in shared pelican; do
    functions="$tmp/common-functions.sh"; [ "$kind" = pelican ] && functions="$tmp/panel-function.sh"
    for missing in user password both; do
        home="$tmp/login-$kind-$missing/home"; mkdir -p "$home/.urnetwork"; out="$tmp/login-$kind-$missing/out"
        test_user=fake-user-123; test_password=fake-password-456
        case "$missing" in user) test_user= ;; password) test_password= ;; both) test_user=; test_password= ;; esac
        check "$kind login keeps diagnostics with empty $missing and redacts remaining secret" login_empty_credentials
    done
done

cat > "$tmp/nightly-driver" <<'SH'
#!/bin/sh
set -eu
. "$COMMON_FUNCTIONS"
. "$NIGHTLY_SEQUENCE"
APP_DIR="$TEST_APP"
PROVIDER_MODE=nightly
PROVIDER_FLAVOR=nightly
UPDATE_TIME=12:00
EVENT_LOG="$EVENT_LOG"
log() { printf '%s\n' "$*"; }
record() { printf '%s\n' "$1" >> "$EVENT_LOG"; }
func_get_architecture() { A_SYS_ARCH=amd64; record architecture; }
func_check_dir() { record check-dir; }
func_check_credentials() { record credentials; }
func_report_identity() { record report; }
func_ip_checker() { record ip-check; }
func_start_vnstat() { record vnstat; }
func_check_update() {
  record update
  cp "$PROVIDER_STUB" "$APP_DIR/urnetwork_${A_SYS_ARCH}_${PROVIDER_FLAVOR}"
  chmod +x "$APP_DIR/urnetwork_${A_SYS_ARCH}_${PROVIDER_FLAVOR}"
}
func_choose_network() { record choose-network; }
func_do_login() { record login; }
func_start_provider() { record start-provider; }
func_bootstrap_nightly_prelude
SH
nightly_ordered() {
    python3 - "$events" <<'PY'
import pathlib
import sys
items = pathlib.Path(sys.argv[1]).read_text().splitlines()
assert items.index("update") < items.index("proxy"), items
PY
}
home="$tmp/nightly/home"; mkdir -p "$home"; events="$tmp/nightly/events"; out="$tmp/nightly/out"; mkdir -p "${out%/*}"
printf '%s\n' 'new:1080:user:pass' > "$tmp/app/proxy.txt"
env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" COMMON_FUNCTIONS="$tmp/common-functions.sh" NIGHTLY_SEQUENCE="$tmp/nightly-sequence.sh" \
    PROVIDER_STUB="$tmp/provider-stub" EVENT_LOG="$events" CALL_LOG="$tmp/nightly/calls" TMPDIR="$tmp" \
    sh "$tmp/nightly-driver" > "$out" 2>&1
rc=$?
check 'fresh nightly downloads provider binary before proxy import' nightly_ordered

cat > "$tmp/jwt-driver" <<'SH'
#!/bin/sh
set -eu
. "$COMMON_FUNCTIONS"
APP_DIR="$TEST_APP"
A_SYS_ARCH=amd64
PROVIDER_FLAVOR=stable
JWT_FILE="$HOME/.urnetwork/jwt"
export JWT_FILE
log() { printf '%s\n' "$*"; }
func_exit_if_stopping() { :; }
func_sleep() { :; }
resolve_provider_env_args() { PROVIDER_ENV_ARGS=""; }
func_run_provider() { code=0; }
pgrep() { return 1; }
func_start_provider_jwt
SH
jwt_contract() {
    [ "$rc" -eq 0 ] && rg -Fq 'empty positional code; environment fallback present' "$contract_log" &&
        [ -s "$home/.urnetwork/jwt" ]
}
home="$tmp/jwt-contract/home"; mkdir -p "$home/.urnetwork"; contract_log="$tmp/jwt-contract/auth-contract"
out="$tmp/jwt-contract/out"; mkdir -p "${out%/*}"
cp "$tmp/provider-stub" "$tmp/app/urnetwork_amd64_stable"; chmod +x "$tmp/app/urnetwork_amd64_stable"
env PATH="$tmp/bin:$PATH" HOME="$home" TEST_APP="$tmp/app" COMMON_FUNCTIONS="$tmp/common-functions.sh" \
    JWT_CONTRACT_TEST=yes AUTH_CONTRACT_LOG="$contract_log" URNETWORK_AUTH_CODE=environment-only-code \
    sh "$tmp/jwt-driver" > "$out" 2>&1
rc=$?
check 'JWT startup keeps empty positional code and environment fallback' jwt_contract

# The nightly bootstrap must download the binary before the proxy import runs it,
# and a failed import must not abort startup. The function-level cases above cannot
# see either, because they run func_check_proxy outside the real sequence.
bootstrap_order() {
  block=$(sed -n '/^      nightly)/,/^        ;;/p' "$REPO/docker/scripts/provider_common.sh")
  update_line=$(printf '%s\n' "$block" | grep -n 'func_check_update' | head -1 | cut -d: -f1)
  proxy_line=$(printf '%s\n' "$block" | grep -n 'func_check_proxy' | head -1 | cut -d: -f1)
  [ -n "$update_line" ] && [ -n "$proxy_line" ] && [ "$update_line" -lt "$proxy_line" ]
}
check 'nightly downloads the binary before importing proxies' bootstrap_order

bootstrap_proxy_fatal() {
  block=$(sed -n '/^      nightly)/,/^        ;;/p' "$REPO/docker/scripts/provider_common.sh")
  printf '%s\n' "$block" | grep -q '^        func_check_proxy$'
}
check 'nightly lets a fatal proxy failure reach startup' bootstrap_proxy_fatal

printf 'Results: %s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
