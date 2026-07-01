import os
import json
from datetime import datetime
from time import sleep
from types import SimpleNamespace
from pathlib import Path
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from share import format as fmt
from share.config import console
from share.run import stream_command
from share.ConsoleMultiplex import TeeOutput
from share.generate import write_namespace
from share.error import handle_error
from src.utils import process_log_null, get_interior_dict

# This is a temporary hack for PretendIO
from io import StringIO
class PretendIO(StringIO):
    def write(self, value):
        print(value)
pretendio = PretendIO()

def process_build( opts:SimpleNamespace, build:SimpleNamespace ):
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
    os.makedirs( project.path / "logs-raw" , exist_ok=True )
    os.makedirs( project.path / "logs-clean", exist_ok=True )
    with (
        open( file=log_path, mode='w', buffering=1, encoding="utf-8" ) as build_log,
        TeeOutput(console, Console( file=build_log, force_terminal=True ), build.name ),
        fmt.Section("Build: " + build.name)
    ):

        # =================[ Build Heading / Config ]==================-
        fmt.h( "Script: " + build.script_path.as_posix() )

        # ==================[ Print Configuration ]====================-

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
        def monitor_output( line ):
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

def process_project( opts:SimpleNamespace, project:SimpleNamespace ):
    os.chdir( project.path )

    # =====================[ stdout Logging ]======================-
    os.makedirs( project.path / "logs-raw" , exist_ok=True )
    os.makedirs( project.path / "logs-clean", exist_ok=True )

    # Tee stdout to log file.
    log_path = project.path / f"logs-raw/{project.name}.log"
    with (
        open( file=log_path, mode='w', buffering=1, encoding="utf-8" ) as log_file,
        TeeOutput(console, Console( file=log_file, force_terminal=True ), project.name ),
        fmt.Section("Project: " + project.name)
    ):
        # ================[ project Heading / Config ]==================-
        if opts.verbose:
            fmt.t2( project.name )
            fmt.t3("Project Config:")
            write_namespace( pretendio, project, 'project')
            fmt.t3("Build Configurations")
            for build in project.build_configs.values():
                fmt.h(build.name)

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
",
    oldText: