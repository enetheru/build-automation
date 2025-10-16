#!/usr/bin/env python
import importlib.util
import json
import multiprocessing
import os
import sys
from datetime import datetime
from io import StringIO
from time import sleep
from types import SimpleNamespace
from typing import IO

import rich
from rich import print
from rich.console import Console, Group
from rich.pretty import pprint
from rich.table import Table

# Local Imports
from share import format as fmt
from share.ConsoleMultiplex import ConsoleMultiplex, TeeOutput
from share.config import gopts
from share.generate import generate_build_scripts, write_namespace
from share.run import stream_command


def setattrdefault[T]( namespace:SimpleNamespace, field:str, default:T ) -> T:
    existing = getattr( namespace, field, None )
    if existing: return existing
    setattr(namespace, field, default)
    return default


def get_interior_dict( subject ) -> dict:
    return {k: v for k, v in subject.__dict__.items()}


# noinspection PyUnusedLocal
def process_log_null( raw_file: IO, clean_file: IO ):
    regex = fmt.re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')

    for line in raw_file:
        clean_file.write( regex.sub('', line ) )

def git_override( opts:SimpleNamespace):
    """Override Git references for project builds by checking remote repositories.

    Args:
        opts (SimpleNamespace): Configuration options with Git URL and reference overrides.

    Returns:
        None: Updates build configurations with resolved Git references and source paths.

    Raises:
        GitCommandError: If Git operations fail and debug mode is enabled.
    """
    from git import GitCommandError
    import git

    g = git.cmd.Git()

    checked = {}
    for project in opts.projects.values():
        for build in project.build_configs.values():

            gitdef:SimpleNamespace = SimpleNamespace(
                **{k:v for k,v in project.gitdef.items() if v}
                  | {k:v for k,v in build.gitdef.items() if v}
                  | {k:v for k,v in opts.gitdef.items() if v})

            ls_args = [gitdef.url, gitdef.ref]
            ls_arg = ' '.join([gitdef.url, gitdef.ref])
            remote_hash:str = ''
            if ls_arg in checked:
                remote_hash = checked[ls_arg]
            else:
                try:
                    fmt.h( f"git ls-remote {ls_arg}" )
                    response = g.ls_remote( *ls_args )
                    if response: remote_hash = response.split()[0]
                except GitCommandError as e:
                    if opts.debug: raise e
                    fmt.hu(f"[yellow]Unable to determine remote reference.")

            if not remote_hash:
                fmt.hu( f"disabling build: '{build.name}'" )
                build.disabled = True
                continue

            fmt.hu(remote_hash)
            checked[ ls_arg ] = remote_hash
            build.gitdef['override'] = remote_hash
            build.source_dir += f".{remote_hash[:7]}"
            build.source_path = project.path / build.source_dir


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
def parse_args( opts:SimpleNamespace ):
    """Parse command-line arguments for the build system.

    Args:
        opts (SimpleNamespace): Namespace to store parsed arguments and derived options.

    Returns:
        None: Modifies the `opts` namespace in place with parsed arguments.

    Adds options for debug mode, dry run, jobs, verbosity, listing, toolchain/project/build filters, and Git overrides.
    """
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

    parser.add_argument('actions', nargs=argparse.REMAINDER)

    parser.parse_args( namespace=opts )

    if opts.actions:
        opts.toolchain_actions += opts.actions
        opts.project_actions += opts.actions
        opts.build_actions += opts.actions

    setattr(opts, 'toolchain_verbs', [] )
    setattr(opts, 'project_verbs', ['fetch'] )
    setattr(opts, 'build_verbs', [] )

    # Create gitdef structure
    if opts.giturl or opts.gitref: # Overrides specified.
        setattr( opts, 'gitoverride', True)
        setattr(opts, 'gitdef', {
            'override': 'yes',
            'url': opts.giturl or '',
            'ref': opts.gitref or ''
        })
        if 'github' in opts.gitdef['url']:
            opts.gitdef['remote'] = opts.gitdef['url'].split('/')[3]
    else:
        setattr( opts, 'gitoverride', False)
        setattr(opts, 'gitdef', {})

    delattr(opts, 'giturl')
    delattr(opts, 'gitref')

