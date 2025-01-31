#!/usr/bin/env python
import argparse
import importlib.util
import multiprocessing
import platform
import sys
from datetime import datetime
from subprocess import CalledProcessError
from typing import IO

import rich
from rich.pretty import pprint
from rich.table import Table

# Local Imports
from share.ConsoleMultiplex import ConsoleMultiplex
from share.actions import fetch_projects
from share.toolchains import *
from share.generate import generate_build_scripts

sys.stdout.reconfigure(encoding='utf-8')


def get_interior_dict( subject ) -> dict:
    return {k: v for k, v in subject.__dict__.items()}


# noinspection PyUnusedLocal
def process_log_null( raw_file: IO, clean_file: IO ):
    regex = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')

    for line in raw_file:
        clean_file.write( regex.sub('', line ) )

# ================[ Setup Multiplexed Console ]================-
console = ConsoleMultiplex()
rich._console = console

# MARK: ArgParse
# ====================[ Setup ArgParser ]======================-
parser = argparse.ArgumentParser(
    prog="Build-Automation", description="Builds Things", epilog="Build All The Things!!", )

parser_io = parser.add_argument_group( "IO" )
parser_io.add_argument( "-q", "--quiet", action="store_true" )  # Supress output
parser_io.add_argument( "-v", "--verbose", action="store_true" )  # extra output

# General or Global Options
parser_opts = parser.add_argument_group( "Options" )
parser_opts.add_argument( "--dry",action='store_true' )
parser_opts.add_argument( "--list", action="store_true" )
parser_opts.add_argument("-j", "--jobs", type=int,
    default=(multiprocessing.cpu_count() - 1) or 1)

# Filter which project/configurations get built.
parser_filter = parser.add_argument_group( "Project Selection" )
parser_filter.add_argument( "--project", default="*" )
parser_filter.add_argument( "--filter", default=".*" )

# Process actions
parser.add_argument('-t', '--toolchain-actions', nargs='+', default=[])
parser.add_argument('-p', '--project-actions', nargs='+', default=[])
parser.add_argument('-b', '--build-actions', nargs='+', default=[])

parser_opts.add_argument( "--gitUrl" )  # The Url to clone from
parser_opts.add_argument( "--gitHash" )  # the Commit to checkout

# Create the namespace before parsing, so we can add derived options from the system
bargs = argparse.Namespace()

bargs.command = " ".join( sys.argv )
bargs.platform = platform.system()
bargs.root_dir = Path( __file__ ).parent

# Log everything to a file
console.tee( Console( file=open( bargs.root_dir / "build_log.txt", "w", encoding='utf-8' ), force_terminal=True ), "build_log" )

# Add all the things from the command line
parser.parse_args( namespace=bargs )

# MARK: Configs
# ==================[ Import Configurations ]==================-
def import_projects() -> dict:
    project_glob = f"{bargs.project}/config.py"
    h4( f"Loading Configs from files using glob: {project_glob}" )

    # Import project_config files.
    config_imports: dict = {}
    project_configs: dict = {}
    for config_file in bargs.root_dir.glob( project_glob ):
        # get the name of the project
        project_name = os.path.basename( config_file.parent )
        # Create Module Spec
        spec = importlib.util.spec_from_file_location( name="config", location=config_file )
        # import module
        config = importlib.util.module_from_spec( spec )
        # load module
        spec.loader.exec_module( config )
        # add to module to import dictionary
        config_imports[project_name] = config
        # Add project to project dictionary
        project = config.project_config
        setattr(project, 'name', project_name )
        project_configs[project_name] = project

    # Filter the configs in the project to match the filter criteria
    for project_name, project_config in project_configs.items():
        build_configs: dict = project_config.build_configs
        project_config.build_configs = {k: v for k, v in build_configs.items() if re.search( bargs.filter, v.name )}

    # keep only projects which have a build config.
    return {k: v for k, v in project_configs.items() if len( v.build_configs )}

projects = import_projects()

# ================[ Main Heading and Options ]=================-
def show_heading():
    console.set_window_title( "AutoBuild" )
    h1( "AutoBuild" )
    h3( "Options", newline=False )
    pprint( bargs.__dict__, expand_all=True )

    h3( "projects and Configs" )
    if not len( projects ):
        print( "[red]No project/config matches criteria[/red]" )
        exit()

    for project_name, project_config in projects.items():
        build_configs: dict = project_config.build_configs
        print( "  - ", project_name )
        for build in build_configs.values():
            print( "    - ", build.name )

show_heading()

# List only.
if bargs.list:
    exit()

# Remove the project filter attributes from the args as we no longer need them.
delattr(bargs, 'project')
delattr(bargs, 'filter')

