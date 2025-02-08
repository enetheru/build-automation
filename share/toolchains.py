from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

from share.format import *
from share.run import stream_command

# MARK: Toolchains
# ╭─────────────────────────────────────────────────────────────────────────────────╮
# │ ████████  ██████   ██████  ██       ██████ ██   ██  █████  ██ ███    ██ ███████ │
# │    ██    ██    ██ ██    ██ ██      ██      ██   ██ ██   ██ ██ ████   ██ ██      │
# │    ██    ██    ██ ██    ██ ██      ██      ███████ ███████ ██ ██ ██  ██ ███████ │
# │    ██    ██    ██ ██    ██ ██      ██      ██   ██ ██   ██ ██ ██  ██ ██      ██ │
# │    ██     ██████   ██████  ███████  ██████ ██   ██ ██   ██ ██ ██   ████ ███████ │
# ╰─────────────────────────────────────────────────────────────────────────────────╯
# List of CPU architectures from the arch setting in godot
# (auto|x86_32|x86_64|arm32|arm64|rv64|ppc32|ppc64|wasm32|loongarch64)
toolchains:dict = {}

""" TODO
Linux Host
    - Compiler Environment / Toolchain
MacOS Host
    - Compiler Environment / Toolchain
"""

# MARK: MSVC
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __ _____   _____                                                      │
# │ |  \/  / __\ \ / / __|                                                     │
# │ | |\/| \__ \\ V / (__                                                      │
# │ |_|  |_|___/ \_/ \___|                                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯
toolchains["msvc"] = SimpleNamespace(**{
    'desc':'# Microsoft Visual Studio',
    'shell':[ "pwsh", "-Command",
        """ "&{Import-Module 'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; Enter-VsDevShell 5ff44efb -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'};" """ ],
    "arch":['x86_64','x86_32']
}),

# MARK: LLVM
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _    _ __   ____  __                                                      │
# │ | |  | |\ \ / /  \/  |                                                     │
# │ | |__| |_\ V /| |\/| |                                                     │
# │ |____|____\_/ |_|  |_|                                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯
# Currently only clang-cl is supported.
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/Program Files/LLVM/bin;{os.environ['PATH']}'
toolchains["llvm"] = SimpleNamespace(**{
    'desc':'# Use Clang-Cl from llvm.org',
    "arch":['x86_64', 'x86_32', 'arm64'],
    'env': env
})

# MARK: LLVM-MinGW
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _    _ __   ____  __     __  __ _      _____      __                      │
# │ | |  | |\ \ / /  \/  |___|  \/  (_)_ _ / __\ \    / /                      │
# │ | |__| |_\ V /| |\/| |___| |\/| | | ' \ (_ |\ \/\/ /                       │
# │ |____|____\_/ |_|  |_|   |_|  |_|_|_||_\___| \_/\_/                        │
# ╰────────────────────────────────────────────────────────────────────────────╯
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/llvm-mingw/bin;{os.environ['PATH']}'
toolchains["llvm-mingw"] = SimpleNamespace(**{
    'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
    "arch":['x86_64', 'x86_32', 'arm32', 'arm64'],
    'env': env
})

# MARK: MinGW64
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __ _      _____      ____ _ _                                         │
# │ |  \/  (_)_ _ / __\ \    / / /| | |                                        │
# │ | |\/| | | ' \ (_ |\ \/\/ / _ \_  _|                                       │
# │ |_|  |_|_|_||_\___| \_/\_/\___/ |_|                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/mingw64/bin;{os.environ['PATH']}'
toolchains["mingw64"] = SimpleNamespace(**{
    'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
    "arch":['x86_64'],
    'env': env
})

# MARK: MSYS2
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __ _____   _____ ___                                                  │
# │ |  \/  / __\ \ / / __|_  )                                                 │
# │ | |\/| \__ \\ V /\__ \/ /                                                  │
# │ |_|  |_|___/ |_| |___/___|                                                 │
# ╰────────────────────────────────────────────────────────────────────────────╯
toolchains["msys2-mingw32"] = SimpleNamespace(**{
    'desc':'i686      gcc linking against msvcrt',
    'shell': [ "C:/msys64/msys2_shell.cmd", "-mingw32", "-defterm", "-no-start", "-c"],
    "arch":['x86_32']
})

toolchains["msys2-mingw64"] = SimpleNamespace(**{
    'desc':'x86_64    gcc linking against msvcrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-mingw64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64']
}),

toolchains["msys2-ucrt64"] = SimpleNamespace(**{
    'desc':'x86_64    gcc linking against ucrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-ucrt64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64']
}),

toolchains["msys2-clang64"] = SimpleNamespace(**{
    'desc':'x86_64    clang linking against ucrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-clang64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64']
}),

