from textual.app import App, ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.widgets import Checkbox, Header, Footer, Button, Static, Input
from pathlib import Path
from types import SimpleNamespace
import re

def discover_data():
    toolchains = {}
    projects = {}
    for file in Path(".").glob("*/toolchains.py"):
        toolchains[file.parent.name] = ["default"] 
    for file in Path(".").glob("*/config.py"):
        if file.parent.name != "share":
            projects[file.parent.name] = ["msvc", "gcc", "clang"]
    return toolchains, projects

class BuildApp(App):
    CSS = """
    Grid {
        grid-size: 3;
        grid-gutter: 1;
        padding: 1;
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
            VerticalScroll(Input(placeholder="Filter Toolchains...", id="filter-tc"), id="toolchains-frame", classes="frame"),
            VerticalScroll(Input(placeholder="Filter Projects...", id="filter-proj"), id="projects-frame", classes="frame"),
            VerticalScroll(Input(placeholder="Filter Builds...", id="filter-build"), id="builds-frame", classes="frame"),
        )
        yield Button("Start Build", id="start")
        yield Footer()

    def on_mount(self) -> None:
        self.toolchains, self.projects = discover_data()
        self.populate_lists()

    def populate_lists(self, tc_filter="", proj_filter=""):
        tc_container = self.query_one("#toolchains-frame")
        for tc in self.toolchains:
            if re.search(tc_filter, tc):
                tc_container.mount(Checkbox(tc, name=f"tc:{tc}"))

        proj_container = self.query_one("#projects-frame")
        for proj in self.projects:
            if re.search(proj_filter, proj):
                proj_container.mount(Checkbox(proj, name=f"proj:{proj}"))

    def on_input_changed(self, event: Input.Changed) -> None:
        # Simple regex filtering demonstration
        if event.input.id == "filter-tc":
            # Re-populate toolchains
            pass
        elif event.input.id == "filter-proj":
            pass

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.name.startswith("proj:") and event.value:
            _, projects = discover_data()
            builds_container = self.query_one("#builds-frame")
            proj_name = event.checkbox.name.split(":")[1]
            for build in projects.get(proj_name, []):
                builds_container.mount(Checkbox(f"{proj_name}:{build}", name=f"build:{proj_name}:{build}"))

if __name__ == "__main__":
    app = BuildApp()
    app.run()
