"""System GCC on a Linux host."""
import os
from types import SimpleNamespace, MethodType

from src.config import toolchain_base, gopts
from toolchains.expand import generic_toolchain_expand


def configure_gcc(self: SimpleNamespace, config: SimpleNamespace) -> bool:
    """Point CMake at the GCC toolchain file."""
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = gopts.path / 'toolchains' / 'toolchain-gcc.cmake'
    return True


def gcc_toolchain() -> SimpleNamespace:
    """gcc and g++ from PATH (Debian packages on the box)."""
    env = {k: v for k, v in os.environ.items()}
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': 'gcc',
        'desc': 'System GCC from PATH, native Linux builds',
        "arch_list": ['x86_64'],  # TODO support more architectures
        'platform_list': ['linux'],
        'env': env,
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    setattr(toolchain, 'configure', MethodType(configure_gcc, toolchain))
    return toolchain
