from io import StringIO
from pathlib import Path, WindowsPath
from types import SimpleNamespace

from rich.console import Console

from share.actions import func_as_script
from share.format import *
from share.run import stream_command

# MARK: Shells
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _        _ _    ___                              _                    │
# │ / __| |_  ___| | |  / __|___ _ __  _ __  __ _ _ _  __| |___                │
# │ \__ \ ' \/ -_) | | | (__/ _ \ '  \| '  \/ _` | ' \/ _` (_-<                │
# │ |___/_||_\___|_|_|  \___\___/_|_|_|_|_|_\__,_|_||_\__,_/__/                │
# ╰────────────────────────────────────────────────────────────────────────────╯
"""
Windows Host
    Compiler Environments / Toolchains
        - msvc
        - mingw32
            - clion builtin
            - mingw64
            - msys64/ucrt64
            - msys64/mingw32
            - msys64/mingw64
        - clang
            - llvm
            - llvm-mingw
            - msys64/clang32
            - msys64/clang64
            - msys64/clangarm64
        - android(clang)
        - emscripten(clang)
Linux Host
    - Compiler Environment / Toolchain
MacOS Host
    - Compiler Environment / Toolchain
"""

shells = {
    # Default Windows
    "pwsh": ["pwsh", "-Command"],
    # Developer Powershell for VS2022
    "pwsh-dev": [
        "pwsh",
        "-Command",
        """&{Import-Module "C:\\\\Program Files\\\\Microsoft Visual Studio\\\\2022\\\\Community\\\\Common7\\\\Tools\\\\Microsoft.VisualStudio.DevShell.dll"; Enter-VsDevShell 5ff44efb -SkipAutomaticLocation -DevCmdArguments "-arch=x64 -host_arch=x64"};""",
    ],
    # MSYS2 GCC
    "msys2-mingw32": [
        "C:/msys64/msys2_shell.cmd",
        "-mingw32",
        "-defterm",
        "-no-start",
        "-c",
    ],
    "msys2-mingw64": [
        "C:/msys64/msys2_shell.cmd",
        "-mingw64",
        "-defterm",
        "-no-start",
        "-c",
    ],
    "msys2-ucrt64": [
        "C:/msys64/msys2_shell.cmd",
        "-ucrt64",
        "-defterm",
        "-no-start",
        "-c",
    ],
    # MSYS2 Clang
    "msys2-clang64": [
        "C:/msys64/msys2_shell.cmd",
        "-clang64",
        "-defterm",
        "-no-start",
        "-c",
    ],
    "msys2-clangarm64": [
        "C:/msys64/msys2_shell.cmd",
        "-clangarm64",
        "-defterm",
        "-no-start",
        "-c",
    ],
    # MSYS2 default, doesnt really have a utility, ust here for completion
    "msys2": ["C:/msys64/msys2_shell.cmd", "-msys", "-defterm", "-no-start", "-c"],
    "emsdk": ["pwsh", "-Command", "C:/emsdk/emsdk_env.ps1;"],
}

# MARK: Toolchains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _                                            │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _  ___                                   │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \(_-<                                   │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_/__/                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
def emsdk_update( toolchain, config:SimpleNamespace, console:Console ):
    import os
    from pathlib import Path

    emsdk_path = Path( 'C:/emsdk' )

    console.set_window_title('Updating Emscripten SDK')
    h3("Update Emscripten SDK")

    os.chdir(emsdk_path)
    stream_command( 'git pull', dry=config.dry )

def emsdk_script( config:dict, console:Console ):
    import os
    from pathlib import Path

    def emsdk_check( config:dict, console:Console ):
        # C:\emsdk\emsdk.ps1 list --help | rg INSTALLED
        pass

    def emsdk_activate(config:dict, console:Console):
        toolchain = config['toolchain']
        chunks = [
            toolchain['shell'],
            Path(toolchain['root']) / 'emsdk',
            'activate',
            toolchain['version']
        ]
        stream_command( ' '.join(chunks), dry=config['dry'] )

    emsdk_path = Path( 'C:/emsdk' )
    emsdk_version = '3.1.64'

    console.set_window_title('Updating Emscripten SDK')
    h3("Update Emscripten SDK")

    os.chdir(emsdk_path)
    stream_command( 'git pull', dry=config.dry )

    # Projects need to activate or install specific versions of the sdk themselves
    # typucally using some variation of the below command.
    # stream_command( f'pwsh emsdk.ps1 install {emsdk_version}', dry=config.dry )

def emsdk_write( build:SimpleNamespace, script:StringIO ):
    script.write( func_as_script(emsdk_script) )

