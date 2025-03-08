import itertools
import platform
from types import SimpleNamespace, MethodType
from copy import deepcopy

from share.script_preamble import *

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
def llvm_mingw_expand( self, build:SimpleNamespace ) -> list:
    configs_out:list = []
    for arch, platform in itertools.product(self.arch, self.platform ):
        cfg = deepcopy(build)

        setattr( cfg, 'arch', arch )
        setattr( cfg, 'platform', platform )

        toolchain = cfg.toolchain
        toolchain.cmake['config_vars'] = [f'-DLLVM_MINGW_PROCESSOR={arch}']

        configs_out.append( cfg )
    return configs_out

def llvm_mingw_toolchain() -> SimpleNamespace:
    toolchain = SimpleNamespace(**{
        'name':"llvm-mingw",
        'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
        'sysroot':Path('C:/llvm-mingw'),
        'shell':[ "pwsh", "-Command"],
        "arch":['i686', 'x86_64', 'armv7', 'aarch64'],
        'platform':['win32'],
        'cmake': { 'toolchain':'share\\toolchain-llvm-mingw.cmake' },
    })
    setattr( toolchain, 'expand', MethodType(llvm_mingw_expand, toolchain) )
    return toolchain

windows_toolchains.append( llvm_mingw_toolchain())

# MARK: MinGW64
# ╭──────────────────────────────────────╮
# │  __  __ _      _____      ____ _ _   │
# │ |  \/  (_)_ _ / __\ \    / / /| | |  │
# │ | |\/| | | ' \ (_ |\ \/\/ / _ \_  _| │
# │ |_|  |_|_|_||_\___| \_/\_/\___/ |_|  │
# ╰──────────────────────────────────────╯
windows_toolchains.append( SimpleNamespace(**{
    'name':"mingw64",
    'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
    'sysroot':Path('C:/mingw64'),
    "arch":['x86_64'],
    'platform':['win32'],
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
def android_update( self, opts:SimpleNamespace, console:Console ):
    import os
    from pathlib import Path

    console.set_window_title('Updating Android SDK')
    print(t2("Android Update"))

    sdk_path = Path( self.path )
    os.chdir(sdk_path / 'cmdline-tools/latest/bin')

    cmd_chunks = [
        'sdkmanager.bat',
        '--update',
        '--verbose' if opts.quiet is False else None,
    ]
    stream_command( ' '.join(filter(None, cmd_chunks)), dry=opts.dry )

def android_expand( self, config:SimpleNamespace ) -> list:
    configs_out:list = []
    for abi, platform in itertools.product(self.arch, self.android_platforms ):
        cfg = deepcopy(config)

        setattr( cfg, 'arch', abi )
        setattr( cfg, 'platform', 'android' )

        cfg.toolchain.cmake['config_vars'] = [
            f'-DANDROID_PLATFORM={platform}',
            f'-DANDROID_ABI={abi}'
        ]

        configs_out.append( cfg )

    return configs_out

def android_toolchain() -> SimpleNamespace:
    toolchain = SimpleNamespace(**{
        'name':'android',
        'desc':'[Android](https://developer.android.com/tools/sdkmanager)',
        'path':Path('C:/androidsdk'),
        'verbs':['update'],
        'arch':['armeabi-v7a','arm64-v8a','x86','x86_64'],
        'platform':['android'],
        'android_platforms':['latest'],
        'cmake':{
            'toolchain':'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake',
        }
    })
    setattr( toolchain, 'update', MethodType(android_update, toolchain) )
    setattr( toolchain, 'expand', MethodType(android_expand, toolchain) )

    return toolchain

windows_toolchains.append( android_toolchain() )

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
        print(t2(f'Emscripten {emscripten_check.task.capitalize()}'))
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}; python {build['script_path']}"',
            dry=opts['dry'] )
        quit()

windows_toolchains.append( SimpleNamespace(**{
    'name':'emscripten',
    'desc':'[Emscripten](https://emscripten.org/)',
    'path':Path('C:/emsdk'),
    'version':'3.1.64',
    'verbs':['update', 'script'],
    'update':emscripten_update,
    'script_parts':[win32_emscripten_script],
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
def darwin_emscripten_script():
    toolchain:dict = {}
    opts:dict = {}
    build:dict = {}
    # start_script

    # MARK: Emscripten
    #[=============================[ Emscripten ]=============================]
    import stat

    cmd_prefix = f'{os.environ['SHELL']} -c'
    emscripten_tool = (Path(toolchain['path']) / 'emsdk').as_posix()

    def emscripten_check( line ):
        if toolchain['version'] in line and 'INSTALLED' in line: emscripten_check.task = 'activate'

    emscripten_check.task = 'install'

    stream_command( f'{cmd_prefix} "{emscripten_tool} list"',
        stdout_handler=emscripten_check,
        quiet=True,
        dry=opts['dry']
    )

    if not ('EMSDK' in os.environ):
        print(t2(f'Emscripten {emscripten_check.task.capitalize()}'))
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}"',
            dry=opts['dry'] )

        env_script = (toolchain['path'] / 'emsdk_env.sh').as_posix()
        os.chmod(env_script, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        stream_command( f'{cmd_prefix} "source {env_script}; python {build['script_path']}"', dry=opts['dry'] )
        quit()


darwin_toolchains.append( SimpleNamespace(**{
    'name':'emscripten',
    'desc':'[Emscripten](https://emscripten.org/)',
    'path':Path('/Users/enetheru/emsdk'),
    'version':'3.1.64',
    'verbs':['update', 'script'],
    'update':emscripten_update,
    'script_parts':[darwin_emscripten_script],
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