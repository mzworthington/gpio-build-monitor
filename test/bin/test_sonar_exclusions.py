from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = "monitor/device/eink/crosspoint"


def _prop(text: str, key: str) -> str:
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _covers(source: str, path: str) -> bool:
    source = source.rstrip("/")
    if source in {".", ""}:
        return True
    return path == source or path.startswith(f"{source}/")


def test_sonar_crosspoint_exclusion_avoids_globs():
    text = (ROOT / ".sonarcloud.properties").read_text(encoding="utf-8")
    assert "**" not in text


def test_sonar_sources_do_not_include_crosspoint_submodule_tree():
    text = (ROOT / ".sonarcloud.properties").read_text(encoding="utf-8")
    sources = [part.strip() for part in _prop(text, "sonar.sources").split(",") if part.strip()]
    assert sources, "Automatic Analysis cannot glob exclusions; set sonar.sources instead"
    assert not any(_covers(source, VENDOR) for source in sources)
    assert any(_covers(source, "monitor/device/eink/src") for source in sources)
    assert any(_covers(source, "monitor/api") for source in sources)
