"""llvm-mingw toolchain."""
import os
from pathlib import Path
from types import SimpleNamespace, MethodType

from src.config import toolchain_base, gopts
from toolchains.expand import generic_toolchain_expand


def configure_llvm_mingw(self: SimpleNamespace, config: SimpleNamespace) -> bool:
    """Point CMake at the llvm-mingw toolchain file and processor."""
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = gopts.path / 'toolchains' / 'toolchain-llvm-mingw.cmake'
            cmake.config_vars.append(f'-DLLVM_MINGW_PROCESSOR={config.arch}')

    return True


def llvm_mingw_toolchain() -> SimpleNamespace:
    """mstorsjo llvm-mingw. i686, x86_64, armv7, and aarch64."""
    sysroot = Path('C:/opt/llvm-mingw-20250305-ucrt-x86_64')
    toolchain_env = {k: v for k, v in os.environ.items()}
    toolchain_env['PATH'] = f'{sysroot / 'bin'};{os.environ['PATH']}'

    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': "llvm-mingw",
        'desc': '[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
        'sysroot': Path(sysroot),
        'shell': ["pwsh", "-Command"],
        "arch_list": ['i686', 'x86_64', 'armv7', 'aarch64'],
        'platform_list': ['win32'],
        'env': toolchain_env,
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    setattr(toolchain, 'configure', MethodType(configure_llvm_mingw, toolchain))
    return toolchain
