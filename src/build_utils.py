#!/usr/bin/env python
"""Build processing utilities: fetch, process builds/projects, stats."""
import json
import os
from datetime import datetime
from time import sleep
from types import SimpleNamespace

from rich import print
from rich.console import Console
from rich.table import Table

from src import format as fmt
from src.ConsoleMultiplex import ConsoleMultiplex, TeeOutput
from src.error import handle_error
from src.generate import write_namespace
from src.run import stream_command
from src.utils import get_interior_dict, process_log_null

console = ConsoleMultiplex()
pretendio = type('obj', (object,), {'write': lambda self, v: print(v)})()




# (fetch_project / git_fetch_project / process_* moved to src/build_utils.py)
# MARK: Build
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___      _ _    _                             │
# │ | _ \_ _ ___  __ ___ ______ | _ )_  _(_) |__| |                            │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< | _ \ || | | / _` |                            │
# │ |_| |_| \___/\__\___/__/__/ |___/\_,_|_|_\__,_|                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
"""Process a single build configuration: generate script, execute actions (source/build/etc.), monitor.

Args:
    opts (SimpleNamespace): Global opts.
    build (SimpleNamespace): Build object.

Side effects:
    Runs pwsh/python script, captures logs/stats.
"""
def process_build( opts:SimpleNamespace, build:SimpleNamespace ):
    """

    :param opts:
    :param build:
    :return:
    """
    project = build.project

    if opts.verbose:
        console.line()
        fmt.t2( f'Process: {build.name}' )
        write_namespace( pretendio, build, 'build')
        write_namespace( pretendio, build.toolchain, 'toolchain')
        write_namespace( pretendio, build.buildtool, 'buildtool')

    setattr( build, 'stats', { # type: ignore[attr-defined]
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
        fmt.Section("Build: " + build.name)
    ):

        # =================[ Build Heading / Config ]==================-
        fmt.h( "Script: " + build.script_path.as_posix() )

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
        # Our little output handler which captures the lines and looks for data to
        # use in the statistics
        def monitor_output( line ):
            """

            :param line:
            """
            if line.startswith('json:'): stats['subs'].update(json.loads( line[6:] ))
            else: print( line )

        errors:list = []
        shell = getattr(build.toolchain, 'shell', [])
        env = getattr(build.toolchain, 'env', None )

        cmd = f'python {build.script_path.as_posix()}'
        run_cmd = ' '.join( shell + [f'"{cmd}"']) if shell else cmd
        fmt.h("RunCmd: " + run_cmd)
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
            end_time = datetime.now()
            stats |= {
                "status": "Failed",
                "end_time": end_time,
                "duration": end_time - stats["start_time"]
            }
            handle_error(f"process_build cmd={run_cmd}", e, opts)
            if errors:
                console.print( Panel( '\n'.join( errors ), title='stderr', style="red"))

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

    with (open(log_path, encoding='utf-8') as log_raw,
          open( cleanlog_path, "w", encoding='utf-8' ) as log_clean):
        clean_log( log_raw, log_clean )


def process_project(opts: SimpleNamespace, project: SimpleNamespace):
    """Process project actions (fetch) and matching builds."""
    os.chdir(project.path)

    os.makedirs(project.path / "logs-raw", exist_ok=True)
    os.makedirs(project.path / "logs-clean", exist_ok=True)

    log_path = project.path / f"logs-raw/{project.name}.log"
    with (
        open(file=log_path, mode='w', buffering=1, encoding="utf-8") as log_file,
        TeeOutput(console, Console(file=log_file, force_terminal=True), project.name),
        fmt.Section("Project: " + project.name)
    ):
        if opts.verbose:
            fmt.t2(project.name)
            fmt.t3("Project Config:")
            write_namespace(pretendio, project, 'project')
            fmt.t3("Build Configurations")
            for build in project.build_configs.values():
                fmt.h(build.name)

        project_total = len(project.build_configs)
        build_num = 0
        for build in project.build_configs.values():
            build_num += 1
            console.set_window_title(f"{project.name}[{build_num}:{project_total}] - {build.name}")
            try:
                process_build(opts, build)
            except KeyboardInterrupt:
                print(f'"Cancelling project "{project.name}", CTRL+C again to cancel all projects"')
                try:
                    from time import sleep
                    sleep(3)
                except KeyboardInterrupt as e:
                    console.pop(project.name)
                    raise e
                print("continuing")



# (show_statistics moved to src/build_utils.py)
def show_statistics( opts:SimpleNamespace ):
    """Display a table summarising build status and durations.

    Args:
        opts (SimpleNamespace): Configuration options containing project and build statistics.

    Returns:
        None: Prints a rich table with build status, duration, and sub-action durations.
    """
    has_stats = any(getattr(build, 'stats', None) is not None for project in opts.projects.values() for build in project.build_configs.values())
    if not has_stats:
        return

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

"""Execute toolchain-specific actions (e.g. 'update') for matching toolchains.

Args:
    opts (SimpleNamespace): Options with toolchain_actions.
"""
def process_toolchains( opts:SimpleNamespace ):
    """Process toolchain-specific actions based on provided options.

    Args:
        opts (SimpleNamespace): Configuration options containing toolchain actions and definitions.

    Returns:
        None: Executes toolchain-specific actions (e.g. update, script) for matching toolchains.
    """
    for verb in opts.toolchain_actions:
        for toolchain_name, toolchain in opts.toolchains.items():
            if verb in getattr( toolchain, 'verbs', [] ):
                getattr( toolchain, verb )( toolchain, opts, console )