# MARK: Import Toolchains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _     _____         _    _         _              │
# │ |_ _|_ __  _ __  ___ _ _| |_  |_   _|__  ___| |__| |_  __ _(_)_ _  ___     │
# │  | || '  \| '_ \/ _ \ '_|  _|   | |/ _ \/ _ \ / _| ' \/ _` | | ' \(_-<     │
# │ |___|_|_|_| .__/\___/_|  \__|   |_|\___/\___/_\__|_||_\__,_|_|_||_/__/     │
# ╰───────────┤_├──────────────────────────────────────────────────────────────╯
def import_toolchains( opts:SimpleNamespace ):
    toolchain_glob = f"*/toolchains.py"
    fmt.h( f"file glob: {toolchain_glob}" )

    # Import toolchain modules.
    fmt.hu()
    for file in opts.path.glob( toolchain_glob ):

        if opts.verbose: fmt.h(file)

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
                fmt.hu(str(e))
                continue

        # generate the project configurations
        try: opts.toolchains |= toolchain_module.generate( opts )
        except Exception as e:
            if opts.debug: raise e
            else: fmt.hu( f'[red]{e}')
    fmt.hd()

    # Filter the results with the toolchain-regex
    opts.toolchains = {k: v for k, v in opts.toolchains.items() if fmt.re.search( opts.toolchain_regex, k )}

    # Fetch all the verbs from the toolchain for displaying help
    for toolchain in opts.toolchains.values():
        opts.toolchain_verbs += [v for v in toolchain.verbs if v not in opts.toolchain_verbs]


# MARK: Import Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _      ___           __ _                         │
# │ |_ _|_ __  _ __  ___ _ _| |_   / __|___ _ _  / _(_)__ _ ___                │
# │  | || '  \| '_ \/ _ \ '_|  _| | (__/ _ \ ' \|  _| / _` (_-<                │
# │ |___|_|_|_| .__/\___/_|  \__|  \___\___/_||_|_| |_\__, /__/                │
# ╰───────────┤_├─────────────────────────────────────┤___/────────────────────╯
def import_projects( opts:SimpleNamespace ) -> dict:
    dbghelp = '[default]( add --debug for more )'
    project_glob = f"*/config.py"
    fmt.h( f"file glob: {project_glob}" )

    # Import project_config files.
    projects = opts.projects
    for config_file in opts.path.glob( project_glob ):
        # FIXME, I should seprate the usage of the tool from the tool directory.
        if os.path.basename(config_file.parent) == 'share': continue
        fmt.hu(config_file)

        # Create Module Spec
        spec = importlib.util.spec_from_file_location(
            name=os.path.basename( config_file.parent ),
            location=config_file )

        # import module
        project_module = importlib.util.module_from_spec( spec )
        opts.modules[spec.name] = project_module

        # Execute the module
        try:
            spec.loader.exec_module( project_module )
        except Exception as e:
            if opts.debug: raise e
            else:
                fmt.h( f'In {spec.name} [red]{e} {dbghelp}')
                continue

    # Filter the results with the project-regex
    opts.modules = {k: v for k, v in opts.modules.items()
                if fmt.re.search( opts.project_regex, k )}

    fmt.h("generating")
    for k,v in opts.modules.items():
        fmt.hu(f"{k}")
        # generate the project configurations
        try: project : SimpleNamespace = v.generate( opts )
        except Exception as e:
            if opts.debug: raise e
            else: fmt.hu( f'In {k} [red]{e} {dbghelp}')
            continue
        setattr(project, 'name', k)
        projects[k] = project

    # Verify required project attributes
    # filter the build configurations
    for project in projects.values():
        # All project configs must have a valid gitdef with a URL
        sources : dict = getattr(project, 'sources')
        if len(sources) == 0:
            msg = f"{project.name} is missing a source definition"
            if gopts.debug: raise Exception(msg)
            fmt.hu(f"[red]{msg}")

        # match --filter <regex>
        builds: dict = project.build_configs
        project.build_configs = {k: v for k, v in builds.items()
            if fmt.re.search( opts.build_regex, v.name )}

    # filter projects with zero valid build configurations
    projects = {v.name: v for v in projects.values() if len( v.build_configs )}

    # Update project and build fields with information from opts
    for name, project in projects.items():
        project.path = opts.path / project.name

        # project.sourcedir = project.path / 'git'

        # collect project verbs for list display
        setattrdefault(project, 'verbs', ['fetch'] )
        opts.project_verbs += [verb for verb in project.verbs
            if verb not in opts.project_verbs]

        # Update all the build configurations
        for build in project.build_configs.values():
            setattr( build, 'project', project )
            setattr( build, 'script_path', project.path / f"{build.name}.py" )

            # setattrdefault(build, 'gitdef', {})

            # collect build verbs for list display
            opts.build_verbs += [verb for verb in getattr(build, 'verbs', [] )
                if verb not in opts.build_verbs]

            # build.source_path
            # is the expected full path to the source of the code
            # if no existing source_dir is set we will use the build name.
            source_path = project.path / getattr( build, 'source_dir', build.name )
            setattr( build, 'source_path', source_path )
            # FIXME, if opts.gitdef['override'] == 'yes', then we need to add the shorthash

    return projects