# MARK: Toolchain Actions
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _          _      _   _                      │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _     /_\  __| |_(_)___ _ _  ___         │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \   / _ \/ _|  _| / _ \ ' \(_-<         │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| /_/ \_\__|\__|_\___/_||_/__/         │
# ╰────────────────────────────────────────────────────────────────────────────╯
def process_toolchains():
    for verb in bargs.toolchain_actions:
        for toolchain_name, toolchain in toolchains.items():
            if verb in getattr( toolchain, 'verbs', [] ):
                getattr( toolchain, verb )( toolchain, bargs, console )

process_toolchains()

# MARK: Update Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _   _          _      _          ___           __ _                       │
# │ | | | |_ __  __| |__ _| |_ ___   / __|___ _ _  / _(_)__ _ ___              │
# │ | |_| | '_ \/ _` / _` |  _/ -_) | (__/ _ \ ' \|  _| / _` (_-<              │
# │  \___/| .__/\__,_\__,_|\__\___|  \___\___/_||_|_| |_\__, /__/              │
# │       |_|                                           |___/                  │
# ╰────────────────────────────────────────────────────────────────────────────╯
def update_configs():
    h4( "Collating Configs" )
    for project in projects.values():
        for k, v in get_interior_dict( bargs ).items():
            if v is None: continue
            if k in ['toolchain_actions', 'project_actions', 'build_actions']: continue
            if getattr( project, k, None ) is None:
                setattr( project, k, v )

        setattr( project, 'actions', copy.deepcopy(bargs.project_actions ))
        setattr( project, 'project_root', project.root_dir / project.name )

        if not getattr(project, 'verbs', False ):
            setattr( project, 'verbs', [] )

        for build in project.build_configs.values():
            for k, v in get_interior_dict( project ).items():
                if v is None: continue
                if k in ["build_configs"]: continue
                if getattr( build, k, None ) is None:
                    setattr( build, k, copy.deepcopy(v) )

            # additional overrides
            # TODO Allow specification of the working tree in the config.
            setattr( build, 'project', project.name )
            setattr( build, 'source_dir', build.project_root / build.name )
            setattr( build, 'script_path', build.project_root / f"{build.name}.py" )
            setattr( build, 'actions', copy.deepcopy(bargs.build_actions ))

            shell = getattr(build.toolchain, 'shell', False)
            if shell: run_cmd = ' '.join(build.toolchain.shell + [f'"python {Path( build.script_path ).as_posix()}"'] )
            else: run_cmd = f'python {Path( build.script_path ).as_posix()}'
            setattr( build, 'run_cmd', run_cmd )

update_configs()
# exit()

# MARK: Generate Scripts
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___                       _         ___         _      _                 │
# │  / __|___ _ _  ___ _ _ __ _| |_ ___  / __| __ _ _(_)_ __| |_ ___           │
# │ | (_ / -_) ' \/ -_) '_/ _` |  _/ -_) \__ \/ _| '_| | '_ \  _(_-<           │
# │  \___\___|_||_\___|_| \__,_|\__\___| |___/\__|_| |_| .__/\__/__/           │
# │                                                    |_|                     │
# ╰────────────────────────────────────────────────────────────────────────────╯
generate_build_scripts( projects )

# MARK: Git Fetch Projects
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _     ___    _      _      ___          _        _                 │
# │  / __(_) |_  | __|__| |_ __| |_   | _ \_ _ ___ (_)___ __| |_ ___           │
# │ | (_ | |  _| | _/ -_)  _/ _| ' \  |  _/ '_/ _ \| / -_) _|  _(_-<           │
# │  \___|_|\__| |_|\___|\__\__|_||_| |_| |_| \___// \___\__|\__/__/           │
# │                                              |__/                          │
# ╰────────────────────────────────────────────────────────────────────────────╯
if 'fetch' in bargs.project_actions:
    fetch_projects( projects )

