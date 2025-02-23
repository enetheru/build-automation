#!/usr/bin/env python
import argparse
import importlib.util
import json
import multiprocessing
import platform
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from subprocess import CalledProcessError
from time import sleep
from types import SimpleNamespace
from typing import IO

import rich
from rich.console import Console
from rich.pretty import pprint
from rich.table import Table

# Local Imports
from share.ConsoleMultiplex import ConsoleMultiplex
from share.format import *
from share.run import stream_command
from share.toolchains import toolchains
from share.generate import generate_build_scripts, write_namespace, MyEncoder


def setattrdefault[T]( namespace:SimpleNamespace, field:str, default:T ) -> T:
    existing = getattr( namespace, field, None )
    if existing: return existing
    setattr(namespace, field, default)
    return default


def get_interior_dict( subject ) -> dict:
    return {k: v for k, v in subject.__dict__.items()}


# noinspection PyUnusedLocal
def process_log_null( raw_file: IO, clean_file: IO ):
    regex = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')

    for line in raw_file:
        clean_file.write( regex.sub('', line ) )


class PretendIO(StringIO):
    def write( self, value ):
        print( value )

pretendio = PretendIO()

# ================[ Setup Multiplexed Console ]================-
sys.stdout.reconfigure(encoding='utf-8')
console = ConsoleMultiplex()
rich._console = console

# MARK: ArgParse
# ====================[ Setup ArgParser ]======================-
parser = argparse.ArgumentParser(
    prog="Build-Automation", description="Builds Things", epilog="Build All The Things!!", )

parser_io = parser.add_argument_group( "IO" )
parser_io.add_argument( "-q", "--quiet", action="store_true" )  # Supress output
parser_io.add_argument( "-v", "--verbose", action="store_true" )  # extra output
parser_io.add_argument( "--list", action="store_true" ) # List the configs and quit
parser_io.add_argument( "--show", action="store_true" ) # Show the configuration and quit
parser_io.add_argument( "--debug", action="store_true" ) # dont continue on some failures.

# General or Global Options
parser_opts = parser.add_argument_group( "Options" )
parser_opts.add_argument( "--dry",action='store_true' )
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

parser_opts.add_argument( "--giturl" )  # The Url to clone from
parser_opts.add_argument( "--gitref" )  # the Commit to checkout

# Create the namespace before parsing, so we can add derived options from the system
opts = SimpleNamespace()
opts.command = " ".join( sys.argv )
opts.platform = platform.system()
opts.path = Path( __file__ ).parent

# ================[ Main Heading and Options ]=================-
def show_heading():
    console.set_window_title( "AutoBuild" )
    h1( "AutoBuild" )
    h3( "Options", newline=False )
    pprint( opts.__dict__, expand_all=True )


# MARK: Toolchain Actions
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _          _      _   _                      │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _     /_\  __| |_(_)___ _ _  ___         │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \   / _ \/ _|  _| / _ \ ' \(_-<         │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| /_/ \_\__|\__|_\___/_||_/__/         │
# ╰────────────────────────────────────────────────────────────────────────────╯
def show_toolchains():
    h3( "Toolchains" )
    for name in toolchains.keys():
        print( "  - ", name )


def process_toolchains():
    for verb in opts.toolchain_actions:
        for toolchain_name, toolchain in toolchains.items():
            if verb in getattr( toolchain, 'verbs', [] ):
                getattr( toolchain, verb )( toolchain, opts, console )


