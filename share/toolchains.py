import itertools
import subprocess
from copy import deepcopy
from types import SimpleNamespace, MethodType

from typing import Mapping, Any, cast

from share.script_preamble import *

import share.android

# Since these things are getting a little complicated lets try to make a little example for myself.
example_mapping = SimpleNamespace(**cast(Mapping[str, Any], {
    'name'      :'name of the compiler, keep short',
    'desc'      :'description of the compiler, can be any length',
    'shell'     :[ "bash", "-c", """ "echo \"shell and script to pass to shell, can be a little awkward to write due to escaping\"" """ ],
    'arch'      :['list','of', 'target', 'architectures', 'like', 'x86_64', 'arm64', 'etc'],
    'platform'  :['list','of', 'target', 'platforms', 'matches', 'values', 'from', 'sys.platform']
}))


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

def msvc_toolchain() -> SimpleNamespace:
    # get the visual studio instance ID
    instance_cmd  = "C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"
    instance_id = subprocess.check_output([instance_cmd, '-property', 'instanceId']).strip().decode('utf-8')

    toolchain = SimpleNamespace(**cast( Mapping[str,Any],{
        'name':'msvc',
        'desc':'# Microsoft Visual Studio',
        'shell':[ "pwsh", "-Command",
                  f""" "&{{Import-Module 'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; Enter-VsDevShell {instance_id} -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'}};" """ ],
        "arch":['x86_64'],
        'platform':['win32']
    }))
    return toolchain

windows_toolchains.append( msvc_toolchain() )

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
windows_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
    'name':'llvm',
    'desc':'# Use Clang-Cl from llvm.org',
    "arch":['x86_64'], # TODO support more architectures
    'platform':['win32'],
    'env': env,
    'cmake':{
        'toolchain':'share\\toolchain-llvm.cmake',
    }
})))

# MARK: LLVM-MinGW
# ╭───────────────────────────────────────────────────────╮
# │  _    _ __   ____  __     __  __ _      _____      __ │
# │ | |  | |\ \ / /  \/  |___|  \/  (_)_ _ / __\ \    / / │
# │ | |__| |_\ V /| |\/| |___| |\/| | | ' \ (_ |\ \/\/ /  │
# │ |____|____\_/ |_|  |_|   |_|  |_|_|_||_\___| \_/\_/   │
# ╰───────────────────────────────────────────────────────╯
# C:\opt\llvm-mingw-20250305-ucrt-x86_64\bin\
def llvm_mingw_expand( self, build:SimpleNamespace ) -> list:
    """Expand LLVM-MinGW toolchain configurations for supported architectures and platforms.

    Args:
        self (SimpleNamespace): The toolchain configuration.
        build (SimpleNamespace): The build configuration to expand.

    Returns:
        list[SimpleNamespace]: List of expanded build configurations with architecture and platform settings.
    """
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
    sysroot = f'C:/opt/llvm-mingw-20250305-ucrt-x86_64'
    toolchain_env = {k:v for k,v in os.environ.items()}
    toolchain_env['PATH'] = f'{sysroot};{os.environ['PATH']}'

    toolchain = SimpleNamespace(**cast( Mapping[str,Any],{
        'name':"llvm-mingw",
        'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
        'sysroot':Path(sysroot),
        'shell':[ "pwsh", "-Command"],
        "arch":['i686', 'x86_64', 'armv7', 'aarch64'],
        'platform':['win32'],
        'env': toolchain_env,
        'cmake': { 'toolchain':'share\\toolchain-llvm-mingw.cmake' },
    }))
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
def mingw64_toolchain() -> SimpleNamespace:
    toolchain_env = {k:v for k,v in os.environ.items()}
    toolchain_env['PATH'] = f'C:/mingw64/bin;{os.environ['PATH']}'

    toolchain = SimpleNamespace(**cast( Mapping[str,Any],{
        'name':"mingw64",
        'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
        'sysroot':Path('C:/mingw64'),
        "arch":['x86_64'],
        'platform':['win32'],
        'env': toolchain_env,
        'cmake': {
            'toolchain':'share\\toolchain-mingw64.cmake'
        },
    }))
    return toolchain


windows_toolchains.append( mingw64_toolchain())



# MARK: MSYS2
# ╭────────────────────────────╮
# │  __  __ _____   _____ ___  │
# │ |  \/  / __\ \ / / __|_  ) │
# │ | |\/| \__ \\ V /\__ \/ /  │
# │ |_|  |_|___/ |_| |___/___| │
# ╰────────────────────────────╯

# It's unfortunate that the godot-cpp build system only looks for prefixed commands.
# I have had to create symlinks for clang64 so that it can find the ar command
# in C:\msys64/cang64/bin
# ln -s ar.exe x86_64-w64-mingw32-llvm-ar.exe

