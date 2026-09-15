from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKFILES = ("uv.lock", "poetry.lock", "pdm.lock", "pylock.toml")


def test_project_ships_a_python_lockfile():
    assert any((ROOT / name).is_file() for name in LOCKFILES)
