import itertools
import shlex
import subprocess
from copy import deepcopy
from types import SimpleNamespace, MethodType

from share import android
from share.config import toolchain_base, gopts
from share.script_preamble import *

def generic_toolchain_expand( self:SimpleNamespace, cfg:SimpleNamespace ) -> list:
    configs_out:list = []

    for arch, platform in itertools.product(self.arch_list, self.platform_list):
        cfg = deepcopy(cfg)
        setattr(cfg, 'toolchain', self )
        setattr(cfg, 'arch', arch )
        setattr(cfg, 'platform', platform )
        configs_out.append( cfg )

    return configs_out


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
    installation_path = subprocess.check_output([instance_cmd, '-property', 'installationPath']).strip().decode('utf-8')

    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':'msvc',
        'desc':'# Microsoft Visual Studio',
        'shell':[ "pwsh", "-Command",
                  f""" "&{{Import-Module '{shlex.quote(installation_path).strip("'")}\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; Enter-VsDevShell {instance_id} -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'}};" """ ],
        "arch_list":['x86_64'],
        'platform_list':['win32'],
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
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

def configure_llvm( self:SimpleNamespace, config:SimpleNamespace ) -> bool:
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = gopts.path / 'share' / 'toolchain-llvm.cmake'

    return True


def llvm_toolchain() -> SimpleNamespace:
    env = {k:v for k,v in os.environ.items()}
    env['PATH'] = f'C:/Program Files/LLVM/bin;{os.environ['PATH']}'
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':'llvm',
        'desc':'# Use Clang-Cl from llvm.org',
        "arch_list":['x86_64'], # TODO support more architectures
        'platform_list':['win32'],
        'env': env,
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    setattr( toolchain, 'configure', MethodType(configure_llvm, toolchain ) )
    return toolchain

windows_toolchains.append( llvm_toolchain() )

# MARK: LLVM-MinGW
# ╭───────────────────────────────────────────────────────╮
# │  _    _ __   ____  __     __  __ _      _____      __ │
# │ | |  | |\ \ / /  \/  |___|  \/  (_)_ _ / __\ \    / / │
# │ | |__| |_\ V /| |\/| |___| |\/| | | ' \ (_ |\ \/\/ /  │
# │ |____|____\_/ |_|  |_|   |_|  |_|_|_||_\___| \_/\_/   │
# ╰───────────────────────────────────────────────────────╯
# C:\opt\llvm-mingw-20250305-ucrt-x86_64\bin\

def configure_llvm_mingw( self:SimpleNamespace, config:SimpleNamespace ) -> bool:
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = gopts.path / 'share' / 'toolchain-llvm-mingw.cmake'
            cmake.config_vars.append(f'-DLLVM_MINGW_PROCESSOR={config.arch}')

    return True


def llvm_mingw_toolchain() -> SimpleNamespace:
    sysroot = Path(f'C:/opt/llvm-mingw-20250305-ucrt-x86_64')
    toolchain_env = {k:v for k,v in os.environ.items()}
    toolchain_env['PATH'] = f'{sysroot / 'bin'};{os.environ['PATH']}'

    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':"llvm-mingw",
        'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
        'sysroot':Path(sysroot),
        'shell':[ "pwsh", "-Command"],
        "arch_list":['i686', 'x86_64', 'armv7', 'aarch64'],
        'platform_list':['win32'],
        'env': toolchain_env,
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    setattr( toolchain, 'configure', MethodType(configure_llvm_mingw, toolchain ) )
    return toolchain

windows_toolchains.append( llvm_mingw_toolchain())

# MARK: MinGW64
# ╭──────────────────────────────────────╮
# │  __  __ _      _____      ____ _ _   │
# │ |  \/  (_)_ _ / __\ \    / / /| | |  │
# │ | |\/| | | ' \ (_ |\ \/\/ / _ \_  _| │
# │ |_|  |_|_|_||_\___| \_/\_/\___/ |_|  │
# ╰──────────────────────────────────────╯

