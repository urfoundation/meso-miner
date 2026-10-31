# Extender role (work in progress, not active)

The extender role is a work in progress. It does not activate yet, so no provider serves as an extender. The role is opt-in and off by default. The wiring has landed: setting `URNETWORK_EXTENDER=on` starts the role's listeners on the direct slot. Activation, the directory, gossip and probes are not implemented in this lane (`provider/extender_role.go:35-37`), so enabling the role does not make the provider an extender.

The sections below describe what the role would need once activation is implemented. They are not a working setup guide.

## Before you start

The role runs from the provider's direct slot because that slot uses this host's address. Configured proxies do not prevent the role from running while direct providing is enabled. If direct providing is disabled, the role does not start and the provider continues without it.

`DISABLE_DIRECT_IP=1` disables direct providing at startup unless a runtime direct setting overrides it. When the direct slot is disabled, the provider logs:

```text
[extender] role not started: direct providing is disabled
```

The role keeps its identity in `~/.urnetwork/.provider.extender.key`. It creates the file on first use with mode `0600`. In Docker, persist `/root/.urnetwork` so the identity survives container recreation.

## Carrier ports

The role would need these carriers:

- TCP 443 for the TLS carrier.
- UDP 443 for QUIC.
- UDP 4053 for DNS.

The optional setting `URNETWORK_EXTENDER_DNS53=on` also enables DNS on UDP 53. Port 4053 remains the standard DNS carrier. If port 53 cannot be bound, the provider keeps 4053.

A bind failure does not stop the provider. If TCP 443 is unavailable while UDP carriers are serving, the extender state is `tcp_unavailable` and the provider retries TCP no faster than every three minutes. Binding port 443 on a bare-metal host requires root or `CAP_NET_BIND_SERVICE`.

The container must publish the ports you intend to use, and the host firewall or upstream router must allow inbound traffic to them. Publishing a Docker port does not open an upstream firewall or router.

## Choose which destinations to forward

Set `URNETWORK_EXTENDER_ALLOWED_HOSTS` to a comma-separated list of exact hostnames and `*.domain` patterns. An empty list refuses every forward request. A wildcard matches subdomains, but not the bare domain. The list has no effect until forwarding is implemented.

For example, this allows `example.com` and subdomains of `example.org`:

```sh
URNETWORK_EXTENDER_ALLOWED_HOSTS='example.com,*.example.org'
```

When the list is empty, the provider logs:

```text
[extender] no forward hosts configured (URNETWORK_EXTENDER_ALLOWED_HOSTS); every forward request will be refused
```

## Docker

The default Docker examples do not publish extender ports. The example below starts the role's listeners with the environment settings, port mappings and persistent state volume. It does not make the provider an extender:

```sh
docker run -d \
  --name=urfix \
  --pull=always \
  --restart=unless-stopped \
  --cap-add=NET_ADMIN \
  --cap-add=NET_RAW \
  --sysctl net.ipv4.ip_forward=1 \
  -p 443:443/tcp \
  -p 443:443/udp \
  -p 4053:4053/udp \
  -e BUILD=jwt \
  -e URNETWORK_EXTENDER=on \
  -e URNETWORK_EXTENDER_ALLOWED_HOSTS='example.com,*.example.org' \
  -v urfix_config:/root/.urnetwork \
  ghcr.io/urfoundation/meso-miner:latest AUTH_CODE_HERE
```

Replace `AUTH_CODE_HERE` with the one-time auth code used by the existing Docker examples. The named volume keeps the JWT and extender identity across container recreation. To enable the optional DNS carrier on port 53, also set `URNETWORK_EXTENDER_DNS53=on` and publish `53:53/udp` if that port is available on the host.

For the other image options and authentication modes, see [Docker Deployment](/urfoundation/meso-miner/wiki/Docker-Deployment).

## Check the role

When no allow list is configured, the provider logs the warning shown above. If TCP 443 is unavailable but other carriers are listening, the role reports `tcp_unavailable` in its status and in the `urnet_extender_state` metric. The `urnet_extender_carrier_listening` metrics show which of TCP, QUIC and DNS are listening. These fields report listener state only. They do not show that the role serves forwards.

See [Log Message Reference](/urfoundation/meso-miner/blob/main/LOG_REFERENCE.md) for the extender log messages and [Configuration](/urfoundation/meso-miner/wiki/Configuration) for the environment settings.
