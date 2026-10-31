# Run a provider as an extender

A provider can also serve the extender role. The role is opt-in and off by default. The serving wiring has landed, but the role is not verified in production and does not activate there. When it runs, it accepts inbound carrier connections, and forward requests are limited to destinations in its allow list.

## Before you start

The role runs from the provider's direct slot because that slot uses this host's address. Configured proxies do not prevent the role from running while direct providing is enabled. If direct providing is disabled, the role does not start and the provider continues without it.

`DISABLE_DIRECT_IP=1` disables direct providing at startup unless a runtime direct setting overrides it. When the direct slot is disabled, the provider logs:

```text
[extender] role not started: direct providing is disabled
```

The role keeps its identity in `~/.urnetwork/.provider.extender.key`. It creates the file on first use with mode `0600`. In Docker, persist `/root/.urnetwork` so the identity survives container recreation.

## Carrier ports

The provider serves these carriers:

- TCP 443 for the TLS carrier.
- UDP 443 for QUIC.
- UDP 4053 for DNS.

The optional setting `URNETWORK_EXTENDER_DNS53=on` also enables DNS on UDP 53. Port 4053 remains the standard DNS carrier. If port 53 cannot be bound, the provider keeps 4053.

A bind failure does not stop the provider. If TCP 443 is unavailable while UDP carriers are serving, the extender state is `tcp_unavailable` and the provider retries TCP no faster than every three minutes. Binding port 443 on a bare-metal host requires root or `CAP_NET_BIND_SERVICE`.

The container must publish the ports you intend to use, and the host firewall or upstream router must allow inbound traffic to them. Publishing a Docker port does not open an upstream firewall or router.

## Choose which destinations to forward

Set `URNETWORK_EXTENDER_ALLOWED_HOSTS` to a comma-separated list of exact hostnames and `*.domain` patterns. An empty list refuses every forward request. A wildcard matches subdomains, but not the bare domain.

For example, this allows `example.com` and subdomains of `example.org`:

```sh
URNETWORK_EXTENDER_ALLOWED_HOSTS='example.com,*.example.org'
```

When the list is empty, the provider logs:

```text
[extender] no forward hosts configured (URNETWORK_EXTENDER_ALLOWED_HOSTS); every forward request will be refused
```

## Docker

The default Docker examples do not publish extender ports. To enable the role, add the environment settings, port mappings and persistent state volume:

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

When no allow list is configured, the provider logs the warning shown above. If TCP 443 is unavailable but other carriers are listening, the role reports `tcp_unavailable` in its status and in the `urnet_extender_state` metric. The `urnet_extender_carrier_listening` metrics show which of TCP, QUIC and DNS are listening.

See [Log Message Reference](/urfoundation/meso-miner/blob/main/LOG_REFERENCE.md) for the extender log messages and [Configuration](/urfoundation/meso-miner/wiki/Configuration) for the environment settings.
