# Changelog

<!-- version list -->

## v0.9.0 (2026-08-10)

### Features

- Add web push alerts for FAIL status on hosted UI
  ([#19](https://github.com/mzworthington/gpio-build-monitor/pull/19),
  [`67ebc48`](https://github.com/mzworthington/gpio-build-monitor/commit/67ebc48ce1b4a818fc4471be8bf2d01ebcadb885))


## v0.8.0 (2026-08-09)

### Documentation

- Clarify optional webhook signature verification and update instructions
  ([`3005dc9`](https://github.com/mzworthington/gpio-build-monitor/commit/3005dc98d1f257504f58d1d8e832aa74731ef0e2))

### Features

- Add author credit link to DocsShell component
  ([`f4c0d36`](https://github.com/mzworthington/gpio-build-monitor/commit/f4c0d360eb50509df7058460d61b372aba9ca6df))


## v0.7.0 (2026-08-09)

### Features

- Enhance bin/serve with WebSocket UI and HTML client support
  ([`94dbe85`](https://github.com/mzworthington/gpio-build-monitor/commit/94dbe857468ddfff7acae45ecf911af411420b5d))


## v0.6.1 (2026-08-09)

### Refactoring

- Reorganize issue and repository sections in HTML templates
  ([`b6a6def`](https://github.com/mzworthington/gpio-build-monitor/commit/b6a6def59f3ec6799a6a58ea142d08ac056abd86))


## v0.6.0 (2026-08-09)

### Chores

- Update changelog
  ([`755a47c`](https://github.com/mzworthington/gpio-build-monitor/commit/755a47c9bc1bf4fdf9a4975e0e8d26c8fa76c667))

### Features

- Improve Dependabot handling and enhance websocket fetching logic
  ([`6685245`](https://github.com/mzworthington/gpio-build-monitor/commit/6685245a24bf11361b03b9ef70e29a6697825f59))


## v0.5.3 (2026-08-08)

### Chores

- Poll CI once per minute instead of every 15 seconds
  ([#14](https://github.com/mzworthington/gpio-build-monitor/pull/14),
  [`7277c8f`](https://github.com/mzworthington/gpio-build-monitor/commit/7277c8fd93ab1c23f96265b79665a27980e6f717))

### Continuous Integration

- Deploy Cloudflare Worker when UI or worker code changes
  ([#13](https://github.com/mzworthington/gpio-build-monitor/pull/13),
  [`dafa148`](https://github.com/mzworthington/gpio-build-monitor/commit/dafa1483adf243c5ae86ea50e7e7f86c6e8dbd81))

- Deploy hosted Worker from the main CI/CD workflow
  ([#13](https://github.com/mzworthington/gpio-build-monitor/pull/13),
  [`dafa148`](https://github.com/mzworthington/gpio-build-monitor/commit/dafa1483adf243c5ae86ea50e7e7f86c6e8dbd81))

- Fold Worker deploy into the main CI/CD workflow
  ([#13](https://github.com/mzworthington/gpio-build-monitor/pull/13),
  [`dafa148`](https://github.com/mzworthington/gpio-build-monitor/commit/dafa1483adf243c5ae86ea50e7e7f86c6e8dbd81))

### Documentation

- Note deploy-worker in the CI/CD job list
  ([#13](https://github.com/mzworthington/gpio-build-monitor/pull/13),
  [`dafa148`](https://github.com/mzworthington/gpio-build-monitor/commit/dafa1483adf243c5ae86ea50e7e7f86c6e8dbd81))


## v0.5.2 (2026-08-08)

### Bug Fixes

- Publish release wheels so Pi auto-updates can install
  ([#12](https://github.com/mzworthington/gpio-build-monitor/pull/12),
  [`f64faae`](https://github.com/mzworthington/gpio-build-monitor/commit/f64faaed8980ccdb31e4bbe1b5dab8f1eca01cf3))


## v0.5.1 (2026-08-08)

### Refactoring

- Enhance documentation and clarify deployment structure
  ([`ff3715a`](https://github.com/mzworthington/gpio-build-monitor/commit/ff3715a9f59e89c8a17ef3b7759a6b714fe596fc))


## v0.5.0 (2026-08-08)

### Features

- Show in scope repos and workflows
  ([`e28274d`](https://github.com/mzworthington/gpio-build-monitor/commit/e28274db302a66b92e2d8b11869bbdc50b2b8cee))

### Refactoring

- Enhance documentation and clarify deployment structure
  ([`ee34899`](https://github.com/mzworthington/gpio-build-monitor/commit/ee34899851f6724f6afbc77aa239993b9c06d511))


## v0.4.0 (2026-08-08)

### Features

- Deplopy ws web app
  ([`16522fc`](https://github.com/mzworthington/gpio-build-monitor/commit/16522fcc9bcde250db976e5a1eeb162e5593783a))

- Deplopy ws web app
  ([`cc196fc`](https://github.com/mzworthington/gpio-build-monitor/commit/cc196fcf80ae13b5f84f48a98e276b0292e6f02e))


## v0.3.0 (2026-08-08)

### Features

- Wake CI refresh from provider webhooks
  ([#11](https://github.com/mzworthington/gpio-build-monitor/pull/11),
  [`cf3057b`](https://github.com/mzworthington/gpio-build-monitor/commit/cf3057b30268bf5744c42f393058a901a4a2441f))

### Refactoring

- Split webhook providers behind an interface
  ([#11](https://github.com/mzworthington/gpio-build-monitor/pull/11),
  [`cf3057b`](https://github.com/mzworthington/gpio-build-monitor/commit/cf3057b30268bf5744c42f393058a901a4a2441f))


## v0.2.2 (2026-07-23)

### Chores

- Update changelog format and enhance semantic release configuration
  ([`b3495c4`](https://github.com/mzworthington/gpio-build-monitor/commit/b3495c4170b23de630201a09a90f0ff4de758e37))


## v0.2.0 (2026-07-23)

Baseline release before changelog automation. Features that already shipped:

### Features

- Poll GitHub Actions and CircleCI and aggregate status across configured repos
- Drive desk LEDs from aggregated CI status (blue / green / red / yellow / purple)
- Mock GPIO on non-Pi hosts so the same loop runs in local development
- Typer CLI (`monitor run`, `monitor check-config`) with integrations config and pin map
- Headless Pi deploy: systemd units, auto-update timer, and bootstrap/serve tooling
