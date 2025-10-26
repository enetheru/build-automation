# MARK: Emscripten
# ╭────────────────────────────────────────────╮
# │  ___                  _      _             │
# │ | __|_ __  ___ __ _ _(_)_ __| |_ ___ _ _   │
# │ | _|| '  \(_-</ _| '_| | '_ \  _/ -_) ' \  │
# │ |___|_|_|_/__/\__|_| |_| .__/\__\___|_||_| │
# │                        |_|                 │
# ╰────────────────────────────────────────────╯
import os
from pathlib import Path
from types import SimpleNamespace, MethodType

import rich

from share import format as fmt
from share.config import toolchain_base
from share.run import stream_command


def emscripten_update( toolchain:SimpleNamespace, config:SimpleNamespace, console:rich.Console ):
    import os
    from pathlib import Path

    console.set_window_title('Updating Emscripten SDK')
    print(fmt.t2("Emscripten Update"))

    emscripten_path = Path( toolchain.path )
    os.chdir(emscripten_path)
    stream_command( 'git pull', dry=config.dry )

def win32_emscripten_script():
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
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command( f'{cmd_prefix} "{emscripten_tool} list"',
                    stdout_handler=emscripten_check,
                    quiet=True,
                    dry=opts['dry']
                    )

    if not ('EMSDK' in os.environ):
        print(fmt.t2(f'Emscripten {emscripten_check.task.capitalize()}'))
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}; python {build['script_path']}"',
                        dry=opts['dry'] )
        quit()

def win32_emscripten_cmake( build:SimpleNamespace ):
    toolchain = build.toolchain
    cmake = build.buildtool
    cmake.toolchain = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake',
    cmake.generators = ['Ninja','Ninja Multi-Config']

def win32_emscripten_toolchain() -> SimpleNamespace:
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