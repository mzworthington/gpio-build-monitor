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

Pushing a tag `vX.Y.Z` that matches the version in `pyproject.toml` triggers a GitHub Release with built wheel and sdist artifacts.

```shell
# bump version in pyproject.toml, commit, then:
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

## Security

- **Dependabot** (`.github/dependabot.yml`) - weekly update PRs for Python and GitHub Actions dependencies
- **Dependency Review** - blocks PRs that introduce known-vulnerable dependencies
- **CodeQL** - static analysis on every push/PR and weekly on a schedule
