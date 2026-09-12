from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INFRA = ROOT / "infra" / "cloudflare" / "index.ts"


def test_public_monitor_hostname_attaches_as_worker_custom_domain():
    src = INFRA.read_text(encoding="utf-8")
    assert "WorkersCustomDomain" in src
    assert "new cloudflare.PagesDomain" not in src
