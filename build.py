#!/usr/bin/env python
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
from share.generate import generate_build_scripts, write_namespace

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
# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _            ___                                                        │
# │   /_\  _ _ __ _| _ \__ _ _ _ ___ ___                                       │
# │  / _ \| '_/ _` |  _/ _` | '_(_-</ -_)                                      │
# │ /_/ \_\_| \__, |_| \__,_|_| /__/\___|                                      │
# │           |___/                                                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
def parse_args(opts:SimpleNamespace) -> SimpleNamespace:
    import argparse

    parser = argparse.ArgumentParser(
        prog="Build-Automation", description="Builds Things", epilog="Build All The Things!!", )

    parser.add_argument( "--debug", action="store_true" ) # dont continue on some failures.
    parser.add_argument( "--dry",action='store_true' )
    parser.add_argument("-j", "--jobs", type=int,
        default=(multiprocessing.cpu_count() - 1) or 1)

    parser_io = parser.add_argument_group( "IO" )
    parser_io.add_argument( "-q", "--quiet", action="store_true" )  # Supress output
    parser_io.add_argument( "-v", "--verbose", action="store_true" )  # extra output
    parser_io.add_argument( "--list", action="store_true" ) # List the configs and quit
    parser_io.add_argument( "--show", action="store_true" ) # Show the configuration and quit

    # Toolchain Options
    toolchain_opts = parser.add_argument_group( "Toolchain" )
    toolchain_opts.add_argument( '-t', "--toolchain-regex", type=str, default='.*' )
    toolchain_opts.add_argument('--toolchain-actions', nargs='+', default=[])

    # Project Options
    project_opts = parser.add_argument_group( "Project Options" )
    project_opts.add_argument('-p', "--project-regex", type=str, default=".*" )
    project_opts.add_argument('--project-actions', nargs='+', default=[])

    # Build Options
    build_opts = parser.add_argument_group( "Build Options" )
    build_opts.add_argument('-b', "--build-regex", type=str, default=".*" )
    build_opts.add_argument( '--build-actions', nargs='+', default=[])

    # Git Overrides
    parser_git = parser.add_argument_group( "Git Overrides" )
    parser_git.add_argument( "--giturl" )  # The Url to clone from
    parser_git.add_argument( "--gitref" )  # the Commit to checkout

    parser.parse_args( namespace=opts )

    setattr(opts, 'toolchain_verbs', set() )
    setattr(opts, 'project_verbs', set() )
    setattr(opts, 'build_verbs', set() )

    # Create gitdef structure
    setattr(opts, 'gitdef', {
        'override': 'yes' if (opts.giturl or opts.gitref) else '',
        'url': opts.giturl or '',
        'ref': opts.gitref or ''
    })
    delattr(opts, 'giturl')
    delattr(opts, 'gitref')
    return opts

# MARK: Import Toolchains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _     _____         _    _         _              │
# │ |_ _|_ __  _ __  ___ _ _| |_  |_   _|__  ___| |__| |_  __ _(_)_ _  ___     │
# │  | || '  \| '_ \/ _ \ '_|  _|   | |/ _ \/ _ \ / _| ' \/ _` | | ' \(_-<     │
# │ |___|_|_|_| .__/\___/_|  \__|   |_|\___/\___/_\__|_||_\__,_|_|_||_/__/     │
# ╰───────────┤_├──────────────────────────────────────────────────────────────╯
def import_toolchains( opts:SimpleNamespace ) -> dict:
    t3( f"Importing Toolchains" )
    toolchain_glob = f"*/toolchains.py"
    h( f"file glob: {toolchain_glob}" )

    # Import toolchain modules.
    toolchains: dict[str,SimpleNamespace] = {}
    for file in opts.path.glob( toolchain_glob ):
        if opts.verbose: h(file)

        # Create Module Spec
        spec = importlib.util.spec_from_file_location(
            name=os.path.basename( file.parent ),
            location=file )

        # import module
        toolchain_module = importlib.util.module_from_spec( spec )

        # Execute the module
        try:
            spec.loader.exec_module( toolchain_module )
        except Exception as e:
            if opts.debug: raise e
            else:
                hu(str(e))
                continue

        # generate the project configurations
        try: toolchains |= toolchain_module.generate( opts )
        except Exception as e:
            if opts.debug: raise e
            else: hu( f'[red]{e}')

    # Filter the results with the toolchain-regex
    toolchains = {k: v for k, v in toolchains.items() if re.search( opts.toolchain_regex, v.name )}

    # Fetch all the verbs from the toolchain for displaying help
    for toolchain in toolchains.values():
        setattrdefault(toolchain, 'verbs', set())
        # collect toolchain verbs to display
        for verb in toolchain.verbs:
            opts.toolchain_verbs.add(verb)

    return toolchains

