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
from types import SimpleNamespace
from typing import IO

from share.script_preamble import *

class MyEncoder(JSONEncoder):
    def default(self, o):
        if isinstance( o, SimpleNamespace ):
            return "Skipping in case of circular reference."
        if isinstance( o, Path ):
            return fmt.os.fspath( o )
        return f"*** CANT JSON DUMP THIS '{type(o).__name__}'"

json.JSONEncoder = MyEncoder

def func_to_string( func ) -> str:
    """Convert a function's source code to a string, skipping specified lines.

    Args:
        func (callable): The function to convert.

    Returns:
        str: The function's source code, excluding lines before '# start_script' if present.
    """
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

def write_namespace( buffer:IO, namespace:SimpleNamespace, name:str, indent=2, level: int = 0):
    """Write a SimpleNamespace as a dictionary-like string to a buffer.

    Args:
        buffer (IO): The output buffer to write to.
        namespace (SimpleNamespace): The namespace to serialize.
        name (str): The variable name for the dictionary.
        indent (int, optional): Number of spaces for indentation. Defaults to 2.
        level (int, optional): Current indentation level. Defaults to 0.

    Returns:
        None: Writes the formatted string to the buffer.
    """

    pad = " " * (indent * level)
    inner_pad = pad + " " * indent

    lines = [f"{pad}{name} = {{"]

    skip_keys = ['script_parts']
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
            for line in f'{qkey}:{json.dumps( {k:v for k,v in value.items() if v and k not in ['verbs'] }, indent=indent )},'.splitlines():
                lines.append(f'{inner_pad}{line}')

        elif isinstance(value, Path): # Handle Path objects
            lines.append(f"{inner_pad}{qkey}:Path({repr(str(value))}),")
        elif isinstance(value, SimpleNamespace): # Skip other SimpleNamespaces
            if key in ['project', 'modules', 'toolchain', 'verbs']: continue
            # write_namespace(buffer, value, f"'{key}'", indent, level+1)
            for line in f'{qkey}:{json.dumps( {k:v for k,v in vars(value).items() if v and k not in ['verbs'] }, indent=indent )},'.splitlines():
                lines.append(f'{inner_pad}{line}')
            continue
        elif isinstance(value, str) and '\n' in value: # Skip Multi-Line Scripts.
            continue
        else: # Default case for simple values
            lines.append(f"{inner_pad}{qkey}:{repr(value)},")

    lines.append(f"{pad}}}")
    buffer.write( "\n".join(lines) )


def write_preamble(buffer:IO):
    """Write the script preamble with imports and setup to a buffer.

    Args:
        buffer (IO): The output buffer to write to.

    Returns:
        None: Writes the preamble to the buffer.
    """
    from share.config import gopts
    lines = [
        "#!/bin/env python",
        "import sys",
        f"sys.path.append({repr(str(gopts.path))})"]
    with open(f'{Path( __file__ ).parent}/script_preamble.py') as script_imports:
        for line in script_imports.readlines()[1:]: lines.append( line.rstrip() )
    lines += [
        '',
        "sys.stdout.reconfigure(encoding='utf-8')",
        "rich._console = console = Console(soft_wrap=False, width=9000)",
        '',
        "print( f'\\nPATH={os.environ['path'][:100]} ...' )",
        '',
        "stats:dict = {}",
        "config:dict = { 'ok': True }",
    ]
    # TODO add checking for required modules and bail nicely.
    buffer.write( '\n'.join( lines ) )
    buffer.write('\n\n')


def write_section( buffer:IO, section:SimpleNamespace, section_name:str ):
    """Write a configuration section to a buffer with a formatted header.

    Args:
        buffer (IO): The output buffer to write to.
        section (SimpleNamespace): The section configuration to write.
        section_name (str): The name of the section.

    Returns:
        None: Writes the section with a formatted code box header to the buffer.
    """
    codebox = '\n'.join(fmt.code_box( section_name, width=120 ).splitlines())
    buffer.writelines(['\n',codebox,'\n'])
    write_namespace( buffer, section, section_name )
    buffer.writelines(['\n', f"config['{section_name}'] = {section_name}", '\n'])

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___                       _         ___         _      _                 │
# │  / __|___ _ _  ___ _ _ __ _| |_ ___  / __| __ _ _(_)_ __| |_ ___           │
# │ | (_ / -_) ' \/ -_) '_/ _` |  _/ -_) \__ \/ _| '_| | '_ \  _(_-<           │
# │  \___\___|_||_\___|_| \__,_|\__\___| |___/\__|_| |_| .__/\__/__/           │
# │                                                    |_|                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate_build_scripts( opts:SimpleNamespace ):
    """Generate Python build scripts for each project configuration.

    Args:
        opts (SimpleNamespace): Configuration options with project definitions.

    Returns:
        None: Writes build scripts to disk for each build configuration.
    """
    projects = opts.projects
    fmt.t3('Generating Build Scripts')

    for project in projects.values():
        for build in project.build_configs.values():
            with open( build.script_path, "w", encoding='utf-8' ) as script:
                write_preamble(script)
                write_section( script, opts, 'opts' )
                write_section( script, build.toolchain, 'toolchain' )
                write_section( script, project, 'project' )
                write_section( script, build, 'build' )

                for section in [opts, build.toolchain, project, build]:
                    for part in getattr( section, f'script_parts', [] ):
                        script.write( func_to_string( part ) )

    fmt.h("[green]OK")


