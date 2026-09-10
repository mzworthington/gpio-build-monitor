# Apply Settings / i18n and home-menu overlays before CrossPoint's gen_i18n.py.
# SCons extra_scripts do not define __file__; locate patches from PROJECT_DIR.
import subprocess
import sys
from pathlib import Path

Import("env")

root = Path(env["PROJECT_DIR"])
monitor = root.parent / "apps" / "monitor" / "patches"


def apply_patch(marker: Path, needle: str, patch: Path) -> None:
    if needle in marker.read_text(encoding="utf-8"):
        print(f"CrossPoint overlay already applied ({patch.name})")
        return
    result = subprocess.run(["git", "apply", str(patch)], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "git apply failed\n")
        raise RuntimeError(f"Failed to apply {patch}")
    print(f"Applied CrossPoint overlay {patch.name}")


apply_patch(
    root / "src" / "activities" / "settings" / "SettingsActivity.h",
    "BuildMonitor",
    monitor / "settings-build-monitor.patch",
)
apply_patch(
    root / "src" / "activities" / "home" / "HomeActivity.h",
    "BUILD_MONITOR",
    monitor / "home-build-monitor.patch",
)