# MARK: Import Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _      ___           __ _                         │
# │ |_ _|_ __  _ __  ___ _ _| |_   / __|___ _ _  / _(_)__ _ ___                │
# │  | || '  \| '_ \/ _ \ '_|  _| | (__/ _ \ ' \|  _| / _` (_-<                │
# │ |___|_|_|_| .__/\___/_|  \__|  \___\___/_||_|_| |_\__, /__/                │
# ╰───────────┤_├─────────────────────────────────────┤___/────────────────────╯
def import_projects(opts:SimpleNamespace) -> dict:
    t3( f"Importing Projects" )
    project_glob = f"*/config.py"
    h1( f"file glob: {project_glob}" )

    # Import project_config files.
    projects: dict[str,SimpleNamespace] = {}
    hu()
    for config_file in opts.path.glob( project_glob ):
        if opts.verbose: h(config_file)

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
                hu( f'In {spec.name} [red]{e}')
                continue

        # generate the project configurations
        try: projects |= project_module.generate( opts )
        except Exception as e:
            if opts.debug: raise e
            else: hu( f'In {spec.name} [red]{e}')

    # Filter the results with the toolchain-regex
    projects = {k: v for k, v in projects.items() if re.search( opts.project_regex, v.name )}

    # Verify and filter the build configurations
    # projects without build configurations will be filtered out.
    for project in projects.values():
        # All project configs must have a valid gitdef with a URL
        if not getattr(project, 'gitdef', {} ).get('url', None):
            hu("[red]project is missing gitdef['url']")
            projects.build_configs = {}
            continue

        # match --filter <regex>
        builds: dict = project.build_configs
        project.build_configs = {k: v for k, v in builds.items() if re.search( opts.build_regex, v.name )}

    # Cull projects after filtering build configurations
    projects = {v.name: v for v in projects.values() if len( v.build_configs )}

    # Fetch all the verbs from the project and build for displaying help
    for project in projects.values():
        setattrdefault(project, 'verbs', {'fetch'} )
        # collect toolchain verbs to display
        for verb in project.verbs:
            opts.project_verbs.add(verb)

        for build in project.build_configs.values():
            setattrdefault(build, 'verbs', {} )
            # collect toolchain verbs to display
            for verb in build.verbs:
                opts.build_verbs.add(verb)

    return projects

# MARK: Update Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _   _          _      _          ___           __ _                       │
# │ | | | |_ __  __| |__ _| |_ ___   / __|___ _ _  / _(_)__ _ ___              │
# │ | |_| | '_ \/ _` / _` |  _/ -_) | (__/ _ \ ' \|  _| / _` (_-<              │
# │  \___/| .__/\__,_\__,_|\__\___|  \___\___/_||_|_| |_\__, /__/              │
# ╰───────┤_├───────────────────────────────────────────|___/──────────────────╯
def update_configs( opts:SimpleNamespace ):
    projects = opts.projects
    t3('Updating Configs')
    issues:str = ''

    # Update all the project configurations
    for name, project in projects.items():
        setattr(project, 'name', name )
        setattr(project, 'opts', opts )
        setattr(project, 'path', opts.path / project.name )
        project.gitdef['remote'] = 'origin'
        project.gitdef['gitdir'] = project.path / 'git'

        # Update all the build configurations
        for build in project.build_configs.values():
            setattr( build, 'project', project )

            setattr( build, 'script_path', project.path / f"{build.name}.py" )

            setattrdefault(build, 'gitdef', {})
            # build.source_path
            # is the expected full patht to the source of the code
            # if no existing source_dir is set we will use the build name.
            source_path = project.path / getattr( build, 'source_dir', build.name )
            setattrdefault( build, 'source_path', source_path )
            # FIXME, if opts.gitdef['override'] == 'yes', then we need to add the shorthash

    if issues: h("[yellow]Issues Detected")
    else: h("[green]OK")

