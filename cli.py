#!/usr/bin/env python
"""Automated build system for Godot engine, godot-cpp, and dependencies.

This script provides a command-line interface for managing toolchains, fetching project
sources, and running build configurations for Godot-related projects.
"""
from io import StringIO

import rich.box
from rich import print
from rich.console import Console
from rich.pretty import pprint

# Local Imports
from src import format as fmt
from src.ConsoleMultiplex import ConsoleMultiplex
from src.config import gopts
from src.generate import generate_build_scripts
from src.build_utils import fetch_project, process_project, show_statistics, process_toolchains
# Src modules (refactored)
from src.args import parse_args
from src.config_loader import import_toolchains, import_projects


# (git_override moved to src/git_utils.py)

class PretendIO(StringIO):
    """A file-like object that redirects writes to the console."""

    def write( self, value ):
        """Write value by printing it to stdout (pretend file-like behaviour)."""
        print( value )

pretendio = PretendIO()

# ================[ Setup Multiplexed Console ]================-
# Member 'TextIO' of 'TextIO | Any' does not have attribute 'reconfigure'
# sys.stdout.reconfigure(encoding='utf-8')
console = ConsoleMultiplex()
rich._console = console




# MARK: Main
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __      _                                                             │
# │ |  \/  |__ _(_)_ _                                                         │
# │ | |\/| / _` | | ' \                                                        │
# │ |_|  |_\__,_|_|_||_|                                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯

"""Main entry point: Setup console, parse args, import/generate, process actions, stats."""
def main():
    """Main entry point for the AutoBuild system.

    Orchestrates the complete build automation workflow:
    1. Initialises console logging and window title
    2. Parses command-line arguments into global options
    3. Imports and filters toolchains from */toolchains.py files
    4. Imports and generates project configurations from */config.py files
    5. Displays a summary of available toolchains, projects, and build configurations
    6. Executes toolchain-specific actions (e.g. update)
    7. Fetches project sources via git if the 'fetch' action is specified
    8. Generates and executes build scripts for matching configurations
    9. Displays a statistics table with build status and durations

    Side effects:
        - Creates/updates log files in project directories
        - Clones/fetches git repositories
        - Executes build scripts via shell commands
        - Modifies console window title
        - Writes build_log.log to the script directory

    Returns:
        None: Exits with status 0 if --list flag used, otherwise completes workflow.

    Raises:
        KeyboardInterrupt: User cancellation propagated from subprocess handlers.
    """
    console.set_window_title( "AutoBuild" )

    # Log everything to a file
    console.tee( Console( file=open( gopts.path / "build_log.log", "w", encoding='utf-8' ), force_terminal=True ),
        name="build_log" )

    parse_args(gopts)

    if gopts.quiet: console.quiet = True
    from rich.panel import Panel
    panel = Panel("🚀 AutoBuild", style="bold cyan", expand=False)
    console.print(panel)

    if gopts.verbose:
        fmt.t3( "Options" )
        pprint( gopts.__dict__, expand_all=True )

    with fmt.Section("Import Toolchains"):
        import_toolchains(gopts)
        toolchains = gopts.toolchains
        if gopts.verbose:
            with fmt.Section("Toolchains"):
                for toolchain in toolchains:
                    fmt.h(toolchain)

    with fmt.Section("Import Projects"):
        import_projects(gopts)
        projects = gopts.projects
        if gopts.verbose:
            with fmt.Section("Projects"):
                for project in projects:
                    fmt.h(project)

    total_builds = sum(len(p.build_configs) for p in gopts.projects.values())
    with fmt.Section("Summary"):
        t_verbs = ', '.join(gopts.toolchain_verbs) if gopts.toolchain_verbs else 'none'
        fmt.h(f"Toolchains ({len(gopts.toolchains)}) - available: {t_verbs}")
        p_verbs = ', '.join(gopts.project_verbs) if gopts.project_verbs else 'none'
        b_verbs = ', '.join(gopts.build_verbs) if gopts.build_verbs else 'none'
        fmt.h(f"Projects ({len(gopts.projects)}) ({total_builds} builds)")
        fmt.h(f"  project actions: {p_verbs}")
        fmt.h(f"  build actions: [{b_verbs}]")

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

        with fmt.Section("Show Statistics"):
            show_statistics( gopts )
        console.pop( "build_log" )
        import sys
        sys.exit(0)

    # perform any actions triggered by verbs for toolchains.
    with fmt.Section("Process Toolchain Actions"):
        if len(gopts.toolchain_actions) == 0:
            verbs = ', '.join(gopts.toolchain_verbs) if gopts.toolchain_verbs else 'none'
            fmt.h(f"No toolchain actions specified. Available: [{verbs}]")
        else:
            process_toolchains( gopts )

    # Basically the same thing again for the fetch command in prject, should be re-arranged
    with fmt.Section("Process Project Actions"):
        if len(gopts.project_actions) == 0:
            verbs = ', '.join(gopts.project_verbs) if gopts.project_verbs else 'none'
            fmt.h(f"No project actions specified. Available: [{verbs}]")
        else:
            if 'fetch' in gopts.project_actions:
                with fmt.Section( 'Fetching Projects' ):
                    for project in projects.values():
                        fetch_project( gopts, project )

    # Generate the build scripts
    # This one is the processing script for the build itself, should be renamed.something like
    # for build_config in project.configs process_build( build ) since the build has a handle to its parent
    with fmt.Section("Process Builds"):
        if len(gopts.build_actions) == 0:
            verbs = ', '.join(gopts.build_verbs) if gopts.build_verbs else 'none'
            fmt.h(f"No build actions specified. Available: [{verbs}]")
        else:
            with fmt.Section("Generate Build Scripts"):
                generate_build_scripts( gopts )

            for project in projects.values():
                try: process_project( gopts, project )
                except KeyboardInterrupt:
                    print("Processing Cancelled")

    with fmt.Section("Show Statistics"):
        show_statistics( gopts )

    console.pop( "build_log" )

if __name__ == "__main__":
    main()