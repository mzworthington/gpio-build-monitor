from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "setup-cloudflare-hosting.sh"


def test_cloudflare_hosting_shim_fetches_over_https_only():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--proto" in text
    assert "=https" in text
