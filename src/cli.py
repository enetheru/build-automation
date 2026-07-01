#!/usr/bin/env python
"""CLI argument parsing and setup for the build system."""
import argparse
import multiprocessing
from types import SimpleNamespace

from share.config import gopts, git_base

# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _            ___                                                        │
# │   /_\  _ _ __ _| _ \__ _ _ _ ___ ___                                       │
# │  / _ \| '_/ _` |  _/ _` | '_(_-</ -_)                                      │
# │ /_/ \_\_| \__, |_| \__,_|_| /__/\___|                                      │
# │           |___/                                                            │
# ╰────────────────────────────────────────────────────────────────────────────╯

def parse_args(opts: SimpleNamespace):
    """Parse command-line arguments and populate/modify the param:opts namespace in-place.

    Handles action collection, git overrides, default verbs, and argument groups.

    Args:
        opts: Namespace that will be filled with parsed values.
    """
    parser = argparse.ArgumentParser(
        prog="build",
        description="Automated build system for Godot engine, godot-cpp, and dependencies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
      ./build.ps1 --list                          List available toolchains/projects/builds
      ./build.ps1 fetch                           Fetch all projects
      ./build.ps1 fetch -p "godot-cpp$"           Fetch specific project
      ./build.ps1 build -p godot-cpp -b msvc      Build specific configs
      ./build.ps1 build --giturl https://... --gitref branch""",
    )

    parser.add_argument("--debug", action="store_true", help="Don't continue on some failures")
    parser.add_argument("--dry", action='store_true', help="Dry run mode")
    parser.add_argument("-j", "--jobs", type=int,
                        default=(multiprocessing.cpu_count() - 1) or 1,
                        help=f"Number of parallel jobs (default: {multiprocessing.cpu_count() - 1 or 1})")

    parser_io = parser.add_argument_group("IO")
    parser_io.add_argument("-q", "--quiet", action="store_true", help="Suppress output")
    parser_io.add_argument("-v", "--verbose", action="store_true", help="Extra output")
    parser_io.add_argument("--list", action="store_true", help="List the configs and quit")
    parser_io.add_argument("--show", action="store_true", help="Show the configuration and quit")

    # Toolchain Options
    toolchain_opts = parser.add_argument_group("Toolchain")
    toolchain_opts.add_argument('-t', "--toolchain-regex", type=str, default='.*',
                                help="Regex to filter toolchains (default: match all)")
    toolchain_opts.add_argument('--toolchain-actions', nargs='+', default=[],
                                help="Actions to perform on matching toolchains (e.g. 'update')")

    # Project Options
    project_opts = parser.add_argument_group("Project Options")
    project_opts.add_argument('-p', "--project-regex", type=str, default=".*",
                              help="Regex to filter projects (default: match all)")
    project_opts.add_argument('--project-actions', nargs='+', default=[],
                              help="Actions to perform on matching projects (e.g. 'fetch')")

    # Build Options
    build_opts = parser.add_argument_group("Build Options")
    build_opts.add_argument('-b', "--build-regex", type=str, default=".*",
                            help="Regex to filter build configurations (default: match all)")
    build_opts.add_argument('--build-actions', nargs='+', default=[],
                            help="Actions to perform on matching builds (e.g. 'source', 'configure', 'build', 'clean')")

    # Git Overrides
    parser_git = parser.add_argument_group("Git Overrides")
    parser_git.add_argument("--giturl", help="Override source URL for projects (e.g. https://github.com/user/repo.git)")
    parser_git.add_argument("--gitref", help="Override source ref/branch/commit for projects (e.g. 'main', 'v4.2', SHA)")

    parser.add_argument('actions', nargs=argparse.REMAINDER,
                                help="Fallback actions applied to all (toolchains/projects/builds) if not specified in groups")

    parser.parse_args(namespace=opts)

    if opts.actions:
        opts.toolchain_actions += opts.actions
        opts.project_actions += opts.actions
        opts.build_actions += opts.actions

    setattr(opts, 'toolchain_verbs', [])
    setattr(opts, 'project_verbs', ['fetch'])
    setattr(opts, 'build_verbs', [])

    if getattr(opts, 'giturl', None) or getattr(opts, 'gitref', None):
        srcdef = SimpleNamespace({**vars(git_base), **{
            'remote': 'override',
            'url': opts.giturl or '',
            'ref': opts.gitref or 'HEAD',
        }})
        if opts.giturl and 'github' in opts.giturl:
            srcdef.remote = opts.giturl.split('/')[3]
        opts.sources['override'] = srcdef
        delattr(opts, 'giturl')
        delattr(opts, 'gitref')