# MARK: Import Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _      ___           __ _                         │
# │ |_ _|_ __  _ __  ___ _ _| |_   / __|___ _ _  / _(_)__ _ ___                │
# │  | || '  \| '_ \/ _ \ '_|  _| | (__/ _ \ ' \|  _| / _` (_-<                │
# │ |___|_|_|_| .__/\___/_|  \__|  \___\___/_||_|_| |_\__, /__/                │
# ╰───────────┤_├─────────────────────────────────────┤___/────────────────────╯
def import_projects() -> dict:
    project_glob = f"{opts.project}/config.py"
    h4( f"Loading Configs from files using glob: {project_glob}" )

    # Import project_config files.
    projects: dict[str,SimpleNamespace] = {}
    for config_file in opts.path.glob( project_glob ):

        # Create Module Spec
        spec = importlib.util.spec_from_file_location(
            name=os.path.basename( config_file.parent ),
            location=config_file )

        # import module
        project_module = importlib.util.module_from_spec( spec )

        # Execute the module
        try:
            spec.loader.exec_module( project_module )
        except Exception as e:
            if opts.debug: raise e
            else:
                print( e )
                continue

        # generate the project configurations
        try:
            projects |= project_module.generate( opts )
        except Exception as e:
            if opts.debug: raise e
            else: print( e )

    # Filter the build configurations using --filter <regex>
    for project in projects.values():
        build_configs: dict = project.build_configs
        project.build_configs = {k: v for k, v in build_configs.items() if re.search( opts.filter, v.name )}

    # Cull projects after filtering build configurations
    projects = {v.name: v for v in projects.values() if len( v.build_configs )}

    # add or update fields for projects and buld configs.
    for name, project in projects.items():
        setattr(project, 'name', name )
        setattr(project, 'opts', opts )
        setattr(project, 'path', opts.path / project.name )
        setattr(project, 'verbs', getattr(project, 'verbs', []) + ['fetch'])
        project.gitdef['remote'] = 'origin'
        for build in project.build_configs.values():
            setattr( build, 'project', project )
            setattrdefault(build, 'gitdef', {})

    return projects


def show_summary( projects:dict ):
    h3( "projects and Configs" )
    if not len( projects ):
        print( "[red]No project/config matches criteria[/red]" )
        exit()

    for project_name, project_config in projects.items():
        build_configs: dict = project_config.build_configs
        print( "  - ", project_name )
        for build in build_configs.values():
            print( "    - ", build.name )


# MARK: Git Fetch Projects
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _     ___    _      _      ___          _        _                 │
# │  / __(_) |_  | __|__| |_ __| |_   | _ \_ _ ___ (_)___ __| |_ ___           │
# │ | (_ | |  _| | _/ -_)  _/ _| ' \  |  _/ '_/ _ \| / -_) _|  _(_-<           │
# │  \___|_|\__| |_|\___|\__\__|_||_| |_| |_| \___// \___\__|\__/__/           │
# ╰──────────────────────────────────────────────\___/─────────────────────────╯
def fetch_projects( projects:dict ):
    import git
    g = git.cmd.Git()

    if 'fetch' not in opts.project_actions:
        return

    h3('Fetching / Updating Projects')

    for project in projects.values():
        if 'fetch' not in project.verbs: continue

        print(f"  == {project.name}" )

        # Change to the git directory and instantiate a repo, some commands still
        # assume being inside a git dir.
        os.chdir( project.path )
        project.gitdef['gitdir'] = project.path / "git"

        # Lets clone if we dont exist
        if not project.gitdef['gitdir'].exists():
            h4( 'Cloning' )
            if project['dry']: continue
            repo = git.Repo.clone_from( project.gitdef['url'], project.gitdef['gitdir'], progress=print,  bare=True, tags=True )
        else:
            repo = git.Repo( project.gitdef['gitdir'] )

        # h4( "Worktrees" )
        repo.git.worktree('prune')
        # for line in str(repo.git.worktree('list')).splitlines():
        #     print( '   ', line)

        # Keep a dictionary of remote:{refs,} to skip already processed remotes.
        h4( "Checking for updates:" )
        fetch_list = {}
        updates: dict[str, set[str]] = {'origin': {project.gitdef['ref']}}
        for config in project.build_configs.values():
            # collate the dictionaries, skipping empty keys
            collect:dict = ({k:v for k,v in project.gitdef.items() if v}
                            | {k:v for k,v in config.gitdef.items() if v}
                            | {k:v for k,v in opts.gitdef.items() if v})


            # FIXME, also unrelated, I have to fix the print to console so that it gets multiplexed
            #   to the logs I broke it by removing from rich import print to fix unicode printing.

            collect['remote'] = config.name
            for r in repo.remotes:
                if collect['url'] in r.urls:
                    collect['remote'] = r.name # FIXME This creates rediculous remote names.
                    break

            # Make this a SimpleNamespace so we can use dot referencing
            gitdef:SimpleNamespace = SimpleNamespace(**collect)

            # add the remote to the repo if it doesnt already exist.
            if gitdef.remote not in [remote.name for remote in repo.remotes]:
                print('adding remote')
                repo.create_remote(gitdef.remote, gitdef.url)

            # get the list of refs from the remote that we have already checked.
            remote_refs = updates.setdefault(gitdef.remote, set() )
            if gitdef.ref in remote_refs: # we've already checked this remote for updates, skip it.
                continue
            else:
                remote_refs.add( gitdef.ref )

            # Check the remote for updates.
            print( f"    git ls-remote {gitdef.url} {gitdef.ref}" )
            ls_ref:str = g.ls_remote( gitdef.url, gitdef.ref )
            if not ls_ref:
                print( f"Unable to fetch remote ref {gitdef.remote}/{gitdef.ref}")
                exit(1)
                # FIXME handle this better.
                #   strip the configurations from the list and continue?
                # Which configurations? I only have a list of remotes.

            remote_hash = ls_ref.split()[0]

            if gitdef.remote == 'origin':
                local_hash = repo.git.rev_parse(f"{gitdef.ref}")
            else:
                from git import GitCommandError
                try:
                    local_hash = repo.git.rev_parse(f"{gitdef.remote}/{gitdef.ref}")
                except GitCommandError as e:
                    print( f"Unable to fetch local ref {gitdef.remote}/{gitdef.ref}")
                    print( e )
                    local_hash = 'missing'

            # Add to the list of repo's to fetch updates from
            if local_hash != remote_hash:
                print( "      local :", local_hash )
                print( "      remote:", remote_hash )
                print( "      local and remote references differ, adding to update list" )
                fetch_list[gitdef.remote] = gitdef.ref

        print("    Remotes:")
        for remote in repo.remotes:
            print(f"      {remote.name}: {remote.url}")

        h4( "Fetching updates:" )
        for remote, ref in fetch_list.items():
            h4(f'Fetching {remote}/{ref}')
            repo.git.fetch( '--verbose', '--progress','--tags', '--force', remote, '*:*' )


