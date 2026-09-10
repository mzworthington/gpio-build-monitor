# Restore patched CrossPoint sources after firmware is linked so the submodule
# stays clean. Must not run at extra_script import: PlatformIO `post:` scripts
# execute after env setup, before compile. Checking out then links stock
# HomeActivity and drops the home-menu row.
import subprocess
import sys
from pathlib import Path

OVERLAY_FILES = [
    "lib/I18n/translations/english.yaml",
    "src/activities/ActivityManager.cpp",
    "src/activities/ActivityManager.h",
    "src/activities/home/HomeActivity.cpp",
    "src/activities/home/HomeActivity.h",
]


def restore_overlay(root: Path) -> None:
    result = subprocess.run(
        ["git", "checkout", "--", *OVERLAY_FILES],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout or "git checkout of overlay files failed")
        return
    print("Restored CrossPoint overlay files; next pio run reapplies patches")


def _after_firmware(source, target, env) -> None:
    restore_overlay(Path(env["PROJECT_DIR"]))


try:
    Import("env")
except NameError:
    restore_overlay(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
else:
    env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", _after_firmware)
