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

`bin/bootstrap` installs Python via mise (if available), creates `.venv`, installs the package in editable mode with dev dependencies, and copies `monitor/integrations.example.yaml` to `monitor/integrations.yaml` when that file does not exist.

`bin/serve` runs `monitor run` with:

- `--conf monitor/integrations.yaml` (override with `CONF_FILE`)
- `--log-level debug` (override with `LOG_LEVEL`)

When `outputs.websocket` is enabled it also starts the HTML client frontend:

- WebSocket UI: `http://127.0.0.1:8080/` (or your configured host/port)
- HTML client: `http://127.0.0.1:8090/` (override with `UI_HOST` / `UI_PORT`)

Set `SERVE_CLIENT=0` to skip the HTML client and use only the WebSocket UI.
## Make and mise

```shell
make bootstrap
make serve          # same as bin/serve
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

With WebSocket output enabled in config, `bin/serve` brings up both UIs:

- `http://localhost:8080/` — live JS status page (served by the monitor)
- `http://localhost:8090/` — Python HTML client (Jinja2 first paint, live updates)

```shell
bin/serve
# SERVE_CLIENT=0 bin/serve   # WebSocket UI only
# UI_PORT=8091 bin/serve     # change HTML client port
```

Or run the HTML client yourself against an already-running monitor:

```shell
monitor client --server http://127.0.0.1:8080
# open http://127.0.0.1:8090/
```

Module form:

```shell
python -m monitor run --conf monitor/integrations.yaml
python -m monitor check-config
```

## Mock vs real GPIO

On your development machine, Python runs without `-O`, so the mock GPIO module is used. On the Pi, run with `python -O` so the real `RPi.GPIO` library is loaded.

See [Raspberry Pi](raspberry-pi.md) for hardware setup and systemd.
