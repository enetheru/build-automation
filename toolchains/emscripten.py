
# ╭────────────────────────────────────────────╮
# │  ___                  _      _             │
# │ | __|_ __  ___ __ _ _(_)_ __| |_ ___ _ _   │
# │ | _|| '  \(_-</ _| '_| | '_ \  _/ -_) ' \  │
# │ |___|_|_|_/__/\__|_| |_| .__/\__\___|_||_| │
# │                        |_|                 │
# ╰────────────────────────────────────────────╯
"""
Emscripten toolchain management utilities.

This module provides a set of functions and utilities for managing and
configuring the Emscripten toolchain, including updating the SDK, configuring
CMake, and managing related toolchain scripts.

Functions:
- emscripten_update: Updates the Emscripten SDK by pulling changes from the
  repository.
- win32_emscripten_script: Configures and initializes the Emscripten toolchain
  script on Windows.
- win32_emscripten_cmake: Configures the CMake tools for building with the
  Emscripten toolchain.
- win32_emscripten_toolchain: Factory function for creating the Emscripten
  toolchain configuration.

Dependencies:
- The module relies on several external imports, including 'os', 'pathlib.Path',
  'rich', and utilities defined in other local modules like 'format', 'config',
  and 'run'.
"""
import os
from pathlib import Path
from types import SimpleNamespace, MethodType

import rich

from src import format as fmt
from src.config import toolchain_base
from src.run import stream_command


def emscripten_update( toolchain:SimpleNamespace, config:SimpleNamespace, console:rich.Console ):
    """
    Updates the Emscripten SDK by pulling the latest changes from the remote repository.
    This function changes the current working directory to the Emscripten SDK path and
    executes a `git pull` command to update the SDK.

    :param toolchain: Contains tools and paths required for Emscripten operations.
    :type toolchain: SimpleNamespace
    :param config: Configuration options, including flags such as dry-run.
    :type config: SimpleNamespace
    :param console: Rich Console instance used for user interface interactions and logging.
    :type console: rich.Console
    :return: None
    """
    import os
    from pathlib import Path

    console.set_window_title('Updating Emscripten SDK')
    fmt.t2("Emscripten Update")

    emscripten_path = Path( toolchain.path )
    os.chdir(emscripten_path)
    stream_command( 'git pull', dry=config.dry )

def win32_emscripten_script():
    """
    Manages the setup and activation of the Emscripten toolchain on a Windows environment
    via PowerShell commands.

    This script determines whether Emscripten needs to be installed or activated, based
    on the provided toolchain configuration, and executes the necessary commands using
    Emscripten's `emsdk.ps1` script. If the activation process completes successfully,
    it ensures the environment is configured correctly for Emscripten usage.

    :raises KeyError: Raised if required keys are missing in the `build`, `toolchain`,
        or `opts` dictionaries.
    :raises AttributeError: Raised if internal methods or attributes are misconfigured.
    """
    build:dict = {}
    toolchain:dict = {}
    opts:dict = {}
    # start_script

    # MARK: Emscripten
    #[=============================[ Emscripten ]=============================]
    from pathlib import Path

    cmd_prefix = f'pwsh -Command'
    emscripten_tool = (Path(toolchain['path']) / 'emsdk.ps1').as_posix()

    def emscripten_check( line ):
        """
        Checks if a specific version of the toolchain is installed and updates the task
        state accordingly.

        This function examines a given line to verify if it contains both the toolchain's
        version and the keyword 'INSTALLED'. If both conditions are satisfied, it sets
        the `task` attribute on the function to 'activate'.

        :param line: A string that is analyzed to determine if the toolchain version and
                     'INSTALLED' keyword are present.
        :type line: str
        """
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command( f'{cmd_prefix} "{emscripten_tool} list"',
                    stdout_handler=emscripten_check,
                    quiet=True,
                    dry=opts['dry']
                    )

    if not ('EMSDK' in os.environ):
        fmt.t2(f'Emscripten {emscripten_check.task.capitalize()}')
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}; python {build['script_path']}"',
                        dry=opts['dry'] )
        quit()

def win32_emscripten_cmake( build:SimpleNamespace ):
    """
    Configures the CMake build tool for Win32 with the Emscripten toolchain. This process
    sets up the appropriate toolchain file and generators required for Emscripten builds.

    :param build: A namespace containing the toolchain and build tool configuration. The
                  `toolchain` attribute specifies the current compilation toolchain, while
                  the `buildtool` attribute holds the CMake build configuration.
    :type build: SimpleNamespace

    :return: None
    """
    toolchain = build.toolchain
    cmake = build.buildtool
    cmake.toolchain = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake',
    cmake.generators = ['Ninja','Ninja Multi-Config']

def win32_emscripten_toolchain() -> SimpleNamespace:
    """
    Creates and returns a toolchain configuration object for the Emscripten platform based on
    Windows 32-bit architecture. The toolchain provides information and utility methods for
    building projects with the Emscripten SDK.

    :return: A configured `SimpleNamespace` object containing the toolchain details for Emscripten.
    :rtype: SimpleNamespace
    """
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':'emscripten',
        'desc':'[Emscripten](https://emscripten.org/)',
        'sdk_path':Path('C:/emsdk'),
        'version':'3.1.64',
        'verbs':['update'],
        'script_parts':[win32_emscripten_script],
        "arch":['wasm32'], #wasm64
        'platform':['emscripten'],
        'cmake':win32_emscripten_cmake
    }})
    setattr( toolchain, 'update', MethodType(emscripten_update, toolchain) )
    return toolchain

# windows_toolchains.append( win32_emscripten_toolchain() )