# MARK: Git Fetch Projects
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _     ___    _      _      ___          _        _                 │
# │  / __(_) |_  | __|__| |_ __| |_   | _ \_ _ ___ (_)___ __| |_ ___           │
# │ | (_ | |  _| | _/ -_)  _/ _| ' \  |  _/ '_/ _ \| / -_) _|  _(_-<           │
# │  \___|_|\__| |_|\___|\__\__|_||_| |_| |_| \___// \___\__|\__/__/           │
# ╰──────────────────────────────────────────────\___/─────────────────────────╯
def fetch_project( opts:SimpleNamespace, project:SimpleNamespace ):
    import git

    if 'fetch' not in project.verbs: return
    t3(project.name)
    g = git.cmd.Git()

    # git ls-remote --symref https://github.com/enetheru/godot-cpp.git HEAD
    # ref: refs/heads/master  HEAD
    # f398ebb8ce61a6ba14cabea77b65136b87f2c24f        HEAD

    # Change to the git directory and instantiate a repo, some commands still
    # assume being inside a git dir.
    os.chdir( project.path )
    project.gitdef['gitdir'] = project.path / "git"

    # Lets clone if we dont exist
    if not project.gitdef['gitdir'].exists():
        hu( 'Cloning' )
        if project['dry']: return
        repo = git.Repo.clone_from( project.gitdef['url'], project.gitdef['gitdir'], progress=print,  bare=True, tags=True )
    else:
        repo = git.Repo( project.gitdef['gitdir'] )

    h("Prune Worktrees")
    repo.git.worktree('prune')

    if opts.verbose:
        h("Worktrees")
        for line in str(repo.git.worktree('list')).splitlines():
            hu(line)

    h("Remotes:")
    for remote in repo.remotes:
        hu(f"{remote.name}: {remote.url}")

    # Keep a dictionary of remote:{refs,} to skip already processed remotes.
    h( "Checking for updates" )
    checked_list = []
    fetch_list = {}
    for config in project.build_configs.values():
        # collate the dictionaries, skipping empty keys
        # Make this a SimpleNamespace so we can use dot referencing
        gitdef:SimpleNamespace = SimpleNamespace(
            **{k:v for k,v in project.gitdef.items() if v}
              | {k:v for k,v in config.gitdef.items() if v}
              | {k:v for k,v in opts.gitdef.items() if v})

        for r in repo.remotes:
            if gitdef.url in r.urls:
                gitdef.remote = r.name
                break

        # Skip remotes we already have already checked.
        if gitdef.remote in checked_list:
            continue

        checked_list.append( gitdef.remote )

        # add the remote to the repo if it doesnt already exist.
        hu()
        if gitdef.remote not in [remote.name for remote in repo.remotes]:
            h('adding remote:')
            hu(gitdef.remote)
            hu(gitdef.url)
            repo.create_remote(gitdef.remote, gitdef.url)


        # Check the remote for updates.
        h( f"git ls-remote {gitdef.url} {gitdef.ref}" )
        ls_ref:str = g.ls_remote( gitdef.url, gitdef.ref )
        if not ls_ref:
            hu(f"[yellow]Unable to determine remote reference.")
            hd()
            continue
        remote_hash = ls_ref.split()[0]

        if gitdef.remote == 'origin':
            local_hash = repo.git.rev_parse(f"{gitdef.ref}")
        else:
            from git import GitCommandError
            try: local_hash = repo.git.rev_parse(f"{gitdef.remote}/{gitdef.ref}")
            except GitCommandError:
                hu(f"Unable to fetch local ref {gitdef.remote}/{gitdef.ref}")
                local_hash = 'missing'

        # Add to the list of repo's to fetch updates from
        if local_hash != remote_hash:
            hu(f"local :{local_hash}")
            hu(f"remote:{remote_hash}")
            hu("local and remote references differ, adding to update list")
            fetch_list[gitdef.remote] = gitdef.ref
        hd()

    if len(fetch_list):
        h( "Fetching updates:" )
        for remote, ref in fetch_list.items():
            fetch_args = ['--verbose', '--progress','--tags', '--force', remote, '*:*']
            hu(f'git fetch {' '.join(fetch_args)}')
            repo.git.fetch( *fetch_args )
    h( "[green]Up-To-Date" )

