"""Standalone MinGW-w64 toolchain."""
import os
from pathlib import Path
from types import SimpleNamespace, MethodType

from src.config import toolchain_base, gopts
from toolchains.expand import generic_toolchain_expand


def configure_mingw(self: SimpleNamespace, config: SimpleNamespace) -> bool:
    """Point CMake at the MinGW toolchain file."""
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = gopts.path / 'toolchains' / 'toolchain-mingw64.cmake'
    return True


def mingw64_toolchain() -> SimpleNamespace:
    """niXman mingw-builds at C:/mingw64."""
    toolchain_env = {k: v for k, v in os.environ.items()}
    toolchain_env['PATH'] = f'C:/mingw64/bin;{os.environ['PATH']}'

    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': "mingw64",
        'desc': '[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
        'sysroot': Path('C:/mingw64'),
        "arch_list": ['x86_64'],
        'platform_list': ['win32'],
        'env': toolchain_env,
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    setattr(toolchain, 'configure', MethodType(configure_mingw, toolchain))
    return toolchain
