"""
A Textual TUI application for managing toolchains, projects, and builds.

This module defines the `BuildApp` class, an application built with the
textual framework. The application provides an interactive interface to
navigate, filter, and manipulate toolchains, projects, and build options.

It includes three scrollable frames for toolchain, project, and build lists
with filtering capabilities, as well as buttons to initiate builds.

Functions:
    discover_data: Scans the filesystem to gather available toolchains and
                   projects with their supported build configurations.

Classes:
    BuildApp: Represents the main application interface and manages user
              interactions, layout, and dynamic content updates.
"""
import re
from io import StringIO

import rich.box
from rich import print
from textual.app import App, ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.widgets import Header, Footer, Button, Input, Label

# Local Imports
from src.ConsoleMultiplex import ConsoleMultiplex
# Src modules (refactored)
from src.args import parse_args
from src.config import gopts
from src.config_loader import import_toolchains, import_projects


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

class BuildApp(App):
    CSS = """
    Grid {
        grid-size: 2;
        grid-gutter: 0;
        padding: 0;
    }
    .frame {
        border: solid green;
        height: 100%;
        overflow-y: auto;
    }
    """
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            VerticalScroll(
                Input(placeholder="Filter Toolchains...", id="filter-tc"),
                id="toolchains-frame", classes="frame"),
            VerticalScroll(
                Input(placeholder="Filter Projects...", id="filter-proj"),
                id="projects-frame", classes="frame"),
            VerticalScroll(
                Input(placeholder="Filter Builds...", id="filter-build"),
                id="builds-frame", classes="frame"),
        )
        yield Button("Start Build", id="start")
        yield Footer()


    def on_mount(self) -> None:
        parse_args(gopts)
        import_toolchains(gopts)
        import_projects(gopts)
        self.toolchains = gopts.toolchains
        self.projects  = gopts.projects
        self.populate_lists()


    def populate_lists(self, tc_filter="", proj_filter=""):
        tc_container = self.query_one("#toolchains-frame")
        for tc in self.toolchains:
            if re.search(tc_filter, tc):
                tc_container.mount(Label(tc, name=f"tc:{tc}"))

        proj_container = self.query_one("#projects-frame")
        for proj in self.projects:
            if re.search(proj_filter, proj):
                proj_container.mount(Label(proj, name=f"proj:{proj}"))

        build_container = self.query_one("#builds-frame")

        for p in gopts.projects.values():
            for build in p.build_configs:
                if re.search(proj_filter, build):
                    build_container.mount(Label(build, name=f"build:{build}"))


    def on_input_changed(self, event: Input.Changed) -> None:
        # TODO hide or repopulate sections.
        if event.input.id == "filter-tc":
            pass
        elif event.input.id == "filter-proj":
            pass
        elif event.input.id == "filter-build":
            pass

    # TODO Log everything to a file
    # console.tee( Console( file=open( gopts.path / "build_log.log", "w", encoding='utf-8' ), force_terminal=True ),
    #              name="build_log" )

    # TODO if help in any of the system verbs then display a list of verb help items.
    # # List only.
    # if gopts.list:
    #     with fmt.Section('List Items'):
    #         with fmt.Section(f"Toolchains ({len(toolchains)})"):
    #             for toolchain in toolchains.values():
    #                 verbs:str = ''
    #                 if len(toolchain.verbs):
    #                     verbs = f' - available actions:{toolchain.verbs}'
    #                 fmt.h(f'{toolchain.name}{verbs}')
    #
    #         n_builds = 0
    #         with fmt.Section(f"Projects ({len(projects)})"):
    #             for project_name,project in projects.items():
    #                 n_builds += len(project.build_configs)
    #                 verbs:str = ''
    #                 if len(project.verbs):
    #                     verbs = f' - available actions:{project.verbs}'
    #                 fmt.h(f'{project.name}{verbs}')
    #
    #         with fmt.Section(f"Build Configurations ({n_builds})"):
    #             fmt.h(f"Available Actions: {gopts.build_verbs or None}")
    #             for project_name,project in projects.items():
    #                 for build_name in project.build_configs:
    #                     fmt.h(f'{project_name} | {build_name}')
    #
    #     with fmt.Section("Show Statistics"):
    #         show_statistics( gopts )
    #     console.pop( "build_log" )
    #     import sys
    #     sys.exit(0)

    # TODO First level of nesting in the output frame has toolchain level procedures
    # process_toolchains( gopts )

    # TODO First level of nesting int he output frame also has project level procedures
    # TODO Within the project frame a second level of nesting is each for each build.
    # if 'fetch' in gopts.project_actions:
    #     with fmt.Section( 'Fetching Projects' ):
    #         for project in projects.values():
    #             fetch_project( gopts, project )

    # TODO button to begin processing, disabled if there are no action specified
    # TODO output widget

    # generate_build_scripts( gopts )

    # for project in projects.values():
    #     try: process_project( gopts, project )
    #     except KeyboardInterrupt:
    #         print("Processing Cancelled")

    # TODO Statistics TabContent
    # total_builds = sum(len(p.build_configs) for p in gopts.projects.values())
    # show_statistics( gopts )


if __name__ == "__main__":
    app = BuildApp()
    app.run()
