#!/usr/bin/env python
"""Automated build system for Godot engine, godot-cpp, and dependencies.

This script provides a command-line interface for managing toolchains, fetching project
sources, and running build configurations for Godot-related projects.
"""
from io import StringIO
import rich.box
from rich import print
from rich.pretty import pprint

# Local Imports
from src import format as fmt
from src.config import gopts
from src.generate import generate_build_scripts
from src.build_utils import console, log_console, has_statistics, process_project, show_statistics, process_toolchains
from src.git_utils import git_fetch_project
# Src modules (refactored)
from src.args import parse_args
from src.config_loader import import_toolchains, import_projects

class PretendIO(StringIO):
    """A file-like object that redirects writes to the console."""

    def write( self, value ):
        """Write value by printing it to stdout (pretend file-like behaviour)."""
        print( value )

pretendio = PretendIO()


# Order is the order a person runs them. Text is one line, for the idle list.
VERB_HELP = {
    'fetch': 'pull the latest from all remotes',
    'source': 'check out a source worktree',
    'update': 'update the toolchain',
    'reset': 'delete the CMake cache',
    'configure': 'configure the build',
    'clean': 'remove build outputs',
    'build': 'compile',
    'test': 'run the tests',
    'install': 'install the build products',
}
VERB_ORDER = list(VERB_HELP)


def _verbs(obj) -> list:
    return list(getattr(obj, 'verbs', None) or [])


def print_summary(toolchains, projects, list_configs: bool) -> None:
    """Counts first, then names. --list prints config names under each project."""
    n_configs = sum(len(project.build_configs) for project in projects.values())
    with fmt.Section('Summary'):
        fmt.h(f'Toolchains: {len(toolchains)}')
        fmt.h(f'Projects: {len(projects)}')
        fmt.h(f'Configs: {n_configs}')
        if toolchains:
            with fmt.Section(f'Toolchains ({len(toolchains)})'):
                for toolchain in toolchains.values():
                    fmt.h(toolchain.name)
        if projects:
            with fmt.Section(f'Projects ({len(projects)})'):
                for project in projects.values():
                    n = len(project.build_configs)
                    label = f'{project.name} ({n} configs)'
                    if list_configs and project.build_configs:
                        with fmt.Section(label):
                            for name in sorted(build.name for build in project.build_configs.values()):
                                fmt.h(name)
                    else:
                        fmt.h(label)


def print_available_actions(toolchains, projects) -> None:
    """Unnumbered list of actions. Shown only when the run named none."""
    found = []

    def add(verbs):
        for verb in verbs:
            if verb and verb not in found:
                found.append(verb)

    for toolchain in toolchains.values():
        add(_verbs(toolchain))
    for project in projects.values():
        add(_verbs(project))
        for build in project.build_configs.values():
            add(_verbs(build))
    if not found:
        return

    ordered = [verb for verb in VERB_ORDER if verb in found]
    ordered += [verb for verb in found if verb not in VERB_HELP]
    # Not a Section: this list is only present when nothing ran, so it is not a step.
    print()
    print('Available Actions')
    for verb in ordered:
        text = VERB_HELP.get(verb)
        fmt.h(f'{verb} - {text}' if text else verb, level=2)

# ================[ Setup Multiplexed Console ]================-
# Member 'TextIO' of 'TextIO | Any' does not have attribute 'reconfigure'
# sys.stdout.reconfigure(encoding='utf-8')
# Headings use rich.print. The transcript uses this same console.
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
    5. Summarises toolchain and project names. --list also lists each build config name
    6. Runs toolchain actions, fetch, then build configs under Processing
    7. Displays one statistics table when a build recorded a row
    8. Lists available actions, unnumbered, when the run named no actions

    Side effects:
        - Creates/updates log files in project directories
        - Clones/fetches git repositories
        - Executes build scripts via shell commands
        - Modifies console window title
        - Writes build_log.log to the script directory

    Returns:
        None. --list prints each project's build config names in the summary and
        then continues, so a requested fetch or build still runs.

    Raises:
        KeyboardInterrupt: User cancellation propagated from subprocess handlers.
    """
    console.set_window_title( "AutoBuild" )

    # Same plain wide console as the per-build logs. force_terminal wraps at 80.
    log_file = open(gopts.path / "build_log.log", "w", encoding="utf-8")
    console.tee(log_console(log_file), name="build_log")

    parse_args(gopts)

    if gopts.quiet: console.quiet = True
    from rich.panel import Panel
    panel = Panel("🚀 AutoBuild", style="bold cyan", expand=False)
    console.print(panel)

    if gopts.verbose:
        console.rule("Options")
        pprint( gopts.__dict__, expand_all=True )

    with fmt.Section('Import'):
        with fmt.Section('Toolchains'):
            import_toolchains(gopts)
            toolchains = gopts.toolchains
            if gopts.verbose:
                for toolchain in toolchains:
                    fmt.h(toolchain)
        with fmt.Section('Projects'):
            gopts.projects = import_projects(gopts)
            projects = gopts.projects
            if gopts.verbose:
                for project in projects:
                    fmt.h(project)

    print_summary(toolchains, projects, gopts.list)

    actions_specified = gopts.toolchain_actions or gopts.project_actions or gopts.build_actions
    if actions_specified:
        with fmt.Section('Processing'):
            toolchain_run = [
                action for action in gopts.toolchain_actions
                if any(action in getattr(toolchain, 'verbs', []) for toolchain in toolchains.values())
            ]
            if toolchain_run:
                process_toolchains(gopts)

            # Fetch updates the bare repo from the in-memory config. Do it
            # before generating scripts, which do not read the new tips.
            if 'fetch' in gopts.project_actions:
                if not projects:
                    fmt.h('No matching configurations, skipping fetch')
                else:
                    for project in projects.values():
                        if 'fetch' not in _verbs(project):
                            continue
                        with fmt.Section(f'{project.name} - fetch'):
                            git_fetch_project(gopts, project)

            if gopts.build_actions:
                if not projects:
                    fmt.h('No matching configurations')
                else:
                    with fmt.Section('Generate Build Scripts'):
                        generate_build_scripts(gopts)
                    for project in projects.values():
                        try: process_project(gopts, project)
                        except KeyboardInterrupt:
                            print('Processing Cancelled')

    if has_statistics(gopts):
        with fmt.Section('Statistics'):
            show_statistics(gopts)

    if not actions_specified:
        print_available_actions(toolchains, projects)

    console.pop( "build_log" )

if __name__ == "__main__":
    main()