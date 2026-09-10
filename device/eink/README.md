# Shared e-ink duty cycle

Host-tested snapshot client logic used by [`device/x3/`](../x3/) and
[`device/x4/`](../x4/). Architecture: [docs/xteink-x4.md](../../docs/xteink-x4.md).

- `duty_cycle` — ETag, sleep, panel Full/Partial/Leave
- `client` — USB desk present, If-None-Match, idle cap
- `power_control` — page key vs power, latch, idle path
- `status_view` — labels, job titles, and CrossPoint list rows (`fill_monitor_lines`)

CrossPoint overlay (reader firmware + Build monitor activity):
[`apps/monitor/`](apps/monitor/). The submodule is [`crosspoint/`](crosspoint/).

```shell
make test          # from this directory
make test-x4       # from the repo root
```