# MARK: Android
# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯
# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
def android_update( toolchain:SimpleNamespace, config:SimpleNamespace, console:Console ):
    import os
    from pathlib import Path

    console.set_window_title('Updating Android SDK')
    print(figlet("Android Update", {"font": "small"}))

    sdk_path = Path( toolchain.path )
    os.chdir(sdk_path / 'cmdline-tools/latest/bin')

    cmd_chunks = [
        'sdkmanager.bat',
        '--update',
        '--verbose' if config['quiet'] is False else None,
    ]
    stream_command( ' '.join(filter(None, cmd_chunks)), dry=config['dry'] )


toolchains["android"] = SimpleNamespace(**{
    'desc':'[Android](https://developer.android.com/tools/sdkmanager)',
    'path':Path('C:/androidsdk'),
    'verbs':['update'],
    'update':android_update,
    'arch':['x86_64', 'x86_32', 'arm64'],
    'cmake':{
        'toolchain':'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake',
        'config_vars':[
            "-DANDROID_PLATFORM=latest",
            "-DANDROID_ABI=x86_64"]
    }
}),

# MARK: Emscripten
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                  _      _                                             │
# │ | __|_ __  ___ __ _ _(_)_ __| |_ ___ _ _                                   │
# │ | _|| '  \(_-</ _| '_| | '_ \  _/ -_) ' \                                  │
# │ |___|_|_|_/__/\__|_| |_| .__/\__\___|_||_|                                 │
# │                        |_|                                                 │
# ╰────────────────────────────────────────────────────────────────────────────╯

# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
def emsdk_update( toolchain:SimpleNamespace, config:SimpleNamespace, console:Console ):
    import os
    from pathlib import Path

    console.set_window_title('Updating Emscripten SDK')
    print(figlet("EMSDK Update", {"font": "small"}))

    emsdk_path = Path( toolchain.path )
    os.chdir(emsdk_path)
    stream_command( 'git pull', dry=config.dry )

def emsdk_script( config:dict, toolchain:dict ):
    from pathlib import Path
    from io import StringIO

    emsdk_path = Path(toolchain['path'])
    emsdk_version = toolchain['version']
    emsdk_tool = f'pwsh -Command {str(emsdk_path / 'emsdk.ps1')} '

    def emsdk_is_active() -> bool:
        return True if 'EMSDK' in os.environ else False

    def emsdk_check( sdk_version ) -> bool:
        output = StringIO()
        stream_command( emsdk_tool + 'list', quiet=True, dry=config['dry'],
            stdout_handler=lambda text : output.write(text + '\n') )
        output.seek(0)
        for line in output:
            if sdk_version not in line: continue
            if 'INSTALLED' in line: return True
        return False

    def emsdk_activate( sdk_version ):
        print(figlet("EMSDK Activate", {"font": "small"}))
        stream_command( emsdk_tool + f'activate {sdk_version}', dry=config['dry'] )

    def emsdk_install( sdk_version ):
        print(figlet("EMSDK Install", {"font": "small"}))
        stream_command( emsdk_tool + f'install {sdk_version}', dry=config['dry'] )

    # Because the emsdk has no means to change the current environnment from within
    # python, I am just going to run the script again, but after activating it.
    if not emsdk_is_active():
        if emsdk_check( emsdk_version ):
            print(figlet("EMSDK Activate", {"font": "small"}))
            stream_command( emsdk_tool + f'activate {emsdk_version}; python {config['script_path']}', dry=config['dry'] )
        else:
            print(figlet("EMSDK Install", {"font": "small"}))
            stream_command( emsdk_tool + f'install {emsdk_version}; python {config['script_path']}', dry=config['dry'] )
            emsdk_install( emsdk_version )
        quit()

toolchains["emsdk"] = SimpleNamespace(**{
    'desc':'[Emscripten](https://emscripten.org/)',
    'path':Path('C:/emsdk'),
    'version':'3.1.64',
    'verbs':['update', 'script'],
    'update':emsdk_update,
    'script':emsdk_script,
    "arch":['wasm32'], #wasm64
    'cmake':{
        'toolchain':'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
    }
})

# MARK: Finalise
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _           _ _                                                       │
# │ | __(_)_ _  __ _| (_)___ ___                                               │
# │ | _|| | ' \/ _` | | (_-</ -_)                                              │
# │ |_| |_|_||_\__,_|_|_/__/\___|                                              │
# ╰────────────────────────────────────────────────────────────────────────────╯
# Copy the dictionary key into the toolchain as the name
def finalise_toolchains():
    for name, toolchain in toolchains.items():

        # set the names
        setattr(toolchain, 'name', name )

finalise_toolchains()
