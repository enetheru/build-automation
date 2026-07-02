"""About page widget for the Build Manager TUI."""

from textual.widgets import Label, Markdown


class AboutWidget(Markdown):
    """Widget displaying application information on the About tab."""

    def compose(self):
        yield Label("Build Manager TUI")
        yield Label("A Textual-based interface for managing toolchains, projects, and builds.")
        yield Label("Author: Samuel Nicholas <nicholas.samuel@gmail.com>")
        yield Label("Project: https://github.com/enetheru/build-automation")
        yield Label("Version: 0.1 | Python 3.8+")
        yield Label("Dependencies: GitPython, pyfiglet, rich, textual")
        yield Label("License: Not specified")
        yield Label("Use regex filters to narrow lists. Press 'q' to quit.")