# MARK: Update Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _   _          _      _          ___           __ _                       │
# │ | | | |_ __  __| |__ _| |_ ___   / __|___ _ _  / _(_)__ _ ___              │
# │ | |_| | '_ \/ _` / _` |  _/ -_) | (__/ _ \ ' \|  _| / _` (_-<              │
# │  \___/| .__/\__,_\__,_|\__\___|  \___\___/_||_|_| |_\__, /__/              │
# ╰───────┤_├───────────────────────────────────────────|___/──────────────────╯
def update_configs( projects:dict ):
    h3( "Updating Configs" )
    for project in projects.values():
        for build in project.build_configs.values():

            setattr( build, 'script_path', project.path / f"{build.name}.py" )

            # all build configs need a gitdef even if empty
            setattr(build, 'gitdef', getattr(build, 'gitdef', {}))

            script_path = build.script_path.as_posix()
            shell:list = getattr(build.toolchain, 'shell', [])
            if shell: run_cmd = ' '.join(shell + [f'"python {script_path}"'] )
            else: run_cmd = f'python {script_path}'

            setattr( build, 'run_cmd', run_cmd )


# MARK: Build
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___      _ _    _                             │
# │ | _ \_ _ ___  __ ___ ______ | _ )_  _(_) |__| |                            │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< | _ \ || | | / _` |                            │
# │ |_| |_| \___/\__\___/__/__/ |___/\_,_|_|_\__,_|                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
def process_build( build:SimpleNamespace ):
    project = build.project
    # Skip the build config if there are no actions to perform

    skip:bool=True
    for k in opts.build_actions:
        if k in build.verbs:
            skip = False

    if skip:
        # h4( f'No matching build verbs for "{build.name}"')
        # print(f"    available verbs: {build.verbs}")
        build.stats = {"status":'skipped', 'duration':'dnr'}
        return

    # =====================[ stdout Logging ]======================-
    log_path = project.path / f"logs-raw/{build.name}.txt"
    if not skip:
        build_log = open( file=log_path, mode='w', buffering=1, encoding="utf-8" )
        build_console = Console( file=build_log, force_terminal=True )
        console.tee( name=build.name, new_console=build_console )

    # =================[ Build Heading / Config ]==================-
    print( align( f"- Starting: {build.name} -", 0, fill( "=", 120 ) ) )
    newline()

    if opts.show:
        write_namespace( pretendio, build, 'build')

    # ==================[ Print Configuration ]====================-
    from rich.panel import Panel
    from rich.syntax import Syntax

    if opts.verbose:
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
    build.stats = stats = {}
    stats['start_time'] = datetime.now()
    stats['subs'] = subs = {}

    # Out little output handler which captures the lines and looks for data to
    # use in the statistics
    def test_handler( line ):
        if line.startswith('json:'):
            subs.update(json.loads( line[6:] ))
        else:
            print( line )

    try:
        env = getattr(build.toolchain, 'env', None )
        returncode = stream_command( build.run_cmd, env=env, stdout_handler=test_handler).returncode
    except CalledProcessError as e:
        print( e )
        returncode = 1
    except KeyboardInterrupt:
        print("Cancelling current job, CTRL+C to cancel project")
        returncode = 1
        try:
            sleep(3)
        except KeyboardInterrupt as e:
            # Cleanup
            build.stats = {"status":'cancelled', 'duration':'dnr'}
            console.pop( build.name )
            raise e
        print("continuing")
    # TODO create a timeout for the processing, something reasonable.
    #   this should be defined in the build config as the largest possible build time that is expected.
    #   that way it can trigger a check of the system if it is failing this test.

    stats["status"] = "Completed" if not returncode else "Failed"
    stats["end_time"] = datetime.now()
    stats["duration"] = stats["end_time"] - stats["start_time"]

    table = Table( highlight=True, min_width=80, show_header=False )
    table.add_row(
        build.name, f"{stats['status']}", f"{stats['duration']}",
        style="red" if stats["status"] == "Failed" else "green", )
    rich.print( table )

    console.pop( build.name )

    # ==================[ Output Log Processing ]==================-
    h3( "Post Run Actions" )
    h4( "Clean Log" )
    cleanlog_path = (project.path / f"logs-clean/{build.name}.txt")
    if 'clean_log' in  get_interior_dict(build).keys():
        clean_log = build.clean_log
    else: clean_log = process_log_null

    with (open( log_path, "r", encoding='utf-8' ) as log_raw,
          open( cleanlog_path, "w", encoding='utf-8' ) as log_clean):
        clean_log( log_raw, log_clean )

    print( align( f"[ Completed:{build.project.name} / {build.name} ]", line=fill( " -", 120 ) ) )