windows_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
    'name':"msys2-mingw32",
    'desc':'i686      gcc linking against msvcrt',
    'shell': [ "C:/msys64/msys2_shell.cmd", "-mingw32", "-defterm", "-no-start", "-c"],
    "arch":['x86_32'],
    'platform':['win32'],
})))

windows_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
    'name':"msys2-mingw64",
    'desc':'x86_64    gcc linking against msvcrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-mingw64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64'],
    'platform':['win32'],
})))

windows_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
    'name':"msys2-ucrt64",
    'desc':'x86_64    gcc linking against ucrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-ucrt64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64'],
    'platform':['win32'],
})))

windows_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
    'name':"msys2-clang64",
    'desc':'x86_64    clang linking against ucrt',
    'shell': ["C:/msys64/msys2_shell.cmd", "-clang64", "-defterm", "-no-start", "-c"],
    "arch":['x86_64'],
    'platform':['win32'],
})))

# MARK: Android
# ╭──────────────────────────────────╮
# │    _           _         _    _  │
# │   /_\  _ _  __| |_ _ ___(_)__| | │
# │  / _ \| ' \/ _` | '_/ _ \ / _` | │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_| │
# ╰──────────────────────────────────╯
# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
def android_update( self, toolchain:SimpleNamespace,  opts:SimpleNamespace, console:Console ):
    console.set_window_title('Updating Android SDK')
    print(fmt.t2("Android Update"))

    packages = share.android.list_installed()
    print( f"installed_packages: {packages}")

    wanted = {
        'platform-tools':'',
        "build-tools":"35.0.0",
        "platforms":"android-35",
        "cmdline-tools":"latest",
        "cmake":"3.10.2.4988404",
        'ndk':'28.1.13356709',
    }

    for package,version in wanted.items():
        print(f"Checking for {package};{version}")
        if not any(package["package"] == package and package["version"] == version for package in packages):
            share.android.install( f'{package};{version}' )


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
    toolchain = SimpleNamespace(**cast( Mapping[str,Any],{
        'name':'android',
        'desc':'[Android](https://developer.android.com/tools/sdkmanager)',
        'path':Path('C:/androidsdk'),
        'verbs':['update'],
        'arch':['armeabi-v7a','arm64-v8a','x86','x86_64'],
        'platform':['android'],
        'sdk':Path('C:/androidsdk'),
        'android_platforms':['latest'],
        'android_api_level':'24',
        'packages': {
            'platform-tools':'',
            "build-tools":"35.0.0",
            "platforms":"android-35",
            "cmdline-tools":"latest",
            "cmake":"3.10.2.4988404",
            'ndk':'28.1.13356709',
        },
        'cmake':{
            'toolchain':'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake',
        }
    }))
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

windows_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
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
})))


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
darwin_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
    'name':"appleclang",
    'desc':"Default toolchain on MacOS",
    'arch':['x86_64','arm64'],
    'platform':['darwin','ios'],
    # Use clang -print-target-triple to get the host triple
})))

# MARK: Emscripten
# ╭────────────────────────────────────────────╮
# │  ___                  _      _             │
# │ | __|_ __  ___ __ _ _(_)_ __| |_ ___ _ _   │
# │ | _|| '  \(_-</ _| '_| | '_ \  _/ -_) ' \  │
# │ |___|_|_|_/__/\__|_| |_| .__/\__\___|_||_| │
# │                        |_|                 │
# ╰────────────────────────────────────────────╯
def darwin_emscripten_script():
    """Generate a script to activate the Emscripten SDK on macOS.

    Returns:
        None: Executes commands to check and activate the Emscripten SDK, updating environment variables.

    Notes:
        Requires the Emscripten SDK path to be set in the toolchain configuration.
    """
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
        print(fmt.t2(f'Emscripten {emscripten_check.task.capitalize()}'))
        stream_command( f'{cmd_prefix} "{emscripten_tool} {emscripten_check.task} {toolchain['version']}"',
            dry=opts['dry'] )

        env_script = (toolchain['path'] / 'emsdk_env.sh').as_posix()
        os.chmod(env_script, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        stream_command( f'{cmd_prefix} "source {env_script}; python {build['script_path']}"', dry=opts['dry'] )
        quit()


darwin_toolchains.append( SimpleNamespace(**cast( Mapping[str,Any],{
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
})))

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
    """Generate a dictionary of available toolchains for the current platform.

    Args:
        opts (SimpleNamespace): Configuration options including the platform.

    Returns:
        dict: A dictionary mapping toolchain names to their SimpleNamespace configurations.
    """
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