# MARK: Git Fetch Projects
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _     ___    _      _      ___          _        _                 │
# │  / __(_) |_  | __|__| |_ __| |_   | _ \_ _ ___ (_)___ __| |_ ___           │
# │ | (_ | |  _| | _/ -_)  _/ _| ' \  |  _/ '_/ _ \| / -_) _|  _(_-<           │
# │  \___|_|\__| |_|\___|\__\__|_||_| |_| |_| \___// \___\__|\__/__/           │
# ╰──────────────────────────────────────────────\___/─────────────────────────╯

def fetch_project( opts:SimpleNamespace, project:SimpleNamespace ):
    fmt.t3(project.name)
    if opts.dry:
        fmt.h("Dry-Run: Skipping Fetch")
        return

    for k,v in project.sources.items():
        match v.type:
            case 'git':
                git_fetch_project( opts, project, k )


def git_fetch_project( opts:SimpleNamespace, project:SimpleNamespace, key : str ):
    import git
    from git import GitCommandError

    g = git.cmd.Git()

    srcdef = project.sources[key]

    # git ls-remote --symref https://github.com/enetheru/godot-cpp.git HEAD
    # ref: refs/heads/master  HEAD
    # f398ebb8ce61a6ba14cabea77b65136b87f2c24f        HEAD

    # Change to the git directory and instantiate a repo, some commands still
    # assume being inside a git dir.
    os.chdir( project.path )

    gitdir = project.path / srcdef.gitdir

    # Lets clone if we dont exist
    if not gitdir.exists():
        fmt.h( 'Cloning Repository' )
        repo = git.Repo.clone_from( srcdef['url'], gitdir, progress=print,  bare=True, tags=True )
    else:
        repo = git.Repo( gitdir )

        fmt.h("Prune Expired Worktrees")
        repo.git.worktree('prune')

        if opts.verbose:
            fmt.h("Worktrees")
            for line in str(repo.git.worktree('list')).splitlines():
                fmt.hu(line)

    fmt.h("Existing Remotes:")
    for remote in repo.remotes:
        fmt.hu(f"{remote.name}: {remote.url}")

    # Keep a dictionary of remote:{refs,} to skip already processed remotes.
    fmt.h( "Looking for Updates" )
    fmt.hu()
    checked_list = []
    fetch_list = {}

    for build in project.build_configs.values():
        # collate the dictionaries, skipping empty keys
        # Make this a SimpleNamespace so we can use dot referencing
        gitdef:SimpleNamespace = SimpleNamespace({**vars(srcdef), **vars(build.srcdef), **vars(opts.srcdef) })

        # We need to check each remote/reference pair to see if we need to update.
        # But since we update all references for any remote, then if the remote is
        # in our list to udpate we can skip it.
        if gitdef.remote in checked_list: continue
        checked_list.append( gitdef.remote )

        # add the remote to the repo if it doesnt already exist.
        if gitdef.remote not in [remote.name for remote in repo.remotes]:
            fmt.h('adding remote:')
            fmt.hu(gitdef.remote)
            fmt.hu(gitdef.url)
            repo.create_remote(gitdef.remote, gitdef.url)
            fetch_list[gitdef.remote] = gitdef.ref
            continue

        # Check the remote for updates.
        try:
            ls_args = ['--exit-code', gitdef.url, gitdef.ref]
            fmt.h( f"git ls-remote {' '.join(ls_args)}" )
            response = g.ls_remote( ls_args )
            if not response:
                fmt.hu( f"git ls-remote returned '{response}'" )
                if opts.gitoverride: exit(1)
                fmt.hu( f"disabling build: '{build.name}'" )
                build.disabled = True
                continue

            remote_hash:str = response.split()[0]
            fmt.hu(remote_hash)
        except GitCommandError as e:
            if opts.debug: raise e
            fmt.hu(f"[yellow]Unable to determine remote reference.")
            # FIXME, I need to disable this configuration if this happens.
            continue

        try:
            cmd_arg = gitdef.ref if gitdef.remote == 'origin' else f"{gitdef.remote}/{gitdef.ref}"
            fmt.h( f"git rev-parse {cmd_arg}" )
            local_hash = repo.git.rev_parse(cmd_arg)
            fmt.hu(local_hash)
        except GitCommandError as e:
            if opts.debug: raise e
            # if the ref doesnt exist it will raise this exception.
            local_hash = None

        # Add to the list of repo's to fetch updates from
        if local_hash != remote_hash:
            fmt.hu('Update Needed')
            fetch_list[gitdef.remote] = gitdef.ref
    fmt.hd()

    if len(fetch_list):
        fmt.h( "Fetching updates:" )
        for remote, ref in fetch_list.items():
            fetch_args = ['--verbose', '--progress','--tags', '--force', remote, '*:*']
            fmt.hu(f'git fetch {' '.join(fetch_args)}')
            repo.git.fetch( *fetch_args )
    fmt.h( "[green]Up-To-Date" )

