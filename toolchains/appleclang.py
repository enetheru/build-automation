"""Apple Clang toolchain for macOS hosts."""
from types import SimpleNamespace, MethodType

from src.config import toolchain_base
from toolchains.expand import generic_toolchain_expand


def appleclang_toolchain() -> SimpleNamespace:
    """Host Clang when AutoBuild is running on macOS.

    toolchains.py adds this only for sys.platform darwin, alongside
    Emscripten. It is the macOS peer of msvc and gcc, not a cross compiler
    used from Windows or Linux. A darwin build for the Mac's own processor
    is a normal host configure, so CMAKE_SYSTEM_NAME stays unset. ios, and
    the other CPU architecture, are cross compiles from that Mac and have
    no toolchain file of their own.
    """
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': "appleclang",
        'desc': "Default toolchain on MacOS",
        'arch_list': ['x86_64', 'arm64'],
        'platform_list': ['darwin', 'ios'],
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    return toolchain
