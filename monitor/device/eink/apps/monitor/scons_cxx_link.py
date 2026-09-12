# CrossPoint never links Fortran. SCons 4.11 SMARTLINK still does
# `import SCons.Tool.FortranCommon` at link time. Homebrew PlatformIO 6.2 on
# Python 3.14 raises ModuleNotFoundError there even when the file is on disk.
import sys
import types

Import("env")

if "SCons.Tool.FortranCommon" not in sys.modules:
    try:
        import SCons.Tool.FortranCommon  # noqa: F401
    except ModuleNotFoundError:
        shim = types.ModuleType("SCons.Tool.FortranCommon")
        shim.isfortran = lambda *_args, **_kwargs: False
        sys.modules["SCons.Tool.FortranCommon"] = shim

env.Replace(SMARTLINK="$CXX", LINK="$CXX")
