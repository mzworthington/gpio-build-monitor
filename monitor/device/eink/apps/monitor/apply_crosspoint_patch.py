# Apply home-menu + i18n overlay before CrossPoint's gen_i18n.py.
# SCons extra_scripts do not define __file__; locate patches from PROJECT_DIR.
import subprocess
import sys
from pathlib import Path

Import("env")

root = Path(env["PROJECT_DIR"])
patch = root.parent / "apps" / "monitor" / "patches" / "home-build-monitor.patch"
header = root / "src" / "activities" / "home" / "HomeActivity.h"

if "BUILD_MONITOR" in header.read_text(encoding="utf-8"):
    print(f"CrossPoint overlay already applied ({patch.name})")
else:
    result = subprocess.run(["git", "apply", str(patch)], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "git apply failed\n")
        raise RuntimeError(f"Failed to apply {patch}")
    print(f"Applied CrossPoint overlay {patch.name}")
