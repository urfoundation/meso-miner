# ⛓ meso-miner

[![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/urfoundation/meso-miner?utm_source=oss&utm_medium=github&utm_campaign=urfoundation%2Fmeso-miner&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)](https://coderabbit.ai)
[![CI](https://github.com/urfoundation/meso-miner/actions/workflows/build.yml/badge.svg)](https://github.com/urfoundation/meso-miner/actions)
![Go Version](https://img.shields.io/github/go-mod/go-version/urfoundation/meso-miner?labelColor=171717&color=FF570A)
![Release](https://img.shields.io/github/v/release/urfoundation/meso-miner?labelColor=171717&color=FF570A)
![Language](https://img.shields.io/github/languages/top/urfoundation/meso-miner?labelColor=171717&color=FF570A)
![Activity](https://img.shields.io/github/commit-activity/m/urfoundation/meso-miner?labelColor=171717&color=FF570A)

**meso-miner** is a provider for the [UrNetwork](https://ur.io) network, built for people who run many proxies and want to see what their machines are doing. It is the same tuned provider line as the 3.23-fix fork, released here for urfoundation, together with `urnet-tools`, a command-line helper that installs, updates and looks after your providers.

Releases are tagged `v<YYYY.M.D>-<unix>-meso` (for example `v2026.10.20-1076956260-meso`). The Docker image is `ghcr.io/urfoundation/meso-miner`. Not affiliated with the official UrNetwork project.

## 🧭 Start here

New to this? Do these three things.

1. **Install.** Pick the one-line installer for your system in [Install](#install) below (Linux, macOS, Windows or Docker).
2. **Sign in.** Run `urnetwork auth` and paste an auth code from [app.ur.network](https://app.ur.network). Step by step: [Beginner guide](docs/guides/beginner.md).
3. **Check it is running.** Run `urnet-tools status`. If something looks wrong, see [Troubleshooting](docs/Troubleshooting.md).

You do not need to change any settings. The provider picks sensible defaults for your machine's memory. Come back to the table of guides further down when you want to go further.

## 🆚 What meso-miner adds to the stock UrNetwork provider

The "stock" column is the plain provider from the upstream URnetwork connect project (its last standalone `provider` command, before it moved into the `sn` repository). "Stock" here does not mean it lacks everything in this table, only what it ships with by default.

| | Stock UrNetwork provider | meso-miner |
| :--- | :--- | :--- |
| Dial visibility | The `[net][s]select` line is logged at INFO | Same line, now with the dial time, and repeated errors are collapsed with a "suppressed" count |
| Contract sizing | 1 MiB first contract, 4 contracts to ramp up to 128 MiB | First contract is 128 KiB to 2 MiB depending on how much memory the machine has (2 MiB on bigger machines), with a faster 3-contract ramp |
| Proxy startup | All at once | Staggered start with a live `[pace]` progress line, plus one shared rate limiter that keeps sign-in traffic to the API under control |
| Proxy changes | Restart required | Add or remove proxies while running, with no downtime |
| Dead proxy handling | Keeps retrying | Tries once a day, drops file proxies after 14 days (65 minutes for URL-fed ones), and remembers this across restarts |
| Proxy source | A file you pass in | A file, a live URL feed, or both, with automatic clean-up |
| Proxy health | None | A to F grade per proxy, re-checked continuously (`proxy health`, `proxy trim`) |
| Fleet visibility | None | Traffic accounting in `usage` and `proxy traffic`, a live `top` view, and Prometheus metrics (`urnet-tools metrics on`) |
| Performance profiles | None | Auto, Turbo V4, Turbo V8, Eco and Lowmem, each tuning memory and garbage collection |
| Crash diagnostics | Logs lost on restart | RAM log in shared memory plus a critical-event log on disk |
| Custom API backend | `--api_url` and `--connect_url` flags on every run | `choose_network` saves them to disk (flags still win) |
| Changing settings | Edit service files by hand, then restart | A control socket applies changes live, and queues them if the provider is stopped |
| Binary upgrade | Stop, swap, start (20 to 60 seconds of downtime) | HotSwap hands over to a verified new binary and rolls back on failure. See [HotSwap](docs/HotSwap.md) |
| Display name | Hostname only | `rename` sets the label, `show-ip` adds the public IP, no restart |
| Several providers on one machine | One per host | One per OS user, listed with `providers` and `providers --all` |
| Moving machines | None | `session save` and `session load` move identity and proxies as an encrypted bundle |
| Subnet 25 | `wallet set`, `claim` and `bind-head` | Adds `sn-status`, and `claim` can use a stored client credential (`--store-client`, `--provider-jwt`, `--legacy-coldkey`) |
| Memory trouble | None | A swap-thrash watchdog restarts the provider cleanly (exit 75) |
| Windows | No management tool | `urnet-tools` runs natively on Windows |

---

## ₿ Bittensor Subnet 25

Most operators need to do one thing: sign a single wallet message, once, from their own computer. Your nodes do not change. Everything else here (hotkeys, claim daemons, fleets, multiple operators) is optional or advanced, and skipping it costs you nothing. Nothing here runs unless you start it.

- [Bittensor Quick Start](docs/Bittensor-Quick-Start.md): start here. Check where you stand, sign once, and see which commands you can ignore.
- [Bittensor operations](docs/Bittensor-Operations.md): the overview, from the two tiers and wallet consent through claims and the FAQ.
- [Bittensor head tier](docs/Bittensor-Head-Tier.md): the optional, advanced tier. Most operators should skip it.
- [Bittensor glossary](docs/Bittensor-Glossary.md): plain meanings of the words.
- [Bittensor claim daemons](docs/Bittensor-Claim-Daemons.md), [fleet](docs/Bittensor-Fleet.md), [hotkey delegation](docs/Bittensor-Hotkey-Delegation.md) and [multi-operator](docs/Multi-Operator.md): optional or advanced.

---

## 🗺 Guides

| If you want to... | Go here |
| :--- | :--- |
| **Get paid on Bittensor SN25 (do I need to do anything?)** | [Bittensor Quick Start](docs/Bittensor-Quick-Start.md) |
| **Pick your skill level** | [🐣 Beginner](docs/guides/beginner.md) · [🧭 Intermediate](docs/guides/intermediate.md) · [🚀 Advanced](docs/guides/advanced.md) |
| Install on a Linux host as a user-level service | [Installation Guide](docs/Installation.md) |
| Run one Docker container | [Docker Deployment](docs/Docker-Deployment.md) |
| Run multiple containers on one host | [Multi-Container Scaling](docs/Multi-Container-Scaling.md) |
| Choose profiles, turbo mode, or host tuning | [Performance Tuning](docs/High-Volume-Performance-Tuning.md) |
| Understand environment variables | [Configuration Reference](docs/Configuration.md) |
| Interpret provider logs | [Log Message Reference](LOG_REFERENCE.md) |
| Track traffic usage (billable vs control overhead) | [Docker Deployment](docs/Docker-Deployment.md) · [CLI Reference](docs/urnet-tools-go.md) |
| Load a proxy file into the provider (per-OS) | [Adding Proxies](docs/Adding-Proxies.md) |
| Feed the provider a live proxy list URL | [Proxy URL Sources](docs/Proxy-URL-Sources.md) |
| Import into a Pelican game-server panel | [Pelican Panel](docs/Docker-Deployment.md#-pelican-panel) · [Egg README](pelican/README.md) |

---

## ⚡ Quick Start

### Install

**🐧 Linux (systemd)**

```sh
curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Linux.sh | sh
```

**🍎 macOS (launchd)**

```sh
curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Mac.sh | sh
```


**🐋 Docker**

```sh
docker pull ghcr.io/urfoundation/meso-miner:latest
```

**🐋 Docker (management wrapper)**

```sh
curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/install-urnet-docker.sh | sh
```

**🪟 Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Win32.ps1 | iex
```

Windows Defender may flag this one-liner. See the note below.

> [!NOTE]
> Windows Defender may flag the Windows install one-liner, and it may flag the downloaded
> binaries. What we see are machine-learning heuristics (the `!ml` suffix), not signatures;
> for the binaries we publish they are false positives. Recent release pages record the scan
> results for the published binaries. If Defender blocks the one-liner, download the script,
> review it, and run it from disk instead. If Defender quarantines an extracted binary,
> allow it from Windows Security > Virus & threat protection > Protection history. Both lines
> go in PowerShell:
>
> ```powershell
> irm https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Install_Win32.ps1 -OutFile "$env:TEMP\install-win.ps1"
> powershell -NoProfile -ExecutionPolicy Bypass -File "$env:TEMP\install-win.ps1"
> ```

<details>
<summary>The detections you may see, and what each one means</summary>

- `Trojan:Script/Wacatac.B!ml`, `Trojan:Script/Wacatac.C!ml`: Defender's machine-learning label for the PowerShell installer script fetching and extracting a remote payload.
- `Trojan:Win32/Wacatac.B!ml`, `Trojan:Win32/Wacatac.C!ml`: Defender's machine-learning label for files whose shape looks like a packed trojan. Our Go binaries are stripped, statically linked and unsigned, which reads as a packed payload. The B and C variants are different model generations, so one binary can be flagged under more than one name. `Trojan:Win32/Execution.A!ml` is another label from the same family on some builds.
- `Trojan:Win32/Commando.A!ml`: fires on the download-and-run command line itself (the `irm ... | iex` one-liner), not on the installed files. Fetching a remote script and piping it into execution reads as a trojan-downloader pattern to the model.
- `Trojan:Win32/Bearfoos.A!ml`: a behavioural label for scheduled-task activity. The installer registers Task Scheduler tasks — a weekly update task (on `latest` installs) and, if you accept auto-start, a logon task so the provider starts at login — and a behavioural model cannot tell that apart from persistence malware.

</details>

### After you install

After installation, authenticate and start providing:

```bash
# Linux / macOS: one Go binary on every platform
urnetwork auth
urnet-tools proxy add ~/proxies.txt
urnet-tools proxy refresh
urnet-tools auto on
```
On Windows, run the same commands in PowerShell but use a Windows path, e.g.
`urnet-tools proxy add "$env:USERPROFILE\Downloads\proxies.txt"`. Full per-OS
walkthrough, including the `.txt.txt` extension trap: [Adding Proxies](docs/Adding-Proxies.md).

> [!NOTE]
> `urnet-tools` is a provider-aware Go binary (the legacy POSIX shell + PowerShell variants are retired). It discovers every provider on the box and **refuses to act on an ambiguous target** — on multi-provider machines, pass `--unit` / `--user` / `--network` / `--network-id` / `--state-dir`. See [docs/urnet-tools-go.md](docs/urnet-tools-go.md).
>
> Docker-only deployments: the provider runs in a container, but the management tool (`urnet-docker`) runs **on the docker host, outside the container**. Install it with the one-liner above (use `curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/install-urnet-docker.sh | sh -s -- urnet-tools` for the systemd variant). The tool self-updates afterward (`urnet-docker update`).

### Uninstall

**🐧 Linux**

```sh
curl -fSsL https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Uninstall_Linux.sh | sh
```

**🍎 macOS**

Manual — see [docs/Installation.md](docs/Installation.md).

**🪟 Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/urfoundation/meso-miner/refs/heads/main/scripts/Provider_Uninstall_Win32.ps1 | iex
```

**🐋 Docker**

```sh
docker rm -f <container> && docker rmi ghcr.io/urfoundation/meso-miner:latest
```

**🐋 Docker (management wrapper)**

```sh
rm /usr/local/bin/urnet-docker   # root install
rm ~/.local/bin/urnet-docker     # non-root install
```

### 🐋 Docker (Production-Ready)

Recommended for real deployments — includes auto-tuning, in-memory logs, and persistent config with zero listening ports:

```bash
docker run -d \
  --name=urnetwork-provider \
  --pull=always \
  --restart=unless-stopped \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --sysctl net.ipv4.ip_forward=1 \
  -e BUILD=jwt \
  -e URNETWORK_PROFILE=auto \
  -e URNETWORK_RAMLOGS=1 \
  -e HOST_HOSTNAME=$(hostname) \
  -e PROXY_URL='https://example.com/your-proxy-list.txt' \
  -v urnetwork_config:/root/.urnetwork \
  -v /path/to/proxy.txt:/app/proxy.txt \
  -e URNETWORK_AUTH_CODE='YOUR_AUTH_CODE_HERE' \
  ghcr.io/urfoundation/meso-miner:latest
```

**Key env vars:**
- `URNETWORK_PROFILE=auto` — Auto-tunes based on available RAM (balanced, lowmem, etc.)
- `URNETWORK_RAMLOGS=1` — In-memory logging for fast diagnostics (view with `urnet-docker logs`)
- `URNETWORK_AUTH_CODE` — Auth code is exchanged for your JWT token, obtained from https://ur.io (single-use on first run; saved to volume)
- `PROXY_URL` — Optional live proxy list URL (comma-separated for multiple), additive with the mounted `proxy.txt`. See [Proxy URL Sources](docs/Proxy-URL-Sources.md).
- `UR_API_URL` / `UR_CONNECT_URL` — Point at a custom API + connect backend instead of `bringyour.com`. Must be set together; saved to the `~/.urnetwork` volume so it survives restarts. See [Configuration Reference](docs/Configuration.md).

> [!TIP]
> Providers do not require any listening ports. Outbound connections handle all traffic. If you wish to enable the optional vnstat web monitor, see [Running with vnstat](docs/Docker-Deployment.md#-optional-running-with-vnstat-bandwidth-monitor).

See [Docker Deployment](docs/Docker-Deployment.md) for Docker Compose, email/password auth, Watchtower, multi-container, and advanced options.

> [!NOTE]
> **Docker Management** — Use `urnet-docker` directly on the host (no `docker exec` wrapping needed):
> - `urnet-docker status`
> - `urnet-docker direct status` (or `urnet-docker direct off` for proxy-only mode)
> - `urnet-docker usage` (or `urnet-docker usage graphs` for time-series history)
> - `urnet-docker proxy add ~/proxies.txt`
> - `cat proxies.txt | urnet-docker proxy paste`
> - `urnet-docker proxy traffic`

---

## 🔧 Common Operations

| Command | Use this when... |
| :--- | :--- |
| `urnetwork auth` | You need to log in or refresh your identity manually |
| `urnet-tools direct [on\|off\|status]` | You want to check or toggle native direct IP providing (`off` = proxy-only stealth) |
| `urnet-tools usage [graphs]` | You want to view persistent traffic accounting (billable relay vs control plane split) |
| `urnet-tools proxy add <path\|url>` | You want to add proxies from a file (straight path or `--file=`) or URL source |
| `urnet-tools proxy paste < file` | You want to stream raw proxies from stdin or a pipe into the provider |
| `urnet-tools proxy trim <count>` | You want to enforce a hard cap, shedding worst A-F reachability graded proxies first |
| `urnet-tools proxy traffic` | You want to see active clients, bandwidth, and **Max Age** per proxy |
| `urnet-tools proxy health` | You need to see which proxies are `DEAD` vs `DEGRADED` vs `UP` |
| `urnet-tools logs` | You want to stream the current RAMLOGS buffer |
| `urnet-tools optimize` | You just added many proxies and need to tune kernel `ulimits` |
| `urnet-tools summary` | You want a single-pane fleet overview -- sources, health, URL cache status |
| `urnet-tools proxy refresh` | You updated your proxy list and want the node to reload live |
| `urnet-tools hot-restart on/off` | Toggle client JWT reuse across restarts (on by default; `off` sets `URNETWORK_HOT_RESTART=0`) |
| `urnet-tools set [<key> [<value>]]` | Show or change a runtime tuning override live, without editing a drop-in or restarting |
| `urnet-tools hotswap` | Swap to an updated binary without a gap where no process is running (needs a `Type=notify` unit; otherwise `update` falls back to a restart). Proxy connections still ramp back over about 30 s. Procedure and measured costs: [docs/HotSwap.md](docs/HotSwap.md) |
| `urnet-tools config [--json]` | Show every provider setting with the source it came from, so you can see which writer won |
| `urnet-tools history [limit]` | Read the provider's command audit trail, now including lifecycle events (start, hotswap, shutdown) alongside `set`/`clear` changes |
| `urnet-tools dashboard` | Terminal status panel: state, active settings, proxy sources, restart warnings |
| `urnet-tools metrics on/off` | Toggle the Prometheus `/metrics` endpoint live, no restart |
| `urnet-tools profile [name]` | Show or set the memory and GC tuning profile |
| `urnet-tools proxy ids` | Show the `client_id` the platform assigned to each proxy, including `direct` |
| `urnet-tools rename <name>` | Set the dashboard display label without touching the hostname |
| `urnet-tools show-ip [on\|off\|status]` | Control whether the public IP is appended to that dashboard label (was `ip-detect`) |
| `urnet-tools providers [--all]` | List the providers on this box; `--all` (as root) covers every OS user |
| `urnet-tools session save <file>` | Export identity+proxy state as encrypted bundle (cross-machine transfer) |
| `urnet-tools session load <file>` | Import identity+proxy state, then restart |
| `urnetwork choose_network <api_url> <connect_url>` | You run your own API/connect backend and want the provider to default to it |
| `urnetwork choose_network --reset` | You want to clear a saved custom network and revert to the main network |

> [!TIP]
> `~/proxies.txt` and `/home/user/proxies.txt` are both valid straight path formats across all tools.

---

## 📡 Telemetry

UrNetwork Connect provides rich standalone metrics directly via `urnet-tools usage` and `urnet-docker usage` (billable vs control plane accounting with hour/day/month historical graphs).

Prometheus metrics are built in. `urnet-tools metrics on` turns them on without a
restart and prints the address to scrape: loopback plus the machine's Tailscale
address by default, or any address you choose with `urnet-tools metrics listen`.
The `monitoring/` bundle runs Prometheus and Grafana with a ready-made fleet
dashboard. See [Monitoring](docs/Monitoring.md).

---

## 💡 Recommended Defaults

- Use the **Linux installer** for a host-managed systemd service
- Use **Docker** if you prefer containers — both are fully documented
- Leave profile on **`auto`** unless you have a specific reason to override
- Mount `/root/.urnetwork` as a persistent volume in Docker deployments
- Run `urnet-tools optimize` after adding a large proxy list, or when the System Auditor flags kernel limits

---

## 📚 Documentation

**In-repo:**

- [Installation](docs/Installation.md)
- [Docker Deployment](docs/Docker-Deployment.md)
- [Multi-Container Scaling](docs/Multi-Container-Scaling.md)
- [Configuration Reference](docs/Configuration.md)
- [Node Identity & Dashboard Label](docs/Node-Identity.md)
- [Proxy Management & Hot-Reload](docs/Proxy-Management.md)
- [High-Volume Performance Tuning](docs/High-Volume-Performance-Tuning.md)
- [Monitoring](docs/Monitoring.md)
- [Project Structure](docs/Project-Structure.md)
- [Log Message Reference](LOG_REFERENCE.md)
- [Go urnet-tools Reference](docs/urnet-tools-go.md)
- [Changelog](CHANGELOG.md)

---

## 🏗 Build Info

- **Base engine:** the 3.23-fix provider line, brought level with it by the v34 parity port. The stock UrNetwork provider is the comparison point in the table above
- **Language:** Go 1.27, compiled on Alpine
- **Platforms:** Linux (systemd, and Alpine/OpenRC with a native boot-start service), macOS, Windows and FreeBSD. Alpine setup: [docs/OpenRC.md](docs/OpenRC.md); FreeBSD setup: [docs/FreeBSD.md](docs/FreeBSD.md)
- **Images:** Multi-arch `linux/amd64` + `linux/arm64`, `darwin/amd64` + `darwin/arm64` via GitHub Actions → GHCR
- **Bridge-friendly:** runs on standard Docker bridge networks, no `--network host` required

---

> [!NOTE]
> meso-miner is a custom build for professional provider use. It is not affiliated with the official UrNetwork project.
