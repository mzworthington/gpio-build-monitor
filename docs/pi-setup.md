# Pi setup (headless)

Headless deployment: Raspberry Pi drives **GPIO LEDs** from the same CI config.
The public website is a **separate** Cloudflare Worker deployment — see
[worker/README.md](../worker/README.md) and [infra/cloudflare/README.md](../infra/cloudflare/README.md).
You do **not** need Cloudflare Tunnel for the hosted UI.

Assumes the repo lives at `/home/pi/gpio-build-monitor`. Adjust paths and the
`User=` lines in the systemd units if yours differ.

## 1. Clone and bootstrap

```shell
git clone https://github.com/mzworthington/gpio-build-monitor.git
cd gpio-build-monitor
bin/bootstrap
```

## 2. Hardware library

```shell
.venv/bin/pip install RPi.GPIO
```

## 3. Config and secrets

```shell
cp monitor/integrations.example.yaml monitor/integrations.yaml
# edit integrations (repos, pins). For headless Pi you can disable websocket:
#   outputs.websocket.enabled: false

sudo mkdir -p /etc/gpio-build-monitor /var/log/gpio-build-monitor
sudo cp monitor/integrations.yaml /etc/gpio-build-monitor/integrations.yaml
sudo cp deploy/env.example /etc/gpio-build-monitor/env
sudo chmod 600 /etc/gpio-build-monitor/env
# edit /etc/gpio-build-monitor/env — at least GITHUB_TOKEN / CIRCLE_CI_TOKEN
```

Validate:

```shell
.venv/bin/monitor check-config --conf /etc/gpio-build-monitor/integrations.yaml
```

See [configuration.md](configuration.md).

## 4. Monitor systemd service

```shell
sudo cp deploy/gpio-build-monitor.service /etc/systemd/system/
# edit WorkingDirectory / ExecStart / User if needed
sudo systemctl daemon-reload
sudo systemctl enable --now gpio-build-monitor
sudo systemctl status gpio-build-monitor
```

LEDs should track CI status. No public hostname is required for this path.

## 5. Optional: local WebSocket UI on the LAN

If you enable `outputs.websocket` on the Pi, the UI is available on the Pi’s
LAN IP (e.g. `http://192.168.x.x:8080`). That is independent of
`monitor.mzworthington.co.uk` (Worker).

## 6. Optional: auto-updates

```shell
sudo cp deploy/sudoers-gpio-build-monitor /etc/sudoers.d/gpio-build-monitor
sudo chmod 0440 /etc/sudoers.d/gpio-build-monitor
sudo cp deploy/gpio-build-monitor-update.service /etc/systemd/system/
sudo cp deploy/gpio-build-monitor-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gpio-build-monitor-update.timer
```

Ensure auto-update vars in `/etc/gpio-build-monitor/env` match [deploy/env.example](../deploy/env.example). More detail: [raspberry-pi.md](raspberry-pi.md#auto-updates).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| GPIO inert | Run with `python -O` (the systemd unit does); `RPi.GPIO` installed |
| Config errors | `.venv/bin/monitor check-config --conf /etc/gpio-build-monitor/integrations.yaml` |
| Service crash-loop | `journalctl -u gpio-build-monitor -n 80` |

## Files reference

| Path | Role |
|------|------|
| [deploy/gpio-build-monitor.service](../deploy/gpio-build-monitor.service) | Monitor process |
| [deploy/env.example](../deploy/env.example) | CI tokens + updater env |
| [worker/](../worker/) | Hosted website (separate deploy) |
| [infra/cloudflare](../infra/cloudflare) | Worker custom domain (laptop) |
