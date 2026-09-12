from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_repo_root_conftest_is_present():
    assert (ROOT / "conftest.py").is_file()