# MARK: Build
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___      _ _    _                             │
# │ | _ \_ _ ___  __ ___ ______ | _ )_  _(_) |__| |                            │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< | _ \ || | | / _` |                            │
# │ |_| |_| \___/\__\___/__/__/ |___/\_,_|_|_\__,_|                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
def process_build( opts:SimpleNamespace, build:SimpleNamespace ):
    project = build.project

    if opts.verbose:
        console.line()
        fmt.t2( f'Process: {build.name}' )
        write_namespace( pretendio, build, 'build')
        write_namespace( pretendio, build.toolchain, 'toolchain')
        write_namespace( pretendio, build.buildtool, 'buildtool')

    setattr( build, 'stats', {
        'status': "dnf",
        'duration':"dnr",
        'subs':{}
    })
    stats = build.stats

    # Skip the build config if there are no actions to perform
    skip:bool=True
    for k in opts.build_actions:
        if k in build.verbs:
            skip = False

    if skip:
        # h4( f'No matching build verbs for "{build.name}"')
        # print(f"    available : {build.verbs}")
        build.stats |= {"status":'Skipped'}
        return

    if build.disabled:
        build.stats |= {"status":'Disabled'}
        return

    # =====================[ stdout Logging ]======================-
    log_path = project.path / f"logs-raw/{build.name}.log"
    with (
        open( file=log_path, mode='w', buffering=1, encoding="utf-8" ) as build_log,
        TeeOutput(console, Console( file=build_log, force_terminal=True ), build.name ),
        fmt.Section(build.name)
    ):

        # =================[ Build Heading / Config ]==================-
        fmt.h( build.script_path.as_posix() )

        # ==================[ Print Configuration ]====================-
        from rich.panel import Panel
        from rich.syntax import Syntax

        # Show the script.
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
        # Out little output handler which captures the lines and looks for data to
        # use in the statistics
        def monitor_output( line ):
            if line.startswith('json:'): stats['subs'].update(json.loads( line[6:] ))
            else: print( line )

        errors:list = []
        shell = getattr(build.toolchain, 'shell', [])
        env = getattr(build.toolchain, 'env', None )

        cmd = f'python {build.script_path.as_posix()}'
        run_cmd = ' '.join( shell + [f'"{cmd}"']) if shell else cmd
        try:
            stats |= { 'start_time':datetime.now() }
            proc = stream_command( run_cmd, env=env,
                stdout_handler=monitor_output,
                stderr_handler=lambda msg: errors.append(msg)
            )
            print( "Post process")
            end_time = datetime.now()
            stats |= {
                'status': "Dry-Run" if opts.dry else "Completed",
                'end_time': end_time,
                'duration': end_time - stats["start_time"]
            }
            print( "status updated after process")
            proc.check_returncode()
        except KeyboardInterrupt:
            end_time = datetime.now()
            stats |= {
                "status": "Cancelled",
                "end_time": end_time,
                "duration": end_time - stats["start_time"]
            }

            print("Build Cancelled with 'KeyboardInterrupt'")
            console.pop( build.name )

            print("Waiting 3s before continuing, CTRL+C to cancel project")
            try: sleep(3)
            except KeyboardInterrupt as e: raise e
            print("continuing...")
        except Exception as e:
            print( "Exception raised")
            end_time = datetime.now()
            stats |= {
                "status": "Failed",
                "end_time": end_time,
                "duration": end_time - stats["start_time"]
            }
            print( "Status Updated after exception")
            panels = [Panel( str(e), title='Exception', title_align='left' )]
            if errors: panels.append( Panel( '\n'.join( errors ), title='stderr', title_align='left'))

            console.print( Panel( Group(*panels), expand=False, title='Errors', title_align='left', width=120 ) )
            if opts.debug: raise e

        # TODO create a timeout for the processing, something reasonable.
        #   this should be defined in the build config as the largest possible build time that is expected.
        #   that way it can trigger a check of the system if it is failing this test.

        table = Table( highlight=True, min_width=80, show_header=False )
        table.add_row(
            build.name, f"{stats['status']}", f"{stats['duration']}",
            style="red" if stats["status"] == "Failed" else "green", )
        console.print( table )

    # ==================[ Output Log Processing ]==================-
    fmt.h1( "Post Run Actions" )
    fmt.hu( "Clean Log" )
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
    """Process a project by executing its build configurations.

    Args:
        opts (SimpleNamespace): Configuration options for filtering and executing builds.
        project (SimpleNamespace): Project configuration with build configurations.

    Returns:
        None: Executes build scripts for matching configurations and updates statistics.

    Raises:
        KeyboardInterrupt: If the process is interrupted by the user.
    """
    os.chdir( project.path )

    # =====================[ stdout Logging ]======================-
    os.makedirs( project.path / "logs-raw" , exist_ok=True )
    os.makedirs( project.path / "logs-clean", exist_ok=True )

    # Tee stdout to log file.
    log_path = project.path / f"logs-raw/{project.name}.log"
    with (
        open( file=log_path, mode='w', buffering=1, encoding="utf-8" ) as log_file,
        TeeOutput(console, Console( file=log_file, force_terminal=True ), project.name ),
        fmt.Section(project.name)
    ):
        # ================[ project Heading / Config ]==================-
        if opts.verbose:
            fmt.t2( project.name )
            fmt.t3("Project Config:")
            write_namespace( pretendio, project, 'project')
            fmt.t3("Build Configurations")
            for build in project.build_configs.values():
                fmt.h(build.name)
        else:
            print(f"Processing {project.name}")

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


