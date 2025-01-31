import copy
from pathlib import Path
from types import SimpleNamespace

from rich.console import Console

from share.format import *
from share.run import stream_command

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

# MARK: Toolchains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _                                            │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _  ___                                   │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \(_-<                                   │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_/__/                                   │
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


toolchains = {
    "msvc": SimpleNamespace(**{
        'desc':'# Microsoft Visual Studio',
        'shell':[ "pwsh", "-Command",
            """ "&{Import-Module 'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; Enter-VsDevShell 5ff44efb -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'};" """ ]
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
        'path':Path('C:/emsdk'),
        'version':'3.1.64',
        'verbs':['update', 'write'],
        'update':emsdk_update,
        'script':emsdk_script
    })
}

# Currently only clang-cl is supported.
env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/Program Files/LLVM/bin;{os.environ['PATH']}'
toolchains["llvm"] = SimpleNamespace(**{
    'desc':'# Use Clang-Cl from llvm.org',
    'env': env
})

env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/llvm-mingw/bin;{os.environ['PATH']}'
toolchains["llvm-mingw"] = SimpleNamespace(**{
    'desc':'[llvm based mingw-w64 toolchain](https://github.com/mstorsjo/llvm-mingw)',
    'env': env
})

env = {k:v for k,v in os.environ.items()}
env['PATH'] = f'C:/mingw64/bin;{os.environ['PATH']}'
toolchains["mingw64"] = SimpleNamespace(**{
    'desc':'[mingw](https://github.com/niXman/mingw-builds-binaries/releases,), This is also the default toolchain for clion',
    'env': env
})

def finalise_toolchains():
    for name, toolchain in toolchains.items():

        # set the names
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


