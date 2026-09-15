from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def test_dockerfile_runs_as_non_root_user():
    lines = [
        line.strip()
        for line in DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    users = [line.split(None, 1)[1] for line in lines if line.startswith("USER ")]
    assert users
    assert users[-1] not in {"0", "root"}


def test_dockerfile_pip_installs_wheels_only():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "--only-binary" in text and ":all:" in text


def test_dockerfile_pip_installs_hash_locked_requirements():
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "--require-hashes" in text
    assert "requirements.lock" in text


def test_dockerfile_declares_one_runtime_cmd():
    lines = [
        line.strip()
        for line in DOCKERFILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    cmds = [line for line in lines if line.startswith("CMD ")]
    assert len(cmds) == 1
