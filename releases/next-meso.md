<!-- DRAFT. At tag time: rename this file to releases/<tag>.md, put the tag in the title and today's date in Released, then delete this comment. -->

# NEXT_TAG

**Released:** NEXT_DATE.

Previous release: [v2026.11.8-1093260920-meso](https://github.com/urfoundation/meso-miner/releases/tag/v2026.11.8-1093260920-meso).

This release adds OpenBSD support, ports the client side of the network operator's FP2 provider selection, closes a handshake bug where one forged id could wedge a peer session, and moves the build to Go 1.27.4. The provider binary does not run the multi client window, so the FP2 port changes nothing for a provider fleet by itself. Update and restart, because the handshake fix changes the binary.

Legend: **[redeploy]** needs the new provider, tool or container image. **[installer]** needs the updated installer or script. **[no redeploy]** covers documentation, CI and tests.

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

### OpenBSD
- **OpenBSD support. [redeploy] [installer]** The provider and `urnet-tools` build for OpenBSD on amd64 and arm64. There is an installer, `rcctl` service setup, cron auto-update and release assets. `urnet-tools` on OpenBSD selects `sudo` when `/etc/doas.conf` does not exist.

### Updates and installer
- **Hotswap accepts meso releases and uses the 2026-10-20 version floor. [redeploy]**
- **Updates stop when unit reconciliation is unsafe and verify the handoff with the control peer. [redeploy]**
- **The installer reports privileged setup failures. [installer]**
- **The provider follows replaced RAM log files. [redeploy]**

### Network and security
- **A forged handshake generation id cannot wedge a peer session. [redeploy]** A peer could send a ClientHello with a high id and make the responder drop every later ClientHello that carried a lower id. The responder now takes an id only from a ClientHello and ignores foreign proofs and responses.
- **IPv6 admission and a TCP-only window in the multi client. [no redeploy]** SDK and proxy clients built on this tree keep an IPv4 hard minimum, ask for IPv6-capable exits when the IPv6 share falls short, and hold a limited window of TCP-only providers. The provider binary does not run this code.
- **The blocklist sync runs the blocker, CFAA, Telegram and security tests against the upstream tables before it opens a PR. [no redeploy]**

### Build and documentation
- **The build is Go 1.27.4. [redeploy]**
- **The BSD cron log path uses forward slashes on every build host. [no redeploy]**
- **The Docker examples use `AUTH=authcode` and `AUTH=userpass`. [no redeploy]**

## Known limitations

- The blocklist tables stay at their current refresh. Upstream's tables from 2026-11-13 use a new format and list a Telegram call reflector that upstream's own test rejects. The sync check blocks them until upstream fixes the table.
- Recent exit memory and the sticky redial of a fixed exit are idle in this line, because it lacks the transport-loss signal they need.
- The OpenBSD runtime was not run on a real OpenBSD host.