# MARK: Build
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___      _ _    _                             │
# │ | _ \_ _ ___  __ ___ ______ | _ )_  _(_) |__| |                            │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< | _ \ || | | / _` |                            │
# │ |_| |_| \___/\__\___/__/__/ |___/\_,_|_|_\__,_|                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
def process_build( opts:SimpleNamespace, build:SimpleNamespace ):
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
    section = Section(f"Run Script")
    section.start()
    h( build.script_path.as_posix() )

    if opts.verbose:
        write_namespace( pretendio, build, 'build')

    # ==================[ Print Configuration ]====================-
    from rich.panel import Panel
    from rich.syntax import Syntax

    if opts.show:
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

    script_path = build.script_path.as_posix()

    run_cmd = f'python {script_path}'
    shell_cmd = ' '.join(getattr(build.toolchain, 'shell', []))
    if shell_cmd: run_cmd = shell_cmd + f' "{run_cmd}"'

    try:
        env = getattr(build.toolchain, 'env', None )
        returncode = stream_command( run_cmd, env=env, stdout_handler=test_handler).returncode
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
    print( table )

    section.end()
    console.pop( build.name )

    # ==================[ Output Log Processing ]==================-
    h1( "Post Run Actions" )
    hu( "Clean Log" )
    cleanlog_path = (project.path / f"logs-clean/{build.name}.txt")
    if 'clean_log' in  get_interior_dict(build).keys():
        clean_log = build.clean_log
    else: clean_log = process_log_null

    with (open( log_path, "r", encoding='utf-8' ) as log_raw,
          open( cleanlog_path, "w", encoding='utf-8' ) as log_clean):
        clean_log( log_raw, log_clean )


# MARK: Project
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___          _        _                       │
# │ | _ \_ _ ___  __ ___ ______ | _ \_ _ ___ (_)___ __| |_                     │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< |  _/ '_/ _ \| / -_) _|  _|                    │
# │ |_| |_| \___/\__\___/__/__/ |_| |_| \___// \___\__|\__|                    │
# ╰────────────────────────────────────────\___/───────────────────────────────╯
# TODO Setup a keyboard interrupt to cancel a job and exit the loop, rather than quit the whole script.
def process_project( opts:SimpleNamespace, project:SimpleNamespace ):
    os.chdir( project.path )

    # =====================[ stdout Logging ]======================-
    os.makedirs( project.path / "logs-raw" , exist_ok=True )
    os.makedirs( project.path / "logs-clean", exist_ok=True )

    # Tee stdout to log file.
    log_path = project.path / "logs-raw/{project.name}.txt"
    log_file = open( file=log_path, mode='w', buffering=1, encoding="utf-8" )
    project_console = Console( file=log_file, force_terminal=True )
    console.tee( project_console , project.name )
    s1( f'Process: {project.name}' )

    # ================[ project Heading / Config ]==================-
    if opts.verbose:
        t2( project.name )
        t3("Project Config:")
        write_namespace( pretendio, project, 'project')
        t3("Build Configurations")
        for build in project.build_configs.values():
            h(build.name)

    project_total = len(project.build_configs)
    build_num = 0
    for build in project.build_configs.values():
        build_num += 1
        console.set_window_title( f"{project.name}[{build_num}:{project_total}] - {build.name}" )
        try:
            process_build( opts, build )
        except KeyboardInterrupt:
            print( f'"Cancelling project "{project.name}", CTRL+C again to cancel all projects"')
            try:
                sleep(3)
            except KeyboardInterrupt as e:
                # Cleanup
                console.pop( project.name )
                raise e
            print("continuing")

    send()
    # remove the project output log.
    console.pop( project.name )