# MARK: Statistics
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ _        _   _    _   _                                               │
# │ / __| |_ __ _| |_(_)__| |_(_)__ ___                                        │
# │ \__ \  _/ _` |  _| (_-<  _| / _(_-<                                        │
# │ |___/\__\__,_|\__|_/__/\__|_\__/__/                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def show_statistics( opts:SimpleNamespace ):
    """Display a table summarizing build status and durations.

    Args:
        opts (SimpleNamespace): Configuration options containing project and build statistics.

    Returns:
        None: Prints a rich table with build status, duration, and sub-action durations.
    """
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
            if not getattr(build, 'stats', None): continue

            # TODO if gitref is empty when updating the configuration, get latest and update field.
            # r:list = [getattr(build, 'gitref', '' )[0:7])
            r:list = ['', f"{project.name}/{build.name}"]

            colour = "green"
            status = build.stats['status']
            match status:
                case 'Completed':
                    colour = "green"
                    pass
                case 'Cancelled' | 'Dry-Run' | 'Skipped', 'Disabled':
                    colour = "yellow"
                case 'Failed':
                    colour = "red"

            r.append(f"[{colour}]{status}[/{colour}]")
            r.append(str(build.stats['duration']))

            subs = build.stats.get('subs', {})
            for column_name in sub_columns:
                sub = subs.get(column_name, None )
                if not sub: r.append( 'n/a' )
                elif sub.get('status', None) == 'Failed':
                    r.append(f"[red]{sub['duration']}[/red]")
                else: r.append( str(sub['duration']) )

            table.add_row( *r )
    console.print(table)

