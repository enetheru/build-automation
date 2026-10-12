"""Emscripten SDK for Windows and macOS hosts.

The SDK directory is toolchain['sdk_path']. On Windows that is C:/emsdk.
"""
import os
from pathlib import Path
from types import SimpleNamespace, MethodType

from src import format as fmt
from src.config import toolchain_base
from src.run import stream_command
from toolchains.expand import generic_toolchain_expand


def emscripten_update(toolchain: SimpleNamespace, config: SimpleNamespace, console) -> None:
    """Pull the Emscripten SDK checkout."""
    console.set_window_title('Updating Emscripten SDK')
    fmt.t2("Emscripten Update")

    emscripten_path = Path(toolchain.sdk_path)
    os.chdir(emscripten_path)
    stream_command('git pull', dry=config.dry)


def win32_emscripten_script():
    """Activate or install the pinned Emscripten version, then re-run the build script."""
    build: dict = {}
    toolchain: dict = {}
    opts: dict = {}
    # start_script

    # MARK: Emscripten
    #[=============================[ Emscripten ]=============================]
    from pathlib import Path

    cmd_prefix = f'pwsh -Command'
    emscripten_tool = (Path(toolchain['sdk_path']) / 'emsdk.ps1').as_posix()

    def emscripten_check(line):
        """

        :param line:
        """
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command(f'{cmd_prefix} "{emscripten_tool} list"',
        stdout_handler=emscripten_check,
        quiet=True,
        dry=opts['dry']
    )

    if not ('EMSDK' in os.environ):
        fmt.t2(f'Emscripten {emscripten_check.task.capitalize()}')
        stream_command(f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}; python {build['script_path']}"',
            dry=opts['dry'])
        quit()


def win32_emscripten_cmake(build: SimpleNamespace):
    """Point CMake at the Emscripten platform file."""
    cmake = build.buildtool
    cmake.toolchain = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
    cmake.generators = ['Ninja', 'Ninja Multi-Config']


def win32_emscripten_toolchain() -> SimpleNamespace:
    """Windows Emscripten toolchain. wasm32, Ninja via emsdk.ps1."""
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': 'emscripten',
        'desc': '[Emscripten](https://emscripten.org/)',
        'sdk_path': Path('C:/emsdk'),
        'version': '3.1.64',
        'verbs': ['update'],
        'script_parts': [win32_emscripten_script],
        "arch_list": ['wasm32'],  # wasm64
        'platform_list': ['emscripten'],
        'cmake': win32_emscripten_cmake,
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    setattr(toolchain, 'update', MethodType(emscripten_update, toolchain))
    return toolchain


def darwin_emscripten_script():
    """Activate or install the pinned Emscripten version, then re-run the build script."""
    toolchain: dict = {}
    opts: dict = {}
    build: dict = {}
    # start_script

    # MARK: Emscripten
    #[=============================[ Emscripten ]=============================]
    import stat

    cmd_prefix = f'{os.environ['SHELL']} -c'
    emscripten_tool = (Path(toolchain['sdk_path']) / 'emsdk').as_posix()

    def emscripten_check(line):
        """

        :param line:
        """
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command(f'{cmd_prefix} "{emscripten_tool} list"',
        stdout_handler=emscripten_check,
        quiet=True,
        dry=opts['dry']
    )

    if not ('EMSDK' in os.environ):
        fmt.t2(f'Emscripten {emscripten_check.task.capitalize()}')
        stream_command(f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}"',
            dry=opts['dry'])

        env_script = (toolchain['sdk_path'] / 'emsdk_env.sh').as_posix()
        os.chmod(env_script, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        stream_command(f'{cmd_prefix} "source {env_script}; python {build['script_path']}"', dry=opts['dry'])
        quit()


def darwin_emscripten_cmake(build: SimpleNamespace):
    """Point CMake at the Emscripten platform file."""
    cmake = build.buildtool
    cmake.toolchain = '/Users/enetheru/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'


def darwin_emscripten_toolchain() -> SimpleNamespace:
    """macOS Emscripten toolchain."""
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': 'emscripten',
        'desc': '[Emscripten](https://emscripten.org/)',
        'sdk_path': Path('/Users/enetheru/emsdk'),
        'version': '3.1.64',
        'verbs': ['update', 'script'],
        'update': emscripten_update,
        'script_parts': [darwin_emscripten_script],
        'arch_list': ['wasm32'],  # wasm64
        'platform_list': ['emscripten'],
        'cmake': darwin_emscripten_cmake
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    return toolchain
