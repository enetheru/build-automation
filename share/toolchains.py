import platform
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

from share.format import *
from share.run import stream_command

# Since these things are getting a little complicated lets try to make a little example for myself.
example = SimpleNamespace(**{
    'name'      :'name of the compiler, keep short',
    'desc'      :'description of the compiler, can be any length',
    'shell'     :[ "bash", "-c", """ "echo \"shell and script to pass to shell, can be a little awkward to write due to escaping\"" """ ],
    'arch'      :['list','of', 'target', 'architectures', 'like', 'x86_64', 'arm64', 'etc'],
    'platform'  :['list','of', 'target', 'platforms', 'matches', 'values', 'from', 'sys.platform']
})

# MARK: Windows
# ╭────────────────────────────────────────────────────────────────────────────╮
# │            ██     ██ ██ ███    ██ ██████   ██████  ██     ██ ███████       │
# │            ██     ██ ██ ████   ██ ██   ██ ██    ██ ██     ██ ██            │
# │            ██  █  ██ ██ ██ ██  ██ ██   ██ ██    ██ ██  █  ██ ███████       │
# │            ██ ███ ██ ██ ██  ██ ██ ██   ██ ██    ██ ██ ███ ██      ██       │
# │             ███ ███  ██ ██   ████ ██████   ██████   ███ ███  ███████       │
# ╰────────────────────────────────────────────────────────────────────────────╯
windows_toolchains:list = []
# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/

# MARK: MSVC
# ╭────────────────────────╮
# │  __  __ _____   _____  │
# │ |  \/  / __\ \ / / __| │
# │ | |\/| \__ \\ V / (__  │
# │ |_|  |_|___/ \_/ \___| │
# ╰────────────────────────╯
windows_toolchains.append( SimpleNamespace(**{
    'name':'msvc',
    'desc':'# Microsoft Visual Studio',
    'shell':[ "pwsh", "-Command",
        """ "&{Import-Module 'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; Enter-VsDevShell 5ff44efb -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'};" """ ],
    "arch":['x86_64'],
    'platform':['win32']
}))

# MARK: LLVM
# ╭────────────────────────╮
# │  _    _ __   ____  __  │
# │ | |  | |\ \ / /  \/  | │
# │ | |__| |_\ V /| |\/| | │
# │ |____|____\_/ |_|  |_| │
# ╰────────────────────────╯
# Currently only clang-cl is supported.
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/Program Files/LLVM/bin;{os.environ['PATH']}'
windows_toolchains.append( SimpleNamespace(**{
    'name':'llvm',
    'desc':'# Use Clang-Cl from llvm.org',
    "arch":['x86_64'], # TODO support more architectures
    'platform':['win32'],
    'env': env,
    'cmake':{
        'toolchain':'share\\toolchain-llvm.cmake',
    }
}))

# MARK: LLVM-MinGW
# ╭───────────────────────────────────────────────────────╮
# │  _    _ __   ____  __     __  __ _      _____      __ │
# │ | |  | |\ \ / /  \/  |___|  \/  (_)_ _ / __\ \    / / │
# │ | |__| |_\ V /| |\/| |___| |\/| | | ' \ (_ |\ \/\/ /  │
# │ |____|____\_/ |_|  |_|   |_|  |_|_|_||_\___| \_/\_/   │
# ╰───────────────────────────────────────────────────────╯
# TODO I think that the expansion of the architectures should be here
#   that way I can fill out the necessary cmake variables.
# Perhaps I can simply provide the configure function here, that can be used
# in projects. I guess I will find out when I expand the number of projects
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/llvm-mingw/bin;{os.environ['PATH']}'
windows_toolchains.append( SimpleNamespace(**{
    'name':"llvm-mingw",
    'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
    'sysroot':Path('C:/llvm-mingw'),
    "arch":['i686', 'x86_64', 'armv7', 'aarch64'],
    'platform':['win32'],
    'env': env,
    'cmake': {
        'toolchain':'share\\toolchain-llvm-mingw.cmake',
        # 'build_vars':'-DLLVM_MINGW_PROCESSOR={arch}'
    },
}))

# MARK: MinGW64
# ╭──────────────────────────────────────╮
# │  __  __ _      _____      ____ _ _   │
# │ |  \/  (_)_ _ / __\ \    / / /| | |  │
# │ | |\/| | | ' \ (_ |\ \/\/ / _ \_  _| │
# │ |_|  |_|_|_||_\___| \_/\_/\___/ |_|  │
# ╰──────────────────────────────────────╯
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/mingw64/bin;{os.environ['PATH']}'
windows_toolchains.append( SimpleNamespace(**{
    'name':"mingw64",
    'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
    'sysroot':'C:/mingw64',
    "arch":['x86_64'],
    'platform':['win32'],
    'env': env,
    'cmake': {
        'toolchain':'share\\toolchain-mingw64.cmake'
    },
}))