# MARK: Project
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___          _        _                       │
# │ | _ \_ _ ___  __ ___ ______ | _ \_ _ ___ (_)___ __| |_                     │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< |  _/ '_/ _ \| / -_) _|  _|                    │
# │ |_| |_| \___/\__\___/__/__/ |_| |_| \___// \___\__|\__|                    │
# ╰────────────────────────────────────────\___/───────────────────────────────╯
# TODO Setup a keyboard interrupt to cancel a job and exit the loop, rather than quit the whole script.
def process_projects( projects:dict ):
    for project in projects.values():
        os.chdir( project.path )

        # =====================[ stdout Logging ]======================-
        os.makedirs( project.path / "logs-raw" , exist_ok=True )
        os.makedirs( project.path / "logs-clean", exist_ok=True )

        # Tee stdout to log file.
        log_path = project.path / "logs-raw/{project.name}.txt"
        log_file = open( file=log_path, mode='w', buffering=1, encoding="utf-8" )
        project_console = Console( file=log_file, force_terminal=True )
        console.tee( project_console , project.name )

        # ================[ project Heading / Config ]==================-
        h2( f'Process: {project.name}' )
        print( figlet( project.name, {"font": "standard"} ) )
        write_namespace( pretendio, project, 'project')

        project_total = len(project.build_configs)
        build_num = 0
        for build in project.build_configs.values():
            build_num += 1
            console.set_window_title( f"{project.name}[{build_num}:{project_total}] - {build.name}" )
            try:
                process_build( build )
            except KeyboardInterrupt:
                print( f'"Cancelling project "{project.name}", CTRL+C again to cancel all projects"')
                try:
                    sleep(3)
                except KeyboardInterrupt as e:
                    # Cleanup
                    console.pop( project.name )
                    raise e
                print("continuing")

        print( align( f"[ Completed:{project.name} ]", 0.02, fill( " -" ) ) )
        # remove the project output log.
        console.pop( project.name )