def configure_mingw( self:SimpleNamespace, config:SimpleNamespace ):
    match config.buildtool.name:
        case 'cmake':
            cmake = config.buildtool
            cmake.toolchain = 'share\\toolchain-mingw64.cmake'

def mingw64_toolchain() -> SimpleNamespace:
    toolchain_env = {k:v for k,v in os.environ.items()}
    toolchain_env['PATH'] = f'C:/mingw64/bin;{os.environ['PATH']}'

    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':"mingw64",
        'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
        'sysroot':Path('C:/mingw64'),
        "arch_list":['x86_64'],
        'platform_list':['win32'],
        'env': toolchain_env,
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    setattr( toolchain, 'configure', MethodType(configure_mingw, toolchain ) )
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
def msys2_mingw32_toolchain() -> SimpleNamespace:
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':"msys2-mingw32",
        'desc':'i686      gcc linking against msvcrt',
        'shell': [ "C:/msys64/msys2_shell.cmd", "-mingw32", "-defterm", "-no-start", "-c"],
        "arch_list":['x86_32'],
        'platform_list':['win32'],
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    return toolchain

windows_toolchains.append( msys2_mingw32_toolchain() )


def msys2_mingw64_toolchain() -> SimpleNamespace:
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':"msys2-mingw64",
        'desc':'x86_64    gcc linking against msvcrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-mingw64", "-defterm", "-no-start", "-c"],
        "arch_list":['x86_64'],
        'platform_list':['win32'],
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    return toolchain
windows_toolchains.append( msys2_mingw64_toolchain() )

def msys2_ucrt64_toolchain() -> SimpleNamespace:
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':"msys2-ucrt64",
        'desc':'x86_64    gcc linking against ucrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-ucrt64", "-defterm", "-no-start", "-c"],
        "arch_list":['x86_64'],
        'platform_list':['win32'],
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    return toolchain
windows_toolchains.append( msys2_ucrt64_toolchain() )

def msys2_clang64_toolchain() -> SimpleNamespace:
    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name':"msys2-clang64",
        'desc':'x86_64    clang linking against ucrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-clang64", "-defterm", "-no-start", "-c"],
        "arch_list":['x86_64'],
        'platform_list':['win32'],
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    return toolchain
windows_toolchains.append( msys2_clang64_toolchain() )

# MARK: Android
# ╭──────────────────────────────────╮
# │    _           _         _    _  │
# │   /_\  _ _  __| |_ _ ___(_)__| | │
# │  / _ \| ' \/ _` | '_/ _ \ / _` | │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_| │
# ╰──────────────────────────────────╯
# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/

windows_toolchains.append( android.android_toolchain() )

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
        "arch_list":['wasm32'], #wasm64
        'platform_list':['emscripten'],
        'cmake':win32_emscripten_cmake,
    }})
    setattr( toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain ) )
    setattr( toolchain, 'update', MethodType(emscripten_update, toolchain) )
    return toolchain

windows_toolchains.append( win32_emscripten_toolchain() )

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
darwin_toolchains.append( SimpleNamespace({**vars(toolchain_base), **{
    'name':"appleclang",
    'desc':"Default toolchain on MacOS",
    'arch':['x86_64','arm64'],
    'platform':['darwin','ios'],
    # Use clang -print-target-triple to get the host triple
}}))

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

def darwin_emscripten_cmake( build:SimpleNamespace ):
    toolchain = build.toolchain
    cmake = build.buildtool
    cmake.toolchain = '/Users/enetheru/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'

darwin_toolchains.append( SimpleNamespace({**vars(toolchain_base), **{
    'name':'emscripten',
    'desc':'[Emscripten](https://emscripten.org/)',
    'path':Path('/Users/enetheru/emsdk'),
    'version':'3.1.64',
    'verbs':['update', 'script'],
    'update':emscripten_update,
    'script_parts':[darwin_emscripten_script],
    "arch":['wasm32'], #wasm64
    'platform':['emscripten'],
    'cmake':darwin_emscripten_cmake
}}))

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