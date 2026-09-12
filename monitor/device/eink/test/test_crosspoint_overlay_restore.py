from pathlib import Path

MONITOR = Path(__file__).resolve().parents[1] / "apps" / "monitor"


def test_overlay_restore_runs_after_firmware_bin_not_at_import():
    src = (MONITOR / "restore_crosspoint_overlay.py").read_text(encoding="utf-8")
    fn_at = src.index("def restore_overlay")
    checkout_at = src.index('["git", "checkout"')
    post_at = src.index("AddPostAction")
    assert fn_at < checkout_at
    assert "BUILD_DIR" in src and "PROGNAME" in src
    assert post_at > checkout_at
    assert src.index("try:") < src.index('Import("env")')