# MARK: Build
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___      _ _    _                             │
# │ | _ \_ _ ___  __ ___ ______ | _ )_  _(_) |__| |                            │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< | _ \ || | | / _` |                            │
# │ |_| |_| \___/\__\___/__/__/ |___/\_,_|_|_\__,_|                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
def process_build( build:SimpleNamespace ):
    # Skip the build config if there are no actions to perform
    skip:bool=True
    for k in build.actions:
        if k in build.verbs:
            skip = False

    if skip:
        h4( f'No matching build verbs for "{build.name}"')
        build.stats = {"status":'skipped', 'duration':'dnr'}
        return

    console.set_window_title( f"{build.project} - {build.name}" )

    # =====================[ stdout Logging ]======================-
    log_path = build.project_root / f"logs-raw/{build.name}.txt"
    build_log = open( file=log_path, mode='w', buffering=1, encoding="utf-8" )
    build_console = Console( file=build_log, force_terminal=True )
    console.tee( name=build.name, new_console=build_console )

    # =================[ Build Heading / Config ]==================-
    print( centre( f"- Starting: {build.name} -", fill( "=", 120 ) ) )
    print()

    # ==================[ Print Configuration ]====================-
    from rich.panel import Panel
    from rich.syntax import Syntax

    if bargs.verbose:
        with open(build.script_path, "rt") as code_file:
            syntax = Syntax(code_file.read(),
                lexer="python",
                code_width=110,
                line_numbers=True,
                tab_size=2,
                dedent=True,
                word_wrap=True)
        print( Panel( syntax,
            title=str(build.script_path),
            title_align='left',
            expand=False,
            width=120 ) )

    # ====================[ Run Build Script ]=====================-

    stats = {"start_time": datetime.now()}
    build.stats = stats

    try:
        env = getattr(build.toolchain, 'env', None )
        proc = stream_command( build.run_cmd, env=env )
    except CalledProcessError as e:
        # TODO Better execution failure handling
        proc = e
    # TODO The evaluation of the output appears delayed, research a lower latency solution
    # TODO I can watch for print statements here which assign statistics.  #   if line.startswith('scrape_this|'):  #     eval(line.split('|')[1], globals(), locals() )
    # TODO create a timeout for the processing, something reasonable.  #   this should be defined in the build config as the largest possible build time that is expected.  #   that way it can trigger a check of the system if it is failing this test.

    stats["status"] = "Completed" if not proc.returncode else "Failed"
    stats["end_time"] = datetime.now()
    stats["duration"] = stats["end_time"] - stats["start_time"]

    table = Table( highlight=True, min_width=80, show_header=False )
    table.add_row(
        build.name, f"{stats['status']}", f"{stats['duration']}",
        style="red" if stats["status"] == "Failed" else "green", )
    print( table )

    console.pop( build.name )

    # ==================[ Output Log Processing ]==================-
    h3( "Post Run Actions" )
    h4( "Clean Log" )
    cleanlog_path = (build.project_root / f"logs-clean/{build.name}.txt")
    if 'clean_log' in  get_interior_dict(build).keys():
        clean_log = build.clean_log
    else: clean_log = process_log_null

    with (open( log_path, "r", encoding='utf-8' ) as log_raw,
          open( cleanlog_path, "w", encoding='utf-8' ) as log_clean):
        clean_log( log_raw, log_clean )

    print( centre( f"[ Completed:{build.project} / {build.name} ]", fill( " -", 120 ) ) )


# MARK: Project
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___          _        _                       │
# │ | _ \_ _ ___  __ ___ ______ | _ \_ _ ___ (_)___ __| |_                     │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< |  _/ '_/ _ \| / -_) _|  _|                    │
# │ |_| |_| \___/\__\___/__/__/ |_| |_| \___// \___\__|\__|                    │
# │                                        |__/                                │
# ╰────────────────────────────────────────────────────────────────────────────╯
# TODO Setup a keyboard interrupt to cancel a job and exit the loop, rather than quit the whole script.
def process_projects():
    for project in projects.values():
        os.chdir( project.project_root )

        # =====================[ stdout Logging ]======================-
        os.makedirs( project.project_root.joinpath( f"logs-raw" ), exist_ok=True )
        os.makedirs( project.project_root.joinpath( f"logs-clean" ), exist_ok=True )

        # Tee stdout to log file.
        log_path = project.project_root / f"logs-raw/{project.name}.txt"
        log_file = open( file=log_path, mode='w', buffering=1, encoding="utf-8" )
        project_console = Console( file=log_file, force_terminal=True )
        console.tee( project_console , project.name )

        # ================[ project Heading / Config ]==================-
        h2( project.name )
        print( figlet( project.name, {"font": "standard"} ) )

        print( f"  {'options':14s}= ", end='' )
        pprint( { k:v for k,v in project.__dict__.items()
            if k not in ['build_configs']
        }, expand_all=True )
        print( f"  {'build_configs':14s}= ", end='' )
        pprint( [k for k in project.build_configs.keys()], expand_all=True)


        for build in project.build_configs.values():
            process_build( build )

        print( centre( f"[ Completed:{project.name} ]", fill( " -" ) ) )
        # remove the project output log.
        console.pop( project.name )

process_projects()

# MARK: Statistics
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _        _   _    _   _                                               │
# │ / __| |_ __ _| |_(_)__| |_(_)__ ___                                        │
# │ \__ \  _/ _` |  _| (_-<  _| / _(_-<                                        │
# │ |___/\__\__,_|\__|_/__/\__|_\__/__/                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def show_statistics():
    table = Table( title="Stats", highlight=True, min_width=80 )

    table.add_column( "Project/Config", style="cyan", no_wrap=True )
    table.add_column( "Status" )
    table.add_column( "Time" )

    for project in projects.values():
        for build in project.build_configs.values():
            if 'stats' in build.__dict__:
                table.add_row(
                f"{project.name}/{build.name}", f"{build.stats['status']}", f"{build.stats['duration']}",
                style="red" if build.stats["status"] == "Failed" else "green", )

    print( table )

show_statistics()
console.pop( "build_log" )
