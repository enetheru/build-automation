from types import SimpleNamespace

# MARK: Shell Commands
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _        _ _    ___                              _                    │
# │ / __| |_  ___| | |  / __|___ _ __  _ __  __ _ _ _  __| |___                │
# │ \__ \ ' \/ -_) | | | (__/ _ \ '  \| '  \/ _` | ' \/ _` (_-<                │
# │ |___/_||_\___|_|_|  \___\___/_|_|_|_|_|_\__,_|_||_\__,_/__/                │
# ╰────────────────────────────────────────────────────────────────────────────╯

shells = {
    'pwsh':['pwsh', '-Command' ],
    'msys2.mingw32': ['C:/msys64/msys2_shell.cmd', '-mingw32', '-defterm', '-no-start', '-c' ],
    'msys2.mingw64': ['C:/msys64/msys2_shell.cmd', '-mingw64', '-defterm', '-no-start', '-c' ],
    'msys2.ucrt64': ['C:/msys64/msys2_shell.cmd', '-ucrt64', '-defterm', '-no-start', '-c' ],
    'msys2.clang64': ['C:/msys64/msys2_shell.cmd', '-clang64', '-defterm', '-no-start', '-c' ],
    'msys2.msys': ['C:/msys64/msys2_shell.cmd', '-msys', '-defterm', '-no-start', '-c' ],
    'msys2.clangarm64': ['C:/msys64/msys2_shell.cmd', '-clangarm64', '-defterm', '-no-start', '-c' ]
    # TODO Emscripten
}

#[===============================[ PowerShell ]===============================]
def pwsh_preamble( defs:dict, command:str ) -> str:
    mini_script = ''
    for k, v in defs.items():
        mini_script += f'${k}="{v}"\n'
    mini_script += command
    return mini_script

def pwsh_command() -> list:
    return ['pwsh', '-Command']

#[=================================[ Python ]=================================]
def python_preamble( config:SimpleNamespace ) -> str:
    from pathlib import WindowsPath
    mini_script = 'import sys\n'
    mini_script += f'sys.path.append({repr(str(config.root_dir))})\n'
    mini_script += 'config = {\n'
    for k, v in config.__dict__.items():
        # Skip items that we dont want
        if k in ['script']:
            continue
        if isinstance( v, WindowsPath ):
            mini_script += f'\t{repr(k)}:{repr(str(v))},\n'
            continue
        mini_script += f'\t{repr(k)}:{repr(v)},\n'
    mini_script += '}\n'
    return mini_script

# MARK: Script Processing
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _     ___                       _                      │
# │ / __| __ _ _(_)_ __| |_  | _ \_ _ ___  __ ___ _____(_)_ _  __ _            │
# │ \__ \/ _| '_| | '_ \  _| |  _/ '_/ _ \/ _/ -_|_-<_-< | ' \/ _` |           │
# │ |___/\__|_| |_| .__/\__| |_| |_| \___/\__\___/__/__/_|_||_\__, |           │
# │               |_|                                         |___/            │
# ╰────────────────────────────────────────────────────────────────────────────╯

def gen_script( config:dict ):
    match config['script_language']:
        case 'python':
            return python_process_script( config )

def python_process_script( config:dict ):
    config['script'].format( **config )

def python_command() -> list:
    return ['python', '-c']
#[==============================[ msys2 / env ]==============================]

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
"""

def python_command( defs:dict, command:str ) -> list:
    from pathlib import WindowsPath
    mini_script = 'import sys\n'
    mini_script += 'config = {\n'
    for k, v in defs.items():
        if isinstance( v, WindowsPath ):
            mini_script += f'\t{repr(k)}:{repr(str(v))},\n'
            continue
        mini_script += f'\t{repr(k)}:{repr(v)},\n'
    mini_script += '}\n'
    mini_script += f'\nsys.path.append(config["root_dir"])\n'
    mini_script += command
    return ['python', '-c', mini_script]

# TODO
# - msys
# - bash
# - zsh

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
"""
def msys2_clang64( config:dict, command:str ) -> list:
    env_command = ['C:/msys64/msys2_shell.cmd', '-clang64', '-defterm',
                   '-no-start', f'-where {config['project_root']}', '-c' ]
    from pathlib import WindowsPath
    mini_script = 'import sys\n'
    mini_script += 'config = {\n'
    for k, v in config.items():
        if isinstance( v, WindowsPath ):
            mini_script += f'\t{repr(k)}:{repr(str(v))},\n'
            continue
        mini_script += f'\t{repr(k)}:{repr(v)},\n'
    mini_script += '}\n'
    mini_script += f'\nsys.path.append(config["root_dir"])\n'
    mini_script += command
    return ['python', '-c', mini_script]
    return