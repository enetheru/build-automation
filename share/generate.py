# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _      ___                       _   _                 │
# │ / __| __ _ _(_)_ __| |_   / __|___ _ _  ___ _ _ __ _| |_(_)___ _ _         │
# │ \__ \/ _| '_| | '_ \  _| | (_ / -_) ' \/ -_) '_/ _` |  _| / _ \ ' \        │
# │ |___/\__|_| |_| .__/\__|  \___\___|_||_\___|_| \__,_|\__|_\___/_||_|       │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯
import inspect
import json
from json import JSONEncoder
from pathlib import Path
from types import SimpleNamespace
from typing import IO

from share.format import *

class MyEncoder(JSONEncoder):
    def default(self, o):
        if isinstance( o, SimpleNamespace ):
            return "Skipping in case of circular reference."
        if isinstance( o, Path ):
            return os.fspath( o )
        return f"*** CANT JSON DUMP THIS '{type(o).__name__}'"

json.JSONEncoder = MyEncoder

def func_to_string( func ) -> str:
    if func is None: return ''
    lines:list = ['']
    skip = True
    source = inspect.getsource( func )
    for line in source.splitlines():
        if skip:
            skip = '# start_script' not in line
            continue
        lines.append( line[4:] if line.startswith('    ') else line )

    # No '# start_script' was found, so assume to use the whole thing.
    return source if skip else '\n'.join(lines)

def write_namespace( buffer:IO, namespace:SimpleNamespace, name:str, indent=2, level: int = 0) -> None:
    """Convert a SimpleNamespace to a dictionary-like buffer string with indentation."""

    pad = " " * (indent * level)
    inner_pad = pad + " " * indent

    lines = [f"{pad}{name} = {{"]

    skip_keys = []
    skip_keys += getattr(namespace, 'skip_keys', [])

    for key, value in namespace.__dict__.items():
        if key in skip_keys or callable(value): # Skip specified keys and functions
            continue
        qkey = repr(key)

        if isinstance(value, dict): # Pretty print dictionaries
            if not value:
                lines.append(f"{inner_pad}{qkey}:{{}},")
                continue
            if isinstance(next(iter(value.values())), SimpleNamespace): continue
            for line in f'{qkey}:{json.dumps( value, indent=indent )},'.splitlines():
                lines.append(f'{inner_pad}{line}')

        elif isinstance(value, Path): # Handle Path objects
            lines.append(f"{inner_pad}{qkey}:Path({repr(str(value))}),")
        elif isinstance(value, SimpleNamespace): # Skip other SimpleNamespaces
            continue
        elif isinstance(value, str) and '\n' in value: # Skip Multi-Line Scripts.
            continue
        else: # Default case for simple values
            lines.append(f"{inner_pad}{qkey}:{repr(value)},")

    lines.append(f"{pad}}}")
    buffer.write( "\n".join(lines) + '\n' )


def write_preamble(buffer:IO, project: SimpleNamespace):
    buffer.write( "#!/bin/env python\nimport sys\n")
    buffer.write( f"sys.path.append({repr(str(project.opts.path))})\n" )
    with open(f'{Path( __file__ ).parent}/script_preamble.py') as script_imports:
        for line in script_imports.readlines()[1:]: buffer.write( line )
    lines = [
        "sys.stdout.reconfigure(encoding='utf-8')",
        "rich._console = console = Console(soft_wrap=False, width=9000)",
        "stats:dict = {}",
        "config:dict = { 'ok': True }",
    ]
    for line in lines: buffer.write( line )
    buffer.write('\n\n')


def section_heading( title ) -> str:
    line:str = fill("- ", 80)
    line = align("# ", 0 , line )
    return align(f"[ {title} ]", line=line ) + '\n'


def write_section( buffer:IO, section:SimpleNamespace, section_name:str ):
    buffer.write( section_heading(f"Start of {section_name}") )
    write_namespace( buffer, section, section_name )
    buffer.write(f"config['{section_name}'] = {section_name}\n")
    for verb in getattr( section, f'verbs', [] ):
        buffer.write( func_to_string( getattr( section, f'{verb}_script', None ) ) )

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
            with open( build.script_path, "w", encoding='utf-8' ) as script:
                write_preamble( script, project )
                write_section( script, project.opts, 'opts' )
                write_section( script, build.toolchain, 'toolchain' )
                write_section( script, project, 'project' )
                write_section( script, build, 'build' )


