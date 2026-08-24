# AI Guide — Meso-Miner Provider

This file is designed for an AI agent to read so it can help users install, configure, and manage the provider. It references the project's existing documentation rather than duplicating it. Give this file to your AI alongside the linked docs below.

## Project Layout

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for the full directory layout. Quick orientation:

- `provider/` — the traffic-relay binary that serves proxies and earns money
- `cmd/urnet-tools` + `cmd/urnet-docker` + `internal/urnettools/` — the provider-aware Go fleet-ops tool (v3.23.0-fix.27.0+; the shell installer `scripts/Provider_Install_Linux.sh` remains the installer but no longer doubles as the CLI)
- `docs/` — user-facing documentation (Installation, Configuration, Proxies, etc.)
- `Dockerfile` — provider Docker image

## Quick Start: Install the Provider

```bash
curl -fsSL https://dl.fullbars.xyz/install.sh | sh
```

The same script becomes the `urnet-tools` CLI after installation. Full install docs: [docs/Installation.md](docs/Installation.md).

### Authenticate

You need an **auth code** from the URnetwork website. The provider exchanges it for a JWT.

```bash
urnet-tools auth                    # interactive — paste auth code at prompt
urnet-tools auth <auth-code>        # non-interactive
urnet-tools auth <jwt>              # or paste a JWT directly
```

Docker deployments can use email/password instead (see [Docker Deployment](docs/Docker-Deployment.md)), which the container exchanges for a JWT internally.

### Add Proxies

```bash
urnet-tools proxy add file proxies.txt     # one ip:port per line
urnet-tools proxy add url https://...      # auto-refreshing URL source
urnet-tools proxy summary                  # fleet-wide proxy overview
```

Full proxy docs: [docs/Proxy-Management.md](docs/Proxy-Management.md), [docs/Proxy-URL-Sources.md](docs/Proxy-URL-Sources.md).

## Docker Deployment

Full guide: [docs/Docker-Deployment.md](docs/Docker-Deployment.md).

```bash
docker pull ghcr.io/full-bars/urnetwork-3.23-fix:latest
docker run -d \
  -e USER_AUTH=email@example.com \
  -e PASSWORD=secret \
  -v /path/to/proxies.txt:/app/proxies.txt:ro \
  ghcr.io/full-bars/urnetwork-3.23-fix:latest
```

## Performance Tuning

Full guide: [docs/High-Volume-Performance-Tuning.md](docs/High-Volume-Performance-Tuning.md).

```bash
urnet-tools turbo v8          # high-throughput profile
urnet-tools auto on           # auto-tune based on detected RAM
urnet-tools eco on            # low-memory GC tuning
urnet-tools optimize          # apply OS kernel limits (ulimit, conntrack, etc.)
urnet-tools ramlogs on        # redirect logs to /dev/shm (RAM disk)
```

## Reference: All urnet-tools Commands

```bash
# Auth & Setup
urnet-tools auth                    # interactive — paste auth code
urnet-tools auth <auth-code>        # non-interactive
urnet-tools update                  # update provider binary
urnet-tools reinstall              # full reinstall
urnet-tools choose_network <api_url> <connect_url>  # save a custom API/connect backend
urnet-tools choose_network --reset  # clear saved custom network, revert to main network

# Proxy Management
urnet-tools proxy add file <path>  # bulk add from file
urnet-tools proxy add url <url>    # auto-refreshing URL source
urnet-tools proxy remove <addr>    # remove specific proxy
urnet-tools proxy remove --match <pattern>  # pattern-based removal
urnet-tools proxy remove-dead      # interactive dead proxy cleanup
urnet-tools proxy refresh          # hot-reload proxies (no restart)
urnet-tools proxy clear            # remove all proxies
urnet-tools proxy summary          # fleet-wide proxy overview
urnet-tools proxy health           # dead/degraded proxy list
urnet-tools proxy traffic          # real-time bandwidth & clients

# Performance
urnet-tools turbo v4|v8|off        # throughput profile
urnet-tools auto on|off            # auto-tune profile
urnet-tools eco on|off             # low-memory GC mode
urnet-tools lowmode on|off         # reduced buffer allocations
urnet-tools optimize               # apply Golden Fleet OS limits
urnet-tools ramlogs on|off         # RAM-disk logging

# Maintenance
urnet-tools start|stop|restart|status  # service management
urnet-tools logs [all|dump|-i]     # stream logs (-i = important only)
urnet-tools uninstall              # full removal

# Experimental
urnet-tools hot-restart on|off     # client JWT reuse (default off)
urnet-tools fast-auth on|off       # bypass auth rate limiter
```

## Environment Variables

Full reference: [docs/Configuration.md](docs/Configuration.md).

Key variables:
| Variable | Purpose |
|----------|---------|
| `USER_AUTH` / `PASSWORD` | Email/password auth |
| `URNETWORK_AUTH_CODE` | JWT auth code (first-run) |
| `UR_API_URL` / `UR_CONNECT_URL` | Custom API/connect backend (must be set together, Docker only) |
| `ENABLE_VNSTAT` | Traffic monitor on port 8080 |
| `URNETWORK_PROFILE` | `auto` (tiers: low/balanced/perf/extreme), `lowmem`, `eco`, `turbo-v4`, `turbo-v8` |
| `PROXY_URL` | Live proxy URL feed (comma-separated) |
| `URNETWORK_HEALTH_INTERVAL` | Health heartbeat interval |
| `URNETWORK_RAMLOGS` | `1` = log to /dev/shm |
| `URNETWORK_SKIP_AUDIT` | `1` = skip startup system audit (disk speed, ulimit, conntrack checks) |
| `URNETWORK_HOT_RESTART` | `1` = experimental client JWT reuse |

## Release & Versioning

- `urnet-tools update` resolves "latest" to the newest release tag
- `urnet-tools update` resolves "latest" to the newest release tag
- Release notes in `releases/` directory

## Key Files

| Path | Purpose |
|------|---------|
| `~/.local/share/urnetwork-provider/bin/urnetwork` | Provider binary |
| `~/.local/share/urnetwork-provider/bin/urnet-tools` | CLI tool |
| `~/.config/systemd/user/urnetwork.service` | Provider systemd unit |
| `~/.config/systemd/user/urnetwork.service.d/override.conf` | Provider env overrides |
| `/dev/shm/urnetwork.log` | Provider ramdisk log (when ramlogs enabled) |

## Troubleshooting

## Documentation Index

| Doc | Covers |
|-----|--------|
| [Installation](docs/Installation.md) | Bare-metal install, post-install setup |
| [Docker Deployment](docs/Docker-Deployment.md) | Docker run, Compose, Watchtower, scaling |
| [Configuration](docs/Configuration.md) | Complete env var reference, profiles |
| [Proxy Management](docs/Proxy-Management.md) | Hot-reload, stable slots, dead cleanup |
| [Proxy URL Sources](docs/Proxy-URL-Sources.md) | Live proxy feeds, dedup, cleanup |
| [Performance Tuning](docs/High-Volume-Performance-Tuning.md) | Profiles, optimizer, parameters |
| [Troubleshooting](docs/Troubleshooting.md) | Exit codes, errors, resource issues |
| [Project Structure](PROJECT_STRUCTURE.md) | Directory layout, architecture |
| [Log Reference](LOG_REFERENCE.md) | Every log line documented |
| [Fork Changes](FORK_CHANGES.md) | All ~66 modifications from upstream |
