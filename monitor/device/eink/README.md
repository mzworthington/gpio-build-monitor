# Shared e-ink snapshot parser

Host-tested `GET /status?view=eink` JSON parser and list-row helpers for the
CrossPoint **Build monitor** activity (`apps/monitor/`). Submodule:
[`crosspoint/`](crosspoint/). Architecture: [docs/xteink-x3.md](../../docs/xteink-x3.md).

```shell
make test          # from this directory
make test-eink     # from the repo root
```

Flash the overlay (build, then tight esptool loop; do not use `pio upload`):

```shell
monitor/device/eink/apps/monitor/flash.sh
```
