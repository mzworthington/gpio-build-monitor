from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cloudflare_hosting_uses_the_edge_dns_command():
    assert not (ROOT / "bin" / "setup-cloudflare-hosting.sh").exists()
    docs = (ROOT / "docs" / "development.md").read_text(encoding="utf-8")
    assert "setup-cloudflare-hosting" in docs
    assert "bin/setup-cloudflare-hosting.sh" not in docs