# MARK: MSYS2
# ╭────────────────────────────╮
# │  __  __ _____   _____ ___  │
# │ |  \/  / __\ \ / / __|_  ) │
# │ | |\/| \__ \\ V /\__ \/ /  │
# │ |_|  |_|___/ |_| |___/___| │
# ╰────────────────────────────╯
windows_toolchains.append( SimpleNamespace(**{
    'name':"msys2-mingw32",
    'desc':'i686      gcc linking against msvcrt',
    'shell': [ "C:/msys64/msys2_shell.cmd", "-mingw32", "-defterm", "-no-start", "-c"],
    "arch":['x86_32'],
    'platform':['win32'],
}))

windows_toolchains.append( SimpleNamespace(**{
    'name':"msys2-mingw64",
    'desc':'x86_64    gcc linking against msvcrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-mingw64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64'],
    'platform':['win32'],
}))

windows_toolchains.append( SimpleNamespace(**{
    'name':"msys2-ucrt64",
    'desc':'x86_64    gcc linking against ucrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-ucrt64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64'],
    'platform':['win32'],
}))

windows_toolchains.append( SimpleNamespace(**{
    'name':"msys2-clang64",
    'desc':'x86_64    clang linking against ucrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-clang64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64'],
    'platform':['win32'],
}))

# MARK: Android
# ╭──────────────────────────────────╮
# │    _           _         _    _  │
# │   /_\  _ _  __| |_ _ ___(_)__| | │
# │  / _ \| ' \/ _` | '_/ _ \ / _` | │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_| │
# ╰──────────────────────────────────╯
# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
def android_update( toolchain:SimpleNamespace, config:SimpleNamespace, console:Console ):
    import os
    from pathlib import Path

    console.set_window_title('Updating Android SDK')
    print(t2("Android Update"))

    sdk_path = Path( toolchain.path )
    os.chdir(sdk_path / 'cmdline-tools/latest/bin')

    cmd_chunks = [
        'sdkmanager.bat',
        '--update',
        '--verbose' if config['quiet'] is False else None,
    ]
    stream_command( ' '.join(filter(None, cmd_chunks)), dry=config['dry'] )

windows_toolchains.append( SimpleNamespace(**{
    'name':'android',
    'desc':'[Android](https://developer.android.com/tools/sdkmanager)',
    'path':Path('C:/androidsdk'),
    'verbs':['update'],
    'update':android_update,
    'arch':['armeabi-v7a','arm64-v8a','x86','x86_64'],
    'platform':['android'],
    'cmake':{
        'toolchain':'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake',
        'ANDROID_PLATFORM': 'latest',
        'ANDROID_ABI':platform.machine()
    }
}))

# MARK: Emscripten
# ╭────────────────────────────────────────────╮
# │  ___                  _      _             │
# │ | __|_ __  ___ __ _ _(_)_ __| |_ ___ _ _   │
# │ | _|| '  \(_-</ _| '_| | '_ \  _/ -_) ' \  │
# │ |___|_|_|_/__/\__|_| |_| .__/\__\___|_||_| │
# │                        |_|                 │
# ╰────────────────────────────────────────────╯
def emscripten_update( toolchain:SimpleNamespace, config:SimpleNamespace, console:Console ):
    import os
    from pathlib import Path

    console.set_window_title('Updating Emscripten SDK')
    print(t2("Emscripten Update"))

    emscripten_path = Path( toolchain.path )
    os.chdir(emscripten_path)
    stream_command( 'git pull', dry=config.dry )

def win32_emscripten_script( config:dict, toolchain:dict ):
    from pathlib import Path

    cmd_prefix = f'pwsh -Command'
    emscripten_tool = (Path(toolchain['path']) / 'emsdk.ps1').as_posix()

    def emscripten_check( line ):
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command( f'{cmd_prefix} "{emscripten_tool} list"',
        stdout_handler=emscripten_check,
        quiet=True,
        dry=config['dry']
    )

    if not ('EMSDK' in os.environ):
        print(t2(f'Emscripten {emscripten_check.task.capitalize()}'))
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}; python {config['script_path']}"',
            dry=config['dry'] )
        quit()

