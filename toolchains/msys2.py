"""MSYS2 environments. Each one is a shell around its own compiler.

godot-cpp looks for prefixed binutils. clang64 needs a symlink so it can find ar:
ln -s ar.exe x86_64-w64-mingw32-llvm-ar.exe
in C:/msys64/clang64/bin
"""
from types import SimpleNamespace, MethodType

from src.config import toolchain_base
from toolchains.expand import generic_toolchain_expand


def _msys2(name: str, desc: str, environ: str, arch: str) -> SimpleNamespace:
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': name,
        'desc': desc,
        'shell': ["C:/msys64/msys2_shell.cmd", f"-{environ}", "-defterm", "-no-start", "-c"],
        "arch_list": [arch],
        'platform_list': ['win32'],
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
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
