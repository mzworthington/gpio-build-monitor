# Development

## Commands

```shell
make lint           # ruff
make test           # ruff + pytest
```

Python dependencies are in `pyproject.toml`. Git hooks use [pre-commit](https://pre-commit.com/):

| Hook | Runs |
|------|------|
| `pre-commit` | `ruff check --fix` |
| `pre-push` | `pytest` |

`bin/bootstrap` installs hooks automatically. To reinstall manually:

```shell
pre-commit install
pre-commit install --hook-type pre-push
```

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on pushes and pull requests to `main`:

- Bootstrap, lint, and pytest
- JUnit report upload

### Releases

Merging to `main` triggers an automatic release when `monitor/` or `pyproject.toml` changed since the last tag. No manual tagging or version bumps are required.

The release job:

1. Detects application changes since the latest `v*` tag
2. Bumps the version in `pyproject.toml` from commit messages
3. Updates `CHANGELOG.md` from conventional commits
4. Builds wheel and sdist artifacts
5. Creates a GitHub Release and pushes the `vX.Y.Z` tag

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
