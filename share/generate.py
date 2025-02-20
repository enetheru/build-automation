# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _      ___                       _   _                 │
# │ / __| __ _ _(_)_ __| |_   / __|___ _ _  ___ _ _ __ _| |_(_)___ _ _         │
# │ \__ \/ _| '_| | '_ \  _| | (_ / -_) ' \/ -_) '_/ _` |  _| / _ \ ' \        │
# │ |___/\__|_| |_| .__/\__|  \___\___|_||_\___|_| \__,_|\__|_\___/_||_|       │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯
import inspect
import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from share.format import *

def func_as_script( func ) -> str:
    src=inspect.getsource( func ).splitlines()[1:]
    for n in range(len(src)):
        line = src[n]
        if line.startswith('    '):
            src[n] = line[4:]
    return '\n'.join(src)

def namespace_to_script( name:str, namespace:SimpleNamespace, script:StringIO, indent=2, level: int = 0) -> None:
    """Convert a SimpleNamespace to a dictionary-like script string with indentation."""
    pad = " " * (indent * level)
    inner_pad = pad + " " * indent

    lines = [f"{pad}{name} = {{"]

    skip_keys = getattr(namespace, 'skip_keys', [])

    for key, value in namespace.__dict__.items():
        if key in skip_keys or callable(value): # Skip specified keys and functions
            continue
        qkey = repr(key)

        if isinstance(value, dict): # Pretty print dictionaries
            for line in f'{qkey}:{json.dumps( value, indent=indent )},'.splitlines():
                lines.append(f'{inner_pad}{line}')
        elif isinstance(value, Path): # Handle Path objects
            lines.append(f"{inner_pad}{qkey}:Path({repr(str(value))}),")
        elif isinstance(value, SimpleNamespace): # recurse over other namespaces
            namespace_to_script( key, value, script )
        elif isinstance(value, str) and '\n' in value: # Skip Multi-Line Scripts.
            continue
        else: # Default case for simple values
            lines.append(f"{inner_pad}{qkey}:{repr(value)},")

    lines.append(f"{pad}}}")
    script.write( "\n".join(lines) + '\n' )


def write_preamble(config: SimpleNamespace, script:StringIO):
    script.write( "#!/bin/env python" )
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

def section_heading( title ) -> str:
    line = fill("- ", 80)
    line = align("# ", 0 , line )
    line = align(f"[ {title} ]", line=line )
    return line


def write_toolchain( toolchain:SimpleNamespace, script:StringIO ):
    script.writelines( [section_heading("Start of Toolchain"),'\n'] )

    toolchain_script =  getattr( toolchain, 'script', None )
    if toolchain_script:
        script.write( func_as_script( toolchain_script ) )
    else:
        script.write( "# No Toolchain additions\n" )



def write_project( project:SimpleNamespace, script:StringIO ):
    script.writelines( [section_heading("Start of Project"),'\n'] )

    project_script =  getattr( project, 'script', None )
    if project_script:
        script.write( func_as_script( project_script ) )
    else:
        script.write( "# No Project additions\n" )



def write_build( build:SimpleNamespace, script:StringIO ):
    script.writelines( [section_heading("Start of Build"),'\n'] )
    script.write( func_as_script( build.script ) )

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___                       _         ___         _      _                 │
# │  / __|___ _ _  ___ _ _ __ _| |_ ___  / __| __ _ _(_)_ __| |_ ___           │
# │ | (_ / -_) ' \/ -_) '_/ _` |  _/ -_) \__ \/ _| '_| | '_ \  _(_-<           │
# │  \___\___|_||_\___|_| \__,_|\__\___| |___/\__|_| |_| .__/\__/__/           │
# │                                                    |_|                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate_build_scripts( projects:dict ):
    for project in projects.values():
        for build in project.build_configs.values():
            script = StringIO()

            write_preamble( build, script )
            write_toolchain( build.toolchain, script )
            write_project( project, script )
            write_build( build, script )

            with open( build.script_path, "w", encoding='utf-8' ) as file:
                file.write( script.getvalue() )
