import os.path
import pathlib

# Powershell env command.
def pwsh_command( defs:dict, command:str ) -> list:
    mini_script = ''
    for k, v in defs.items():
        mini_script += f'${k}="{v}"\n'
    mini_script += command
    return ['pwsh', '-Command', mini_script]

def python_command( defs:dict, command:str ) -> list:
    from pathlib import WindowsPath
    mini_script = ''
    for k, v in defs.items():
        if isinstance( v, WindowsPath ):
            mini_script += f'{k}={repr(str(v))}\n'
            continue
        mini_script += f"{k}={repr(v)}\n"
    mini_script += command
    return ['python', '-c', mini_script]

# TODO
# - msys
# - bash
# - zsh