windows_toolchains.append( SimpleNamespace(**{
    'name':'emscripten',
    'desc':'[Emscripten](https://emscripten.org/)',
    'path':Path('C:/emsdk'),
    'version':'3.1.64',
    'verbs':['update', 'script'],
    'update':emscripten_update,
    'script':win32_emscripten_script,
    "arch":['wasm32'], #wasm64
    'platform':['emscripten'],
    'cmake':{
        'toolchain':'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake',
        'generators':['Ninja','Ninja Multi-Config']
    }
}))


# MARK: Darwin
# ╭────────────────────────────────────────────────────────────────────────────╮
# │                 ██████   █████  ██████  ██     ██ ██ ███    ██             │
# │                 ██   ██ ██   ██ ██   ██ ██     ██ ██ ████   ██             │
# │                 ██   ██ ███████ ██████  ██  █  ██ ██ ██ ██  ██             │
# │                 ██   ██ ██   ██ ██   ██ ██ ███ ██ ██ ██  ██ ██             │
# │                 ██████  ██   ██ ██   ██  ███ ███  ██ ██   ████             │
# ╰────────────────────────────────────────────────────────────────────────────╯
darwin_toolchains:list = []

# MARK: AppleClang
# ╭───────────────────────────────────────────────╮
# │    _             _      ___ _                 │
# │   /_\  _ __ _ __| |___ / __| |__ _ _ _  __ _  │
# │  / _ \| '_ \ '_ \ / -_) (__| / _` | ' \/ _` | │
# │ /_/ \_\ .__/ .__/_\___|\___|_\__,_|_||_\__, | │
# │       |_|  |_|                         |___/  │
# ╰───────────────────────────────────────────────╯
darwin_toolchains.append( SimpleNamespace(**{
    'name':"appleclang",
    'desc':"Default toolchain on MacOS",
    'arch':['x86_64','arm64'],
    'platform':['darwin','ios'],
    # Use clang -print-target-triple to get the host triple
}))

# MARK: Emscripten
# ╭────────────────────────────────────────────╮
# │  ___                  _      _             │
# │ | __|_ __  ___ __ _ _(_)_ __| |_ ___ _ _   │
# │ | _|| '  \(_-</ _| '_| | '_ \  _/ -_) ' \  │
# │ |___|_|_|_/__/\__|_| |_| .__/\__\___|_||_| │
# │                        |_|                 │
# ╰────────────────────────────────────────────╯
def darwin_emscripten_script( config:dict, toolchain:dict ):
    from pathlib import Path
    import stat

    cmd_prefix = f'{os.environ['SHELL']} -c'
    emscripten_tool = (Path(toolchain['path']) / 'emsdk').as_posix()

    def emscripten_check( line ):
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command( f'{cmd_prefix} "{emscripten_tool} list"',
        stdout_handler=emscripten_check,
        quiet=True,
        dry=config['dry']
    )

    if not ('EMSDK' in os.environ):
        print(t2(f'Emscripten {emscripten_check.task.capitalize()}'))
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}"',
            dry=config['dry'] )

        env_script = (toolchain['path'] / 'emsdk_env.sh').as_posix()
        os.chmod(env_script, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        stream_command( f'{cmd_prefix} "source {env_script}; python {config['script_path']}"', dry=config['dry'] )
        quit()


darwin_toolchains.append( SimpleNamespace(**{
    'name':'emscripten',
    'desc':'[Emscripten](https://emscripten.org/)',
    'path':Path('/Users/enetheru/emsdk'),
    'version':'3.1.64',
    'verbs':['update', 'script'],
    'update':emscripten_update,
    'script':darwin_emscripten_script,
    "arch":['wasm32'], #wasm64
    'platform':['emscripten'],
    'cmake':{
        'toolchain':'/Users/enetheru/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
    }
}))

# MARK: Select
# ╭────────────────────────────────────────────────────────────────────────────╮
# │                 ███████ ███████ ██      ███████  ██████ ████████           │
# │                 ██      ██      ██      ██      ██         ██              │
# │                 ███████ █████   ██      █████   ██         ██              │
# │                      ██ ██      ██      ██      ██         ██              │
# │                 ███████ ███████ ███████ ███████  ██████    ██              │
# ╰────────────────────────────────────────────────────────────────────────────╯
# Copy the dictionary key into the toolchain as the name

def generate(opts:SimpleNamespace) -> dict:
    import sys

    toolchains:dict = {}

    match sys.platform:
        case 'win32':
            for tc in windows_toolchains:
                toolchains[tc.name] = tc
        case 'darwin':
            for tc in darwin_toolchains:
                toolchains[tc.name] = tc

    return toolchains