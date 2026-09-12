# Pi setup (headless)

Headless deployment: Raspberry Pi drives **GPIO LEDs** by following the hosted
Build Monitor API (`https://monitor.mzworthington.co.uk/api`). CI polling lives
on the Cloudflare Worker. The public website is Cloudflare Pages. You do
**not** need Cloudflare Tunnel, GitHub tokens, or `integrations.yaml` on the Pi.

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

## 3. Environment

```shell
sudo mkdir -p /etc/gpio-build-monitor /var/log/gpio-build-monitor
sudo cp monitor/device/pi/env.example /etc/gpio-build-monitor/env
sudo chmod 600 /etc/gpio-build-monitor/env
# optional: set MONITOR_API_ORIGIN if you are not using the default hosted API
```

## 4. GPIO follower systemd service

```shell
sudo cp monitor/device/pi/gpio-build-monitor.service /etc/systemd/system/
# edit WorkingDirectory / ExecStart / User if needed
sudo systemctl daemon-reload
sudo systemctl enable --now gpio-build-monitor
sudo systemctl status gpio-build-monitor
```

The unit runs `python -O -m gpio_pi`. LEDs track the hosted snapshot. No public
hostname is required for this path.

## 5. Optional: auto-updates

```shell
sudo cp monitor/device/pi/sudoers-gpio-build-monitor /etc/sudoers.d/gpio-build-monitor
sudo chmod 0440 /etc/sudoers.d/gpio-build-monitor
sudo cp monitor/device/pi/gpio-build-monitor-update.service /etc/systemd/system/
sudo cp monitor/device/pi/gpio-build-monitor-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gpio-build-monitor-update.timer
```

Ensure auto-update vars in `/etc/gpio-build-monitor/env` match [monitor/device/pi/env.example](../monitor/device/pi/env.example). More detail: [raspberry-pi.md](raspberry-pi.md#auto-updates).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| GPIO inert | Run with `python -O` (the systemd unit does); `RPi.GPIO` installed |
| Wrong API | `MONITOR_API_ORIGIN` in `/etc/gpio-build-monitor/env` |
| Service crash-loop | `journalctl -u gpio-build-monitor -n 80` |

## Files reference

| Path | Role |
|------|------|
| [monitor/device/pi/gpio_pi/](../monitor/device/pi/gpio_pi/) | GPIO follower package |
| [monitor/device/pi/gpio-build-monitor.service](../monitor/device/pi/gpio-build-monitor.service) | Follower process |
| [monitor/device/pi/env.example](../monitor/device/pi/env.example) | API origin + updater env |
| [monitor/device/web/](../monitor/device/web/) | Hosted website (separate deploy) |
| [infra/cloudflare](../infra/cloudflare) | Worker custom domain (laptop) |