# MARK: Toolchain Actions
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _          _      _   _                      │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _     /_\  __| |_(_)___ _ _  ___         │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \   / _ \/ _|  _| / _ \ ' \(_-<         │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| /_/ \_\__|\__|_\___/_||_/__/         │
# ╰────────────────────────────────────────────────────────────────────────────╯

def process_toolchains( opts:SimpleNamespace ):
    """Process toolchain-specific actions based on provided options.

    Args:
        opts (SimpleNamespace): Configuration options containing toolchain actions and definitions.

    Returns:
        None: Executes toolchain-specific actions (e.g., update, script) for matching toolchains.
    """
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

    # Log everything to a file
    console.tee( Console( file=open( gopts.path / "build_log.log", "w", encoding='utf-8' ), force_terminal=True ),
        name="build_log" )

    parse_args(gopts)

    if gopts.quiet: console.quiet = True
    fmt.t1( "AutoBuild" )

    if gopts.verbose:
        fmt.t3( "Options" )
        pprint( gopts.__dict__, expand_all=True )

    with fmt.Section("Import Toolchains"):
        import_toolchains(gopts)
        toolchains = gopts.toolchains

    with fmt.Section("Import Projects"):
        import_projects(gopts)
        projects = gopts.projects

    if gopts.gitoverride:
        fmt.t3( "Processing Override" )
        git_override(gopts)

    # TODO if help in any of the system verbs then display a list of verb help items.

    # List only.
    if gopts.list:
        with fmt.Section('List Items'):
            with fmt.Section(f"Toolchains ({len(toolchains)})"):
                for toolchain in toolchains.values():
                    verbs:str = ''
                    if len(toolchain.verbs):
                        verbs = f' - available actions:{toolchain.verbs}'
                    fmt.h(f'{toolchain.name}{verbs}')

            n_builds = 0
            with fmt.Section(f"Projects ({len(projects)})"):
                for project_name,project in projects.items():
                    n_builds += len(project.build_configs)
                    verbs:str = ''
                    if len(project.verbs):
                        verbs = f' - available actions:{project.verbs}'
                    fmt.h(f'{project.name}{verbs}')

            with fmt.Section(f"Build Configurations ({n_builds})"):
                fmt.h(f"Available Actions: {gopts.build_verbs or None}")
                for project_name,project in projects.items():
                    for build_name in project.build_configs:
                        fmt.h(f'{project_name} | {build_name}')

    # perform any actions triggered by verbs for toolchains.
    with fmt.Section("Process Toolchain Actions"):
        if len(gopts.toolchain_actions) == 0:
            fmt.h("No toolchain actions specified")
        else:
            process_toolchains( gopts )

    # Basically the same thing again for the fetch command in prject, should be re-arranged
    with fmt.Section("Process Project Actions"):
        if len(gopts.project_actions) == 0:
            fmt.h("No project actions specified")
        else:
            if 'fetch' in gopts.project_actions:
                with fmt.Section( 'Fetching Projects' ):
                    for project in projects.values():
                        fetch_project( gopts, project )

    # Generate the build scripts
    with fmt.Section("Generate Build Scripts"):
        generate_build_scripts( gopts )

    # This one is the processing script for the build itself, should be renamed.something like
    # for build_config in project.configs process_build( build ) since the build has a handle to its parent
    with fmt.Section("Process Builds"):
        if len(gopts.build_actions) == 0:
            fmt.h("No build actions specified")
        else:
            for project in projects.values():
                try: process_project( gopts, project )
                except KeyboardInterrupt:
                    print("Processing Cancelled")

    with fmt.Section("Show Statistics"):
        show_statistics( gopts )

    console.pop( "build_log" )

if __name__ == "__main__":
    main()