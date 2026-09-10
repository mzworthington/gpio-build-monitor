# Restore patched CrossPoint sources after compile so the submodule stays clean.
# Patches live in gpio-build-monitor (`patches/`). The next `pio run` reapplies them.
import subprocess
from pathlib import Path

Import("env")

root = Path(env["PROJECT_DIR"])
files = [
    "lib/I18n/translations/english.yaml",
    "src/activities/ActivityManager.cpp",
    "src/activities/ActivityManager.h",
    "src/activities/home/HomeActivity.cpp",
    "src/activities/home/HomeActivity.h",
    "src/activities/settings/SettingsActivity.cpp",
    "src/activities/settings/SettingsActivity.h",
]
result = subprocess.run(["git", "checkout", "--", *files], cwd=root, capture_output=True, text=True)
if result.returncode != 0:
    print(result.stderr or result.stdout or "git checkout of overlay files failed")
else:
    print("Restored CrossPoint overlay files; next pio run reapplies patches")
