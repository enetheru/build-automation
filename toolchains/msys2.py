"""MSYS2 environments. Each one is a shell around its own compiler.

godot-cpp looks for prefixed binutils. clang64 needs a symlink so it can find ar:
ln -s ar.exe x86_64-w64-mingw32-llvm-ar.exe
in C:/msys64/clang64/bin
"""
import platform
from types import SimpleNamespace, MethodType

from src.config import toolchain_base, gopts
from toolchains.expand import generic_toolchain_expand

# dumpmachine names. x86_32 is this tree's name for the mingw32 gcc, which
# reports i686-w64-mingw32.
_PROCESSOR = {
    'x86_64': 'x86_64',
    'x86_32': 'i686',
    'arm64': 'aarch64',
}

_FAMILY = {
    'amd64': 'x64',
    'x86_64': 'x64',
    'x64': 'x64',
    'i686': 'x86',
    'i386': 'x86',
    'x86': 'x86',
    'x86_32': 'x86',
    'aarch64': 'arm64',
    'arm64': 'arm64',
    'armv7': 'arm32',
    'arm': 'arm32',
}


def _family(name: str) -> str:
    return _FAMILY.get(name.lower(), name.lower())


def configure_msys2(self: SimpleNamespace, config: SimpleNamespace) -> bool:
    """Mark mingw32 as a cross compile.

    The x64 environments target this Windows host, so they keep CMake's
    normal host detection. mingw32's gcc is i686. Without CMAKE_SYSTEM_NAME,
    CMake forces CMAKE_CROSSCOMPILING false and native CPU flags follow the
    host chip.
    """
    if getattr(config.buildtool, 'name', None) != 'cmake':
        return True
    recorded = getattr(config, 'toolchain', None)
    arch = getattr(recorded, 'target_arch', None) or getattr(config, 'arch', None)
    if not arch:
        return True
    target = _PROCESSOR.get(arch, arch)
    if platform.system() == 'Windows' and _family(platform.machine()) == _family(target):
        return True
    cmake = config.buildtool
    cmake.toolchain = gopts.path / 'toolchains' / 'toolchain-msys2.cmake'
    cmake.config_vars.append(f'-DMSYS2_PROCESSOR={target}')
    return True


def _msys2(name: str, desc: str, environ: str, arch: str) -> SimpleNamespace:
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': name,
        'desc': desc,
        'shell': ["C:/msys64/msys2_shell.cmd", f"-{environ}", "-defterm", "-no-start", "-c"],
        "arch_list": [arch],
        'platform_list': ['win32'],
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    setattr(toolchain, 'configure', MethodType(configure_msys2, toolchain))
    return toolchain


def msys2_mingw32_toolchain() -> SimpleNamespace:
    """i686 gcc linking against msvcrt."""
    return _msys2("msys2-mingw32", 'i686      gcc linking against msvcrt', 'mingw32', 'x86_32')


def msys2_mingw64_toolchain() -> SimpleNamespace:
    """x86_64 gcc linking against msvcrt."""
    return _msys2("msys2-mingw64", 'x86_64    gcc linking against msvcrt', 'mingw64', 'x86_64')


def msys2_ucrt64_toolchain() -> SimpleNamespace:
    """x86_64 gcc linking against ucrt."""
    return _msys2("msys2-ucrt64", 'x86_64    gcc linking against ucrt', 'ucrt64', 'x86_64')


def msys2_clang64_toolchain() -> SimpleNamespace:
    """x86_64 clang linking against ucrt."""
    return _msys2("msys2-clang64", 'x86_64    clang linking against ucrt', 'clang64', 'x86_64')