# MARK: Statistics
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _        _   _    _   _                                               │
# │ / __| |_ __ _| |_(_)__| |_(_)__ ___                                        │
# │ \__ \  _/ _` |  _| (_-<  _| / _(_-<                                        │
# │ |___/\__\__,_|\__|_/__/\__|_\__/__/                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def show_statistics( opts:SimpleNamespace ):
    table = Table( title="Stats", highlight=True, min_width=80 )

    # unique set of available data names
    column_set:set = set()
    for project in opts.projects.values():
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

    for project in opts.projects.values():
        for build in project.build_configs.values():
            if not 'stats' in build.__dict__: continue

            r:list = ['', f"{project.name}/{build.name}"]
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
                if not sub:
                    r.append( 'n/a' )
                    continue
                if sub.get('status', None) == 'Failed': r.append(f"[red]{sub['duration']}[/red]")
                else: r.append( sub['duration'] )

            table.add_row( *r )
    print( table )

# MARK: Toolchain Actions
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _          _      _   _                      │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _     /_\  __| |_(_)___ _ _  ___         │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \   / _ \/ _|  _| / _ \ ' \(_-<         │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| /_/ \_\__|\__|_\___/_||_/__/         │
# ╰────────────────────────────────────────────────────────────────────────────╯

def process_toolchains( opts:SimpleNamespace ):
    for verb in opts.toolchain_actions:
        for toolchain_name, toolchain in opts.toolchains.items():
            if verb in getattr( toolchain, 'verbs', [] ):
                getattr( toolchain, verb )( toolchain, opts, console )

# MARK: Main
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __      _                                                             │
# │ |  \/  |__ _(_)_ _                                                         │
# │ | |\/| / _` | | ' \                                                        │
# │ |_|  |_\__,_|_|_||_|                                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯
def main():
    console.set_window_title( "AutoBuild" )

    # Create the namespace before parsing, so we can add derived options from the system
    opts = SimpleNamespace(**{
        'command': " ".join( sys.argv ),
        'platform': platform.system(),
        'path': Path( __file__ ).parent,
        'toolchains': {},
        'projects': {}
    })

    # Log everything to a file
    console.tee( Console( file=open( opts.path / "build_log.txt", "w", encoding='utf-8' ), force_terminal=True ),
        name="build_log" )

    parse_args(opts)

    if opts.quiet: console.quiet = True
    t1( "AutoBuild" )

    if opts.verbose:
        t3( "Options" )
        pprint( opts.__dict__, expand_all=True )

    opts.toolchains = toolchains = import_toolchains(opts)
    opts.projects  = projects = import_projects(opts)

    # TODO if help in any of the system verbs then display a list of verb help items.

    # List only.
    if opts.list:
        with Section('List'):
            t3('Toolchains')
            h(f"Available Verbs: {opts.toolchain_verbs or None}")
            h('List:')
            for toolchain_name in toolchains:
                hu(toolchain_name)

            t3('Projects')
            h(f"Available Verbs: {opts.project_verbs or None}")
            h('List:')
            for project_name,project in projects.items():
                hu(project_name)

            t3('Project | Builds')
            h(f"Available Verbs: {opts.build_verbs or None}")
            h('List:')
            for project_name,project in projects.items():
                for build_name in project.build_configs:
                    hu(f'{project_name} | {build_name}')

        quit()

    process_toolchains( opts )

    update_configs( opts )

    if 'fetch' in opts.project_actions:
        with Section( 'Fetching Projects' ):
            for project in projects.values():
                fetch_project( opts, project )

    generate_build_scripts( opts )

    for project in projects.values():
        try: process_project( opts, project )
        except KeyboardInterrupt:
            print("Processing Cancelled")

    show_statistics( opts )

    console.pop( "build_log" )

if __name__ == "__main__":
    main()