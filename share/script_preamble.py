
import os
import sys
from types import SimpleNamespace

# Machine env GIT_PYTHON_GIT_EXECUTABLE is ssh.exe. GitPython then runs
# `ssh version`, and ssh treats "version" as a hostname.
_git_exec = os.environ.get("GIT_PYTHON_GIT_EXECUTABLE", "")
if _git_exec and os.path.basename(_git_exec).lower() not in {"git", "git.exe", "git.cmd"}:
    del os.environ["GIT_PYTHON_GIT_EXECUTABLE"]

import git

from pathlib import Path

from src import format as fmt
from src.run import stream_command
from src.Timer import Timer, TaskStatus

import rich
from rich.console import Console
from rich.pretty import pprint

from rich.panel import Panel

sys.stdout.reconfigure(encoding='utf-8')
# The parent captures this script through a pipe. Rich then wraps at 79
# columns and folds paths in the middle. A terminal keeps the normal console.
# AUTOBUILD_COLOR means the parent frame will paint ANSI, so this pipe still
# emits color. soft_wrap leaves the wrapping to that frame.
# Auto detection on a Windows pipe selects the legacy console renderer.
# That renderer sets console attributes and writes plain text, so the
# parent frame never receives the color. Standard ANSI and legacy_windows
# off put the codes in the pipe. TERM=dumb would also refuse auto color.
_want_color = (
    os.environ.get('AUTOBUILD_COLOR') == '1'
    and not os.environ.get('NO_COLOR')
    and os.environ.get('CLICOLOR') != '0'
)
if sys.stdout.isatty():
    rich._console = console = Console()
elif _want_color:
    rich._console = console = Console(
        force_terminal=True,
        soft_wrap=True,
        color_system='standard',
        legacy_windows=False,
        no_color=False,
    )
else:
    rich._console = console = Console(color_system=None, soft_wrap=True)
if not sys.stdout.isatty():
    # Captured logs only need the toolchain directory that was prepended.
    # The rest of PATH is the machine and is the same on every build.
    prepend = os.environ.get('AUTOBUILD_PATH_PREPEND', '')
    if prepend:
        print(f'PATH+={prepend}')

stats:dict = {}
config:dict = { 'ok': True }