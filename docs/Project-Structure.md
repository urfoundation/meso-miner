# Project Structure

This is a map of the meso-miner repository, grouped by what each part is for. Most operators never need it: if you only run a provider, start with the [README](../README.md).

meso-miner is a Go module (`github.com/urnetwork/connect`, Go 1.27). The network library sits in the repository root, and the programs built on it live in sub-folders.

```
meso-miner/
│
│  PROGRAMS (what you install and run)
├── provider/                  The provider: the relay node that earns for you
├── cmd/
│   ├── urnet-tools/           The management tool for a host (install, update, status, proxies)
│   ├── urnet-docker/          The same tool for Docker hosts; runs on the host, not in the container
│   └── fake-provider/         A stand-in provider used only by CI tests
├── internal/
│   ├── urnettools/            The code behind urnet-tools and urnet-docker
│   ├── tui/                   Terminal drawing used by `urnet-tools top`
│   ├── verdictfeed/           Reads the provider verdict feed
│   ├── promtext/              Checks Prometheus metric text
│   └── durable*/              Test and support code for durable volume storage
├── connectctl/                Small local helper for talking to a connect server
├── blocker/                   Generator for the built-in ad and tracker block lists
│
│  SHIPPING (images, installers, monitoring)
├── Dockerfile                 Alpine multi-arch provider image (amd64, arm64)
├── docker/scripts/            Container start-up: entrypoint.sh picks the mode, start_*.sh set it up
├── scripts/                   Installers and uninstallers (Linux, macOS, Windows, FreeBSD), the Docker
│                              tool installer, and tag helpers (compute-meso-tag.sh, pre-tag-check.sh)
├── pelican/                   Egg for Pelican game-server panels
├── monitoring/                Prometheus and Grafana bundle (docker-compose, dashboard, alert rules)
│
│  NETWORK LIBRARY (the root package; the same stack the stock provider uses)
├── transport*.go              Connections to the platform: WebSocket (H1, H1+), QUIC/H3, WebRTC, DNS tunnel
├── transfer*.go               Contracts, sending and receiving, encryption, routing, round-trip timing
├── ip*.go                     Packet relay, NAT, fragments, ICMP, UDP sockets, and the security policy
├── net*.go, egress*.go        Dialing, DNS-over-HTTPS, resilient connections, which network a dial leaves on
├── control_family*.go         Which IP family (v4 or v6) control connections use
├── reconnect_*.go             Limits on how fast the provider reconnects
├── proxy_*.go                 Proxy health, scoring and target families
├── message_pool.go            Reusable buffers that keep memory churn down
├── tuning.go, memory_budget.go  Memory profiles chosen from the machine's RAM
├── metrics_prometheus.go      Prometheus metrics
├── audit*.go, log*.go         Host checks and logging
├── api*.go, jwt.go            Platform API client and sign-in tokens
├── verify_wire.go, govern_*.go  Wire formats for route verification and the governor feed
├── *_test.go                  Tests
│
│  PROTOCOL AND DATA
├── protocol/                  .proto files and generated Go code (do not edit the generated files)
├── api/bringyour.yml          API description
├── security/                  Script and source list for the IP block data
├── extender/                  Extender (relay helper) library
├── hotkeywallet/              Wallet consent chain for several operators
├── durablesys/, durablevolume/  Storage and volume leases for durable state
├── emoji/                     Emoji names used for readable node labels
├── third_party/               Vendored libraries (Substrate RPC client, named pipes)
├── testdata/                  Test fixtures
│
│  DOCUMENTATION
├── README.md                  Start here
├── docs/                      Operator guides (published to the wiki by wiki-sync.yml)
│   ├── guides/                Beginner, intermediate and advanced walkthroughs
│   └── design/                Design notes for larger features
├── LOG_REFERENCE.md           What each log line means
├── CHANGELOG.md               What changed in each release
├── FORK_CHANGES.md            Detailed history of every change this line made to the stock code
├── MIGRATION_PLAN.md          Historical plan for the move to the H3 engine
├── releases/                  Per-release notes
├── AI.md, CODESTYLE.md        Notes for people and tools changing the code
│
│  BUILD AND AUTOMATION
└── .github/
    ├── workflows/             Build, release, shakedown, lifecycle, CodeQL, wiki-sync and blocklist-sync jobs
    ├── scripts/               Helpers used by those workflows
    └── RELEASE_TEMPLATE.md    Template for release notes
```

## The provider (`provider/`)

`provider/main.go` is the command-line entry point (`auth`, `provide`, `proxy`, `claim`, `sn-status` and more). Around it, by purpose:

| Area | Files |
|---|---|
| Proxies: loading, state, hot-reload | `proxy_url*.go`, `proxy_reload.go`, `proxy_state.go`, `proxy_id.go`, `proxy_match.go`, `proxy_paste.go` |
| Proxies: health, grading and limits | `proxy_probe.go`, `proxy_udp_check.go`, `proxy_health_log.go`, `proxy_grade_*.go`, `proxy_trim.go`, `proxy_scout.go`, `proxy_slow_retry.go`, `proxy_failure_history.go`, `proxy_auth_history.go` |
| Sign-in pacing | `auth_rate_limiter.go`, `proxy_admission_gate.go`, `network_refresh.go` |
| Identity and restarts | `client_jwt_store.go`, `hotswap*.go`, `control_socket.go`, `pending_overrides*.go`, `restart_reason.go` |
| Transport choices | `family_transport.go`, `h3_*.go`, `direct.go`, `socks5_udp.go` |
| Subnet 25 and wallets | `sn*.go`, `claim_*.go`, `bt_*.go`, `fleet*.go`, `hotkey_wallet.go`, `wallet_*.go` |
| Safety and self-healing | `thrash_watchdog.go`, `mempressure*.go`, `liveness_*.go`, `oom_cap.go`, `loop_supervisor.go` |
| Logs and metrics | `shmlog_*.go`, `critlog.go`, `important_log.go`, `startup_banner.go`, `metrics_*.go`, `node_snapshot*.go`, `earn_tracker.go` |
| DNS | `doh_cache.go` |

## urnet-tools (`cmd/urnet-tools` and `internal/urnettools/`)

The operator tool, written in Go. It finds providers (systemd, OpenRC, launchd, Windows, FreeBSD, containers), manages their life cycle, updates the provider and itself with checksum verification, and shows status. Main parts:

| Area | Files |
|---|---|
| Commands and help | `cli.go`, `cobra.go`, `cobra_docker.go`, `legacy_cmds.go` |
| Finding providers | `discover*.go`, `target.go`, `select_multi.go`, `provider.go` |
| Start, stop, restart, install | `lifecycle_*.go`, `openrc*.go`, `restart_*.go` |
| Updates | `update.go`, `idle_update.go`, `release.go`, `hotswap*.go` |
| Proxies, sessions, settings | `proxy.go`, `session_cmds.go`, `control_client.go`, `config.go`, `self_heal.go` |
| Live views | `top_*.go`, `snapshot*.go`, `usage*.go`, `metrics_status.go`, `baseline.go`, `sn_status.go` |
| Docker | `docker*.go`, `cli_docker.go` |

## About fleet reporting

The old Hub dashboard and its `hub` commands are gone. For a view across many machines, turn on Prometheus metrics with `urnet-tools metrics on` and use the [Monitoring](Monitoring.md) bundle with Grafana. A leftover `bandwidth_reporter.go` and `report_url` setting remain in the code, but nothing receives their reports.
