from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sonar_analysis_excludes_crosspoint_vendor_tree():
    text = (ROOT / ".sonarcloud.properties").read_text(encoding="utf-8")
    assert "sonar.exclusions" in text
    assert "monitor/device/eink/crosspoint/" in text


def test_sonar_crosspoint_exclusion_avoids_globs():
    text = (ROOT / ".sonarcloud.properties").read_text(encoding="utf-8")
    assert "**" not in text
