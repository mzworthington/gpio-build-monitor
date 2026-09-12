# Getting started

## Prerequisites

- Python 3.10+ ([mise](https://mise.jdx.dev/) is recommended; this repo pins 3.12)
- API tokens for the CI providers you configure - see [Configuration](configuration.md#environment-variables)

## Bootstrap

```shell
bin/bootstrap
cp monitor/integrations.example.yaml monitor/integrations.yaml   # skipped if bootstrap already created it
# edit monitor/integrations.yaml and export tokens
monitor check-config
bin/serve
```

`bin/bootstrap` installs Python via mise (if available), creates `.venv`, installs the package in editable mode with dev dependencies, and copies `monitor/api/monitor/integrations.example.yaml` to `monitor/api/monitor/integrations.yaml` when that file does not exist.

`bin/serve` is a full local setup. It loads `.env` if present, then:

1. Installs frontend deps (`pnpm install`) when `monitor/device/web/node_modules` is missing
2. Builds the TypeScript UI (`pnpm build:web`)
3. Starts `monitor run` — Python API (`/api/status`, `/api/ws`) plus the Alpine UI on `/`

Open:

- Python API + Alpine UI: `http://127.0.0.1:8080/` (from `outputs.websocket`)
- Snapshot: `http://127.0.0.1:8080/api/status`

Hosted UI is Cloudflare Pages at `/`; `/api*` proxies to the Python aggregator.

## Make and mise

```shell
make bootstrap
make serve          # Python API + Alpine UI on the websocket port
make test           # ruff + pytest
make publish        # lint, test, then build sdist/wheel
```

With mise:

```shell
mise run bootstrap
mise run serve
mise run test
```

## CLI

The `monitor` command is provided by [Typer](https://typer.tiangolo.com/):

```shell
monitor --help
monitor run --conf monitor/integrations.yaml --log-level debug
monitor check-config --conf monitor/integrations.yaml
```

- `monitor run` - start the refresh loop (timed poll, optional webhook wake-ups)
- `monitor check-config` - validate config and required environment variables without starting outputs

With WebSocket output enabled in config, `bin/serve` brings up the Python API and Alpine UI on the same origin:

- `http://localhost:8080/` — Alpine status page
- `http://localhost:8080/api/status` — JSON snapshot
- `ws://localhost:8080/api/ws` — live status

```shell
bin/serve
```

Module form:

```shell
python -m monitor run --conf monitor/integrations.yaml
python -m monitor check-config
```

## Mock vs real GPIO

On your development machine, Python runs without `-O`, so the mock GPIO module is used. On the Pi, run with `python -O` so the real `RPi.GPIO` library is loaded.

See [Raspberry Pi](raspberry-pi.md) for hardware setup and systemd.

Menu bar on a Mac: [Mac menu bar](macos.md) (SwiftBar + `GET /status`).

Battery e-ink (Xteink X3): [Xteink e-ink](xteink-x3.md) (CrossPoint overlay + `GET /status?view=eink`).