# MARK: Statistics
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _        _   _    _   _                                               │
# │ / __| |_ __ _| |_(_)__| |_(_)__ ___                                        │
# │ \__ \  _/ _` |  _| (_-<  _| / _(_-<                                        │
# │ |___/\__\__,_|\__|_/__/\__|_\__/__/                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def show_statistics( projects:dict ):
    table = Table( title="Stats", highlight=True, min_width=80 )

    # unique set of available data names
    column_set:set = set()
    for project in projects.values():
        for build in project.build_configs.values():
            if not 'stats' in build.__dict__: continue
            if not 'subs' in build.stats: continue
            for key in build.stats['subs'].keys():
                column_set.add(key)

    table.add_column( "Commit" )
    table.add_column( "Project/Config", style="cyan", no_wrap=True )
    table.add_column( "Status" )
    table.add_column( "Total Time" )

    sub_columns:list = []
    for action in opts.build_actions:
        if action in column_set:
            sub_columns.append( action )
            table.add_column( action )

    for project in projects.values():
        for build in project.build_configs.values():
            if not 'stats' in build.__dict__: continue

            r:list = [f"{project.name}/{build.name}"]
            # TODO if gitref is empty when updating the configuration, get latest and update field.
            # r.append(getattr(build, 'gitref', '' )[0:7])

            colour = "green"
            status = build.stats['status']
            if opts.dry:
                colour = "yellow"
                status = "dry-run"
            elif build.stats["status"] == "Failed":
                colour = "red"

            r.append(f"[{colour}]{status}[/{colour}]")

            r.append(str(build.stats['duration'])[:-3])

            subs = build.stats.get('subs', None)
            if not subs: continue
            for column_name in sub_columns:
                sub = subs.get(column_name, None )
                if not sub: continue
                if sub.get('status', None) == 'Failed': r.append(f"[red]{sub['duration']}[/red]")
                else: r.append( sub['duration'] )

            table.add_row( *r )
    rich.print( table )

# MARK: Main
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __      _                                                             │
# │ |  \/  |__ _(_)_ _                                                         │
# │ | |\/| / _` | | ' \                                                        │
# │ |_|  |_\__,_|_|_||_|                                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯
def main():
    # Log everything to a file
    console.tee( Console( file=open( opts.path / "build_log.txt", "w", encoding='utf-8' ), force_terminal=True ), "build_log" )
    print( " build log" )

    # Add all the things from the command line
    parser.parse_args( namespace=opts )

    # Create gitdef structure
    setattr(opts, 'gitdef', {
        'override': 'yes' if (opts.giturl or opts.gitref) else '',
        'url': opts.giturl or '',
        'ref': opts.gitref or ''
    })
    delattr(opts, 'giturl')
    delattr(opts, 'gitref')

    show_heading()
    show_toolchains()
    process_toolchains()
    projects  = import_projects()

    show_summary( projects )

    # TODO if help in any of the system verbs then display a list of verb help items.

    # Remove the project filter attributes from the args as we no longer need them.
    delattr(opts, 'project')
    delattr(opts, 'filter')

    # List only.
    if opts.list: exit()

    fetch_projects( projects )
    print("  OK")

    update_configs( projects )
    print("  OK")

    h3('Generating Build Scripts')
    generate_build_scripts( projects )
    print("  OK")

    try:
        process_projects( projects )
    except KeyboardInterrupt:
        print("Processing Cancelled")

    show_statistics( projects )

    console.pop( "build_log" )

    # Dump last config to json so we can inspect it
    # TypeError: Object of type SimpleNamespace is not JSON serializable
    with open( "last_config_dump.json", 'w' ) as file:
        json.JSONEncoder = MyEncoder
        file.write( json.dumps( projects, indent=2 ) )

if __name__ == "__main__":
    main()