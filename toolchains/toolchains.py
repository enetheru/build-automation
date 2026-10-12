"""Host toolchain list.

Each toolchain lives in its own module. This file only picks the ones for
the machine that is running the build.
"""
import sys
from types import SimpleNamespace

import toolchains.android as android
import toolchains.appleclang as appleclang
import toolchains.emscripten as emscripten
import toolchains.llvm as llvm
import toolchains.llvm_mingw as llvm_mingw
import toolchains.mingw64 as mingw64
import toolchains.msvc as msvc
import toolchains.msys2 as msys2


def generate(opts: SimpleNamespace) -> dict:
    """Map toolchain name to its config for this host.

    Args:
        opts: Configuration options. Accepted so the loader can call this
            the same way it calls a project generate.

    Returns:
        Toolchain name to SimpleNamespace.
    """
    entries: list = []
    match sys.platform:
        case 'win32':
            entries = [
                msvc.msvc_toolchain(),
                llvm.llvm_toolchain(),
                llvm_mingw.llvm_mingw_toolchain(),
                mingw64.mingw64_toolchain(),
                msys2.msys2_mingw32_toolchain(),
                msys2.msys2_mingw64_toolchain(),
                msys2.msys2_ucrt64_toolchain(),
                msys2.msys2_clang64_toolchain(),
            ]
            android_toolchain = android.android_toolchain()
            if android_toolchain is not None:
                entries.append(android_toolchain)
            entries.append(emscripten.win32_emscripten_toolchain())
        case 'darwin':
            entries = [
                appleclang.appleclang_toolchain(),
                emscripten.darwin_emscripten_toolchain(),
            ]

    return {tc.name: tc for tc in entries}