toolchains = {
    "msvc": SimpleNamespace(**{
        'desc':'# Microsoft Visual Studio',
        'shell':[ "pwsh", "-Command", """&{Import-Module "C:\\\\Program Files\\\\Microsoft Visual Studio\\\\2022\\\\Community\\\\Common7\\\\Tools\\\\Microsoft.VisualStudio.DevShell.dll"; Enter-VsDevShell 5ff44efb -SkipAutomaticLocation -DevCmdArguments "-arch=x64 -host_arch=x64"};""" ]
    }),
    "llvm": SimpleNamespace(**{
        'desc':'# Use Clang-Cl from llvm.org',
        'env_map': {'PATH':"C:/Program Files/LLVM/bin"}
    }),
    "llvm-mingw": SimpleNamespace(**{
        'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
        'env_map': {'PATH':"C:/llvm-mingw/bin"}
    }),
    "mingw64": SimpleNamespace(**{
        'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
        'env_map': {'PATH':"C:/mingw64/bin"}
    }),
    "msys2-mingw32": SimpleNamespace(**{
        'desc':'i686      gcc linking against msvcrt',
        'shell': [ "C:/msys64/msys2_shell.cmd", "-mingw32", "-defterm", "-no-start", "-c"],
    }),
    "msys2-mingw64": SimpleNamespace(**{
        'desc':'x86_64    gcc linking against msvcrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-mingw64", "-defterm", "-no-start", "-c"],
    }),
    "msys2-ucrt64": SimpleNamespace(**{
        'desc':'x86_64    gcc linking against ucrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-ucrt64", "-defterm", "-no-start", "-c"],
    }),
    "msys2-clang32": SimpleNamespace(**{
        'desc':'i686      clang linking against ucrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-clang32", "-defterm", "-no-start", "-c"],
    }),
    "msys2-clang64": SimpleNamespace(**{
        'desc':'x86_64    clang linking against ucrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-clang64", "-defterm", "-no-start", "-c"],
    }),
    "msys2-clangarm64": SimpleNamespace(**{
        'desc':'aarch64   clang linking against ucrt',
        'shell': ["C:/msys64/msys2_shell.cmd", "-clangarm64", "-defterm", "-no-start", "-c"],
    }),
    "android": SimpleNamespace(**{
        'desc':'[Android](https://developer.android.com/tools/sdkmanager)',
    }),
    "emsdk": SimpleNamespace(**{
        'desc':'[Emscripten](https://emscripten.org/)',
        'root':Path('C:/emsdk'),
        'verbs':['update', 'write'],
        'update':emsdk_update,
        'shell': ["pwsh", "-Command", "C:/emsdk/emsdk_env.ps1;"],
        'write': emsdk_write
    })
}

def finalise_toolchains():
    for name, toolchain in toolchains.items():
        setattr(toolchain, 'name', name )

finalise_toolchains()

# MARK: Toolchain Scripts
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _        ___         _      _                │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _   / __| __ _ _(_)_ __| |_ ___          │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \  \__ \/ _| '_| | '_ \  _(_-<          │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| |___/\__|_| |_| .__/\__/__/          │
# │                                                     |_|                    │
# ╰────────────────────────────────────────────────────────────────────────────╯

def env_mingw64_script(config:dict, console:Console):
    import os
    from pathlib import Path

    mingw_path = Path("C:/mingw64/bin" )

    h4(f'prepending {mingw_path} PATH')
    os.environ['PATH'] = f'{mingw_path};{os.environ.get('PATH')}'

def env_llvm_script(config:dict, console:Console):
    import os
    from pathlib import Path

    llvm_path = Path("C:/Program Files/LLVM/bin" )

    h4( f'prepending "{llvm_path}" to PATH' )
    os.environ['PATH'] = f'{llvm_path};{os.environ.get('PATH')}'

def env_llvm_mingw_script(config:dict, console:Console):
    import os
    from pathlib import Path

    llvm_mingw_path = Path("C:/llvm-mingw/bin" )

    h4( f'prepending "{llvm_mingw_path}" to PATH' )
    os.environ['PATH'] = f'{llvm_mingw_path};{os.environ.get('PATH')}'

def env_android_script(config:dict, console:Console):
    import os
    from pathlib import Path

    cmdlineTools = Path("C:/androidsdk/cmdline-tools/latest/bin")

    h4( f'prepending "{cmdlineTools}" to PATH' )
    os.environ['PATH'] = f'{cmdlineTools};{os.environ.get('PATH')}'

    if 'update' in config['actions']:
        console.set_window_title('Updating Android SDK')
        h3("Update Android SDK")

        cmd_chunks = [
            'sdkmanager.bat',
            '--update',
            '--verbose' if config['quiet'] is False else None,
        ]
        stream_command( ' '.join(filter(None, cmd_chunks)), dry=config['dry'] )

# MARK: Preamble
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _     ___                    _    _                    │
# │ / __| __ _ _(_)_ __| |_  | _ \_ _ ___ __ _ _ __ | |__| |___                │
# │ \__ \/ _| '_| | '_ \  _| |  _/ '_/ -_) _` | '  \| '_ \ / -_)               │
# │ |___/\__|_| |_| .__/\__| |_| |_| \___\__,_|_|_|_|_.__/_\___|               │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯

def namespace_to_script( name:str, namespace:SimpleNamespace, script:StringIO ):
    chunk = [f"{name} = {{"]
    skip_keys = []
    if 'skip_keys' in namespace.__dict__.keys():
        skip_keys = namespace.skip_keys

    for k, v in namespace.__dict__.items():
        if k in skip_keys: continue
        # Fix Windows Path Items
        if isinstance(v, WindowsPath):
            chunk.append(f"\t{repr(k)}:Path({repr(str(v))}),")
            continue
        # Skip Functions
        if callable(v): continue
        # recurse over other namespaces
        if isinstance(v, SimpleNamespace):
            namespace_to_script( k, v, script )
            continue
        # Skip Multi-Line Scripts.
        if type(v) is str and '\n' in v: continue
        chunk.append(f"\t{repr(k)}:{repr(v)},")
    chunk.append("}\n")
    script.write( "\n".join(chunk) )


def write_preamble(config: SimpleNamespace, script:StringIO):
    script.write( f"""
import sys
sys.path.append({repr(str(config.root_dir))})

from pathlib import Path
import rich
from rich.console import Console

from share.format import *
from share.run import stream_command

rich._console = console = Console(soft_wrap=False, width=9000)

""")
    namespace_to_script('config', config, script )
