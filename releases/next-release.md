# Next release

Previous release: [v2026.11.6-1091992770-meso](https://github.com/urfoundation/meso-miner/releases/tag/v2026.11.6-1091992770-meso).

The extender role now runs by default and activates with the platform. I added guided setup for it, fixed receive-loop panics and improved log following. I also added on-demand diagnostic bundles.

Legend: **[redeploy]** needs the new provider, tool or container image. **[installer]** needs the updated installer or script. **[no redeploy]** covers documentation and tests.

## Quick start

Install on Linux:

```sh
curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Linux.sh | sh
```

Install on macOS:

```sh
curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Mac.sh | sh -s -- install
```

Install on Windows in PowerShell:

```powershell
irm https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Win32.ps1 | iex
```

Install on FreeBSD from a non-root service account with `sudo`:

```sh
fetch -qo urnet-install.sh https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_FreeBSD.sh
sudo sh urnet-install.sh install
```

For Docker, pull `ghcr.io/urfoundation/meso-miner:latest`. See the [Docker deployment guide](https://github.com/urfoundation/meso-miner/blob/main/docs/Docker-Deployment.md) for setup and persistent state.

## What changed

### Extender

- **The extender runs by default** **[redeploy]**. It activates with the platform; `urnet-tools extender on` and `off` change the saved setting. Activation keeps its pacing across restarts and waits for platform root keys before trusting stored records.
- **TCP 443 binds first** **[redeploy]**. The extender opens no other carrier while it cannot bind TCP 443. UDP 53 is optional and user-managed; setup does not inspect or open it.
- **Status explains carrier listings** **[redeploy]**. Status and `top` distinguish bound carriers from those accepted by the platform. Logs identify omitted carriers and report when they return.
- **Restarts and access checks are safer** **[redeploy]**. The manager restarts an exited role. A public suffix no longer grants access to unrelated domains. Root-key errors omit response bodies, and `top` resets extender state when switching providers.

### Extender setup

- **`urnet-tools extender setup` is new** **[redeploy]**. On supported platforms it checks ports, bind privileges and host firewall rules, then shows the plan before making changes. A live bind check runs when available. FreeBSD is print-only, as noted below.
- **Approval stays explicit** **[redeploy]**. Only `--yes` (`-y`) or `--force` approves a non-interactive run. Elevation never implies approval; the elevated run presents its plan. Manual reruns keep the selected target and flags.
- **Firewall and capability changes are conservative** **[redeploy]**. firewalld runtime and permanent rules are planned separately, without a reload. Setup stops when it cannot inspect firewalld rules and preserves existing file capabilities when adding bind permission.
- **Port checks match the exact local port** **[redeploy]**. The `lsof` check does not mistake a remote endpoint or a longer port number for a local match. FreeBSD uses `sockstat`, including dual-stack entries.
- **FreeBSD setup is print-only and untested** **[redeploy]**. It prints the `sysctl` commands and undo instructions without elevating or changing the host. The setting removes privileged-port protection for all local users. Regular providing is unaffected.
- **The Linux installer reports TCP 443 availability** **[installer]**. The notice does not change the port or interrupt installation.

### Provider and logs

- **Receive-loop panics are fixed** **[redeploy]**. Missing paths and inconsistent or stale receive indexes no longer stop the client; repeated mismatch diagnostics are bounded.
- **Log following continues across RAM log trims** **[redeploy]**. The follower tracks the path when a trim replaces the file and avoids losing new lines when retained history repeats.
- **`urnet-tools diag` captures profiles on request** **[redeploy]**. It collects diagnostic bundles from a running provider without a restart. The free-space check uses the diag directory's filesystem and treats negative availability as zero.
- **Windows uninstall handles multiple processor records** **[installer]**. It proceeds only when the reported architectures agree; otherwise it removes nothing.

### Documentation

- **The extender guide, log reference and Docker guidance are updated** **[no redeploy]**. The Docker bridge guidance distinguishes IPv4 from IPv6 and includes Compose examples.

## Known limitations

- The Docker RAM log follower can replay retained lines after a trim.
- A hot-swap candidate can race the old provider while it still holds a listening socket.
- FreeBSD extender setup has not been tested on a FreeBSD host.

Full changelog: https://github.com/urfoundation/meso-miner/compare/v2026.11.6-1091992770-meso...main
