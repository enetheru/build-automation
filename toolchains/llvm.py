"""LLVM Clang-CL toolchain."""
import os
from types import SimpleNamespace, MethodType

from src.config import toolchain_base, gopts
from toolchains.expand import generic_toolchain_expand


def configure_llvm(self: SimpleNamespace, config: SimpleNamespace) -> bool:
    """Point CMake at the LLVM toolchain file."""
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = gopts.path / 'toolchains' / 'toolchain-llvm.cmake'

    return True


def llvm_toolchain() -> SimpleNamespace:
    """Clang-CL from llvm.org, with its bin directory on PATH."""
    env = {k: v for k, v in os.environ.items()}
    env['PATH'] = f'C:/Program Files/LLVM/bin;{os.environ['PATH']}'
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': 'llvm',
        'desc': '# Use Clang-Cl from llvm.org',
        "arch_list": ['x86_64'],  # TODO support more architectures
        'platform_list': ['win32'],
        'env': env,
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    setattr(toolchain, 'configure', MethodType(configure_llvm, toolchain))
    return toolchain
