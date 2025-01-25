from types import SimpleNamespace

from share.format import *

# Incase I forget here is the command for these banners:
# CodeBox -border "╭─╮│ │╰─╯" -compact -align left -font 'small' Shell Commands

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
    'pwsh':['pwsh', '-Command' ],
    # MSYS2 GCC
    'msys2-mingw32': ['C:/msys64/msys2_shell.cmd', '-mingw32', '-defterm', '-no-start', '-c' ],
    'msys2-mingw64': ['C:/msys64/msys2_shell.cmd', '-mingw64', '-defterm', '-no-start', '-c' ],
    'msys2-ucrt64': ['C:/msys64/msys2_shell.cmd', '-ucrt64', '-defterm', '-no-start', '-c' ],
    # MSYS2 Clang
    'msys2-clang64': ['C:/msys64/msys2_shell.cmd', '-clang64', '-defterm', '-no-start', '-c' ],
    'msys2-clangarm64': ['C:/msys64/msys2_shell.cmd', '-clangarm64', '-defterm', '-no-start', '-c' ],
    # MSYS2 default, doesnt really have a utility, ust here for completion
    'msys2': ['C:/msys64/msys2_shell.cmd', '-msys', '-defterm', '-no-start', '-c' ],

    # TODO Emscripten
}

# TODO add Developer Powershell for VS2022
# Developer Powershell for VS2022 lists this for command line
# powershell.exe -NoExit -Command "&{Import-Module """C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\Microsoft.VisualStudio.DevShell.dll"""; Enter-VsDevShell 5ff44efb -SkipAutomaticLocation -DevCmdArguments """-arch=x64 -host_arch=x64"""}"

# MARK: Toolchains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _                                            │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _  ___                                   │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \(_-<                                   │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_/__/                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
toolchains = ['msvc',               # Microsoft Visual Studio
              'llvm',               # Use Clang-Cl from llvm.org
              'llvm-mingw',         # llvm based mingw-w64 toolchain.
              #   https://github.com/mstorsjo/llvm-mingw
              'mingw64',            # mingw from https://github.com/niXman/mingw-builds-binaries/releases,
              #   This is also the default toolchain for clion.
              'msys2-mingw32',      # i686      gcc linking against msvcrt
              'msys2-mingw64',      # x86_64    gcc linking against msvcrt
              'msys2-ucrt64',       # x86_64    gcc linking against ucrt
              'msys2-clang32',      # i686      clang linking against ucrt
              'msys2-clang64',      # x86_64    clang linking against ucrt
              'msys2-clangarm64',   # aarch64   clang linking against ucrt
              'android',            # https://developer.android.com/tools/sdkmanager
              'emscripten',         # https://emscripten.org/
              ]

