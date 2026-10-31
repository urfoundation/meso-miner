# Next release: draft (urfoundation meso-miner)

**Status:** draft. It covers everything merged after `v2026.10.24-1080497440-meso` on `main`, through `4506731cd` (merge of #63). Nothing is tagged or pushed. The next tag is not chosen, so this file keeps its staging name.
**Note:** this repository has no release workflow. The release is cut by hand, so rename this file to `releases/<tag>.md` at the cut and attach it to the release.
**Sourcing:** written from the CHANGELOG `[Unreleased]` section and the commit subjects in `v2026.10.24-1080497440-meso..HEAD`. Not re-verified line by line.

Legend: **[redeploy]** needs the built artifact redeployed. **[installer]** needs the installer or unit refresh. **[no redeploy]** docs, CI or tests only.

## Extender (not active in production)

- **The extender stack lands; the serving role is unproven in production** **[redeploy]** ([#289](https://github.com/full-bars/meso-miner/pull/289), [#290](https://github.com/full-bars/meso-miner/pull/290)). The extender v2 library, feed and gossip layer and pinned directory candidate are ported from 3.23-fix. The provider's serving-role wiring (`URNETWORK_EXTENDER`, forwards limited by `URNETWORK_EXTENDER_ALLOWED_HOSTS`) is opt-in. The serving role does not activate in production and has not been verified there. `provider/extender_role.go` says it does not implement activation, the directory, gossip or probes.
- **The TLS ClientHello is a runtime switch** **[redeploy]** ([#289](https://github.com/full-bars/meso-miner/pull/289)). `urnet-tools set tls-hello on|off` applies to new connections. It is off by default while it soaks.

## Docker and provider

- **Docker startup keeps the saved proxy config when an import fails** **[redeploy]** (2326c8c8, ff69bf59, 6f1d7687, a4e57efe, 56104b33). Staged imports stay away from live state. Corrupt saved state is kept for recovery and no longer blocks startup. Startup stops only when no usable config is saved.
- **Docker debug logs redact credentials; nightly starts reuse the stored JWT** **[redeploy]** (32489225, 1662af74, c5aa058a, 47785a9b, b92662ab).
- **Provider proxy state changes hold the proxy lock** **[redeploy]** (5a93487d, 1510520d, d01c7df6, 921b9999). An unreadable `proxy.state` is reported, not masked, and a file proxy add keeps the source file's owner and mode.
- **Provider logs redact malformed addresses and raw keys** **[redeploy]** (1e915804).
- **Shutdown no longer waits behind a queued reload** **[redeploy]** (b98aa755).
- **A changed preset API URL triggers the stale JWT warning** **[redeploy]** (96a61b1e).
- **The governor charges H3 dials in bytes and admits proxied H3 under the attempt budget** **[redeploy]** (0a91e854, ad10c0ca). A canceled H3 attempt counts its bytes without counting as an attempt.
- **The degraded reaper says which hold stopped it** **[redeploy]** (f9057cee, b7ebef77).
- **The RAM-log trim does not hold the writer lock during the copy** **[redeploy]** (9b7ea765, 6e84da18, a5b5249b).
- **The URL fetch failure reason stays in the important log** **[redeploy]** (a48c7ca7, bbc48004).
- **OOM-cap state writes report a failure** **[redeploy]** (57aba3d6, dac1de3d).
- **The disk benchmark cache is tied to its sampling shape** **[redeploy]** (125a3d30, 714ec151).
- **The smart dialer costs nothing while it is off and is restart-required** **[redeploy]** (7b01ef21).
- **Unreadable RAM is classified by its source for the headroom cap** **[redeploy]** (25a7ad8d).
- **A thrash restart is marked as planned** **[redeploy]** (5b8866ef).

## urnet-tools and installers

- **The workstation flag is removed from `urnet-tools`** **[installer]** (49a31d42, 6c90f970). Signing has no gate, and seed use asks a person or refuses. A script that still passes `--i-am-on-my-own-workstation` gets a sentence naming the removed flag.
- **The FreeBSD installer refuses an asset whose digest cannot be established** **[installer]** (a1d5dcb1).
- **FreeBSD provider discovery and cron use the root-owned copy** **[installer]** (cffea783, 36ac726c, 03b529c0, e09861b2).
- **The FreeBSD installer never writes through a symlinked shell rc** **[installer]** (69006d0a).
- **The FreeBSD installer replaces its version file instead of following it, and accepts a staged binary that only lost its exec bit** **[installer]** (35a0de93, 2f4d0cb4).
- **`urnet-tools` on macOS takes the darwin path from the universal tarball; `logs --important` follows rotation** **[installer]** (b556feb1, 14f79bc6).
- **The hotkey wallet write finishes without a directory flush on Windows** **[redeploy]** (76a7686f, 0d9cb5f1).

## Security

- **The CFAA and IP blocker tables refreshed** **[redeploy]** (6e7a6875, 8004c71f). Data only; it takes effect once a node runs this release.

## CI and documentation

- **The scheduled live-numbers commits are signed** **[no redeploy]** (CHANGELOG `[Unreleased]`, full-bars PR 286).
- **The installer shell-rc test runs in CI** **[no redeploy]** (a70b6969).
- **Several CI jobs change scope** **[no redeploy]** (680491bd, 1f1407f1, 8787d74e, 74fa3420, 64834a42).
- **Bittensor live numbers refreshed** **[no redeploy]** (commits under `docs(bittensor)`).

## Deploy notes

1. Nodes on `h3 all`, a count or `auto` get the proxied-H3 budget change. Nodes on the default `h3 direct` are not affected by it.
2. `smart_dialer` is restart-required. `set smart_dialer on` takes effect at the next start.
3. The extender role and the Chrome ClientHello are both off unless set.
