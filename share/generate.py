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
from pathlib import WindowsPath, PosixPath
from types import SimpleNamespace

from share.format import *

def func_as_script( func ) -> str:
    src=inspect.getsource( func ).splitlines()[1:]
    for n in range(len(src)):
        line = src[n]
        if line.startswith('    '):
            src[n] = line[4:]
    return '\n'.join(src)

def namespace_to_script( name:str, namespace:SimpleNamespace, script:StringIO, indent=2 ):
    namespace_to_script.indent += indent
    pad = ' ' * indent
    chunk = [f"{name} = {{"]
    skip_keys = []
    if 'skip_keys' in namespace.__dict__.keys():
        skip_keys = namespace.skip_keys

    for k, v in namespace.__dict__.items():
        if k in skip_keys: continue
        # Skip Functions
        if callable(v): continue
        # Pretty print dictionaries
        if isinstance(v, dict):
            for line in f'{repr(k)}:{json.dumps( v, indent=2 )},'.splitlines():
                chunk.append(f'{pad}{line}')
            continue
        # Fix Windows Path Items
        if isinstance(v, WindowsPath) or isinstance(v, PosixPath):
            chunk.append(f"{pad}{repr(k)}:Path({repr(str(v))}),")
            continue
        # recurse over other namespaces
        if isinstance(v, SimpleNamespace):
            namespace_to_script( k, v, script )
            continue
        # Skip Multi-Line Scripts.
        if type(v) is str and '\n' in v: continue
        chunk.append(f"{pad}{repr(k)}:{repr(v)},")
    chunk.append("}\n")
    script.write( "\n".join(chunk) )
    namespace_to_script.indent -= indent
namespace_to_script.indent = 0


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

def write_toolchain( toolchain:SimpleNamespace, script:StringIO ):
    script.write( centre("[ Start Of Toolchain ]", left("\n#", fill("- ", 80))) )
    script.write('\n')

    toolchain_script =  getattr( toolchain, 'script', None )
    if toolchain_script:
        script.write( func_as_script( toolchain_script ) )
    else:
        script.write( "# No Toolchain additions" )



def write_project( project:SimpleNamespace, script:StringIO ):
    script.write( centre("[ Start Of Project ]", left("\n#", fill("- ", 80))) )
    script.write('\n')

    project_script =  getattr( project, 'script', None )
    if project_script:
        script.write( func_as_script( project_script ) )
    else:
        script.write( "# No Project additions" )



def write_build( build:SimpleNamespace, script:StringIO ):
    script.write( centre("[ Start of Build ]", left("\n#", fill("- ", 80))) )
    script.write('\n')

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
    h4( "Generating Build Scripts" )
    for project in projects.values():
        for build in project.build_configs.values():
            script = StringIO()

            write_preamble( build, script )
            write_toolchain( build.toolchain, script )
            write_project( project, script )
            write_build( build, script )

            with open( build.script_path, "w", encoding='utf-8' ) as file:
                file.write( script.getvalue() )