# MARK: Toolchain Scripts
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _        ___         _      _                │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _   / __| __ _ _(_)_ __| |_ ___          │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \  \__ \/ _| '_| | '_ \  _(_-<          │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| |___/\__|_| |_| .__/\__/__/          │
# │                                                     |_|                    │
# ╰────────────────────────────────────────────────────────────────────────────╯

toolchain_scripts = {
# Mingw64
    'mingw64':"""
import os
from share.format import *

mingw_path = Path("C:/mingw64/bin" )

h4(f'prepending {mingw_path} PATH')
os.environ['PATH'] = f'{mingw_path};{os.environ.get('PATH')}' 
""",

# LLVM
    'llvm':"""
import os
from share.format import *

llvm_path = Path("C:/Program Files/LLVM/bin" )

h4( f'prepending "{llvm_path}" to PATH' )
os.environ['PATH'] = f'{llvm_path};{os.environ.get('PATH')}'
""",

# Android
    'android':"""
import os
from share.format import *

cmdlineTools = Path("C:/androidsdk/cmdline-tools/latest/bin")

h4( f'prepending "{cmdlineTools}" to PATH' )
os.environ['PATH'] = f'{cmdlineTools};{os.environ.get('PATH')}'

if config['update']:
    console.set_window_title('Updating Android SDK')
    h3("Update Android SDK")
    
    cmd_chunks = [
        'sdkmanager.bat',
        '--update',
        '--verbose' if config['quiet'] is False else None,
    ]
    command = ' '.join(filter(None, cmd_chunks))

    print_eval( command, dry=config['dry'] )
""",

# Emscripten
    'emscripten':"""
#     param(
#         $emsdk = "C:\emsdk",
#         $version = "latest"
#     )
#     H3 "Update Emscripten SDK"
#     
#     if( -Not (Test-Path -Path "$emsdk" -PathType Container) ) {
#         Write-Error "Missing emsdk Path: '$emsdk'"
#         return 1
#     }
#     if( -Not (Test-Path -Path "$emsdk\emsdk.ps1" -PathType Leaf) ) {
#         Write-Error "Missing Script: '$emsdk\emsdk.ps1'"
#         return 1
#     }
#     
#     if( $version -match "latest" ){
#         # scons: *** [bin\.web_zip\godot.editor.worker.js] The system cannot find the file specified
#         # https://forum.godotengine.org/t/error-while-building-godot-4-3-web-template/86368
#         
#         Write-Warning "Latest Emscripten version is not oficially supported"
#         Write-Output @"
#     # Official Requirements:
#     # godotengine - 4.0+     | Emscripten 1.39.9
#     # godotengine - 4.2+     | Emscripten 3.1.39
#     # godotengine - master  | Emscripten 3.1.62
#     #
#     # But in the github action runner, it's 3.1.64
#     # And all of the issues related show 3.1.64
# "@
#     }
#     
#     Set-Location $emsdk
#     Format-Eval git pull
#     
#     Format-Eval $emsdk\emsdk.ps1 install $version

# Activate Escripten
    # param(
    #     $emsdk = "C:\emsdk",
    #     $version = "latest"
    # )
    # if( $emsdk_activated -eq $True ){
    #     H4 "Emscripten SDK is already activated."
    #     return
    # }
    # H4 "Activate Emscripten SDK"
    # Format-Eval "$emsdk\emsdk.ps1" activate $version
    # $emsdk_activated = $True
"""
}

def python_toolchain( config:SimpleNamespace ):
    env_mod = '# No Environment Modifications'
    if config.toolchain in toolchain_scripts.keys():
        env_mod =  toolchain_scripts[config.toolchain]

    return env_mod + centre( ' End of Toolchain Modifications ', left( '\n#', fill( '- ', 80)))

# MARK: Preamble
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _     ___                    _    _                    │
# │ / __| __ _ _(_)_ __| |_  | _ \_ _ ___ __ _ _ __ | |__| |___                │
# │ \__ \/ _| '_| | '_ \  _| |  _/ '_/ -_) _` | '  \| '_ \ / -_)               │
# │ |___/\__|_| |_| .__/\__| |_| |_| \___\__,_|_|_|_|_.__/_\___|               │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯
#[===============================[ PowerShell ]===============================]
def pwsh_preamble( defs:dict, command:str ) -> str:
    mini_script = ''
    for k, v in defs.items():
        mini_script += f'${k}="{v}"\n'
    mini_script += command
    return mini_script

#[=================================[ Python ]=================================]
def python_preamble( config:SimpleNamespace ) -> str:
    from pathlib import WindowsPath
    script = f"""
import sys
from pathlib import Path
import rich
from rich.console import Console

rich._console = console = Console(soft_wrap=False, width=9000)
sys.path.append({repr(str(config.root_dir))})

"""
    chunk = ['config = {']
    for k, v in config.__dict__.items():
        # Skip items that we dont want
        if k in ['script']:
            continue
        if isinstance( v, WindowsPath ):
            chunk.append( f'\t{repr(k)}:Path({repr(str(v))}),' )
            continue
        chunk.append( f'\t{repr(k)}:{repr(v)},' )
    chunk.append( '}\n' )
    script += '\n'.join( chunk )

    script += centre( ' End Of Preamble ', left( '\n#', fill( '- ', 80)))
    script += '\n'
    return script