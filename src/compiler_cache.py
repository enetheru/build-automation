"""Choose ccache or sccache for a CMake build.

ccache is the better C and C++ cache for a gcc or clang driver: direct mode
and depend mode. sccache is the better cache for cl.exe and clang-cl.
A launcher has to be on the CMake command line, before FetchContent, so the
dependencies pick it up too. The Visual Studio generator never runs one.
Android and Emscripten already wrap the compiler.
"""
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

# clang-cl lives in the llvm toolchain. llvm-mingw is a gcc-style clang driver.
_MSVC_LIKE = {'msvc', 'llvm'}
_SKIP = {'android', 'emscripten'}
_MSYS_SHELL_FLAGS = {'-defterm', '-no-start', '-here', '-full-path'}

_found: dict[tuple[str, str | None], str | None] = {}


def apply_cmake_compiler_cache(build: SimpleNamespace) -> None:
    """Append CMAKE_C/CXX_COMPILER_LAUNCHER when a cache tool is visible."""
    cmake = getattr(build, 'buildtool', None)
    if cmake is None or getattr(cmake, 'name', None) != 'cmake':
        return
    toolchain = getattr(build, 'toolchain', None)
    if toolchain is None:
        return
    generator = getattr(cmake, 'short_gen', None)
    launcher = find_compiler_cache(toolchain, generator)
    if not launcher:
        return
    path = Path(launcher).as_posix()
    if ' ' in path:
        path = f'"{path}"'
    config_vars = cmake.config_vars
    for lang in ('C', 'CXX'):
        flag = f'-DCMAKE_{lang}_COMPILER_LAUNCHER={path}'
        if flag not in config_vars:
            config_vars.append(flag)


def find_compiler_cache(toolchain: SimpleNamespace, generator: str | None = None) -> str | None:
    """Return the launcher executable for this toolchain and generator.

    The Visual Studio generator key is `msvc`. Ninja Multi-Config keeps that
    toolchain and still honors a launcher. Search the toolchain's own bin,
    then PATH, then a copy that belongs to another toolchain on this machine.
    """
    if generator == 'msvc':
        return None
    name = getattr(toolchain, 'name', '')
    if name in _SKIP:
        return None
    key = (name, generator)
    if key in _found:
        return _found[key]
    order = ('sccache', 'ccache') if name in _MSVC_LIKE else ('ccache', 'sccache')
    own = _prefix_bins(toolchain)
    found = None
    for tool in order:
        found = _which_in(tool, own) or shutil.which(tool) or _other_toolchain(tool, toolchain)
        if found:
            break
    _found[key] = found
    return found


def _prefix_bins(toolchain: SimpleNamespace) -> list[Path]:
    """Bin directory this toolchain puts in front of PATH, plus an MSYS2 env bin."""
    bins: list[Path] = []
    env = getattr(toolchain, 'env', None) or {}
    raw = env.get('PATH') if isinstance(env, dict) else None
    if raw:
        first = raw.split(os.pathsep)[0]
        if first:
            bins.append(Path(first))
    shell = list(getattr(toolchain, 'shell', None) or [])
    if shell and Path(str(shell[0])).name.lower() == 'msys2_shell.cmd':
        root = Path(shell[0]).parent
        for arg in shell[1:]:
            if not isinstance(arg, str) or not arg.startswith('-') or arg.startswith('--'):
                continue
            if arg in _MSYS_SHELL_FLAGS:
                continue
            if arg == '-c':
                break
            bins.append(root / arg[1:] / 'bin')
    return bins


def _other_toolchain(tool: str, toolchain: SimpleNamespace) -> str | None:
    """A copy that ships with another toolchain.

    Prefer a donor that targets one of the same architectures, so a 64-bit
    build does not pick up the i686 ccache when a 64-bit one is installed.
    """
    from src.config import gopts
    name = getattr(toolchain, 'name', None)
    wanted = set(getattr(toolchain, 'arch_list', None) or [])
    same_arch: list[str] = []
    rest: list[str] = []
    for other in gopts.toolchains.values():
        other_name = getattr(other, 'name', None)
        if other_name == name or other_name in _SKIP:
            continue
        hit = _which_in(tool, _prefix_bins(other))
        if not hit:
            continue
        other_arch = set(getattr(other, 'arch_list', None) or [])
        if wanted and other_arch and wanted & other_arch:
            same_arch.append(hit)
        else:
            rest.append(hit)
    if same_arch:
        return same_arch[0]
    if rest:
        return rest[0]
    return None


def _which_in(tool: str, bins: list[Path]) -> str | None:
    if not bins:
        return None
    return shutil.which(tool, path=os.pathsep.join(os.fspath(path) for path in bins))
