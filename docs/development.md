# Development

## Commands

```shell
make lint           # ruff
make test           # ruff + pytest
make test-eink      # native C++ tests for the e-ink snapshot parser (`monitor/device/eink`)
```

Python dependencies are in `pyproject.toml`. Git hooks use [pre-commit](https://pre-commit.com/):

| Hook | Runs |
|------|------|
| `pre-commit` | `ruff check --fix` |
| `commit-msg` | Conventional Commits subject |
| `pre-push` | `pytest` |

`bin/bootstrap` installs hooks automatically. To reinstall manually:

```shell
pre-commit install
pre-commit install --hook-type pre-push
pre-commit install --hook-type commit-msg
```

## Cloudflare

Public hostname: Cloudflare Worker from `monitor/device/web/` (`pnpm deploy:api`). Pages still deploys to `*.pages.dev`. Custom domain via `infra/cloudflare`. Python `monitor/api` is local (`bin/serve`).

```shell
bin/setup-cloudflare-hosting.sh
cd monitor/device/web && pnpm install && pnpm test && pnpm typecheck && pnpm deploy:api
cd ../../../infra/cloudflare && pnpm install && pulumi up
```

The status page is TypeScript Alpine (`monitor/device/web/src/web/`) bundled into `monitor/device/web/public/monitor.js`. CI `web` and `deploy-api` run that build. Leave `PYTHON_API_ORIGIN` empty so StatusHub is the hub.

[`.github/workflows/pulumi-cloudflare.yml`](../.github/workflows/pulumi-cloudflare.yml) previews/applies the Pulumi stack via the shared edge-dns reusable workflow.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pushes and pull requests to `main`:

- Bootstrap, lint, and pytest
- JUnit report upload
- On `main` only: `deploy-pages` (`wrangler pages deploy` for `*.pages.dev`) and `deploy-api` (`wrangler deploy` for `monitor.mzworthington.co.uk`)
- Privacy notice: `/privacy`
- On `main` only: `release` when application code changed since the last tag

### Releases

Merging to `main` triggers an automatic release when `monitor/api/` or `pyproject.toml` changed since the last tag. No manual tagging or version bumps are required.

The release job:

1. Detects application changes since the latest `v*` tag
2. Bumps the version in `pyproject.toml` from commit messages
3. Updates `CHANGELOG.md` from conventional commits
4. Builds wheel and sdist artifacts (`semantic-release version`)
5. Creates a GitHub Release and pushes the `vX.Y.Z` tag
6. Uploads the wheel/sdist to that release (`semantic-release publish`)

Pi auto-updates (`bin/update`) install the `monitor-*.whl` asset from the latest GitHub Release, so step 6 is required for new versions to land on devices.

Use [Conventional Commits](https://www.conventionalcommits.org/) so entries land in the changelog:

| Commit prefix | Version bump |
|---------------|--------------|
| `fix:` | patch |
| `feat:` | minor |
| `feat!:` or `BREAKING CHANGE` | major |

Example: `feat: add purple LED blink pattern` → minor release and a changelog entry on the next merge to `main`.

If this is the first automated release and no `v*` tags exist yet, CI seeds a baseline tag from the current `pyproject.toml` version before bumping.

## Security

- **Dependabot** (`.github/dependabot.yml`) - weekly update PRs for Python and GitHub Actions dependencies
- **Dependency Review** - blocks PRs that introduce known-vulnerable dependencies
- **CodeQL** - static analysis on every push/PR and weekly on a schedule
