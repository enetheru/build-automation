"""Apple Clang toolchain for macOS hosts."""
from types import SimpleNamespace, MethodType

from src.config import toolchain_base
from toolchains.expand import generic_toolchain_expand


def appleclang_toolchain() -> SimpleNamespace:
    """Default toolchain on macOS. Host triple comes from clang -print-target-triple."""
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': "appleclang",
        'desc': "Default toolchain on MacOS",
        'arch_list': ['x86_64', 'arm64'],
        'platform_list': ['darwin', 'ios'],
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    return toolchain
