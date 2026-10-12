
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
rich._console = console = Console()

print( f'\\nPATH={os.environ['PATH'][:100]} ...' )

stats:dict = {}
config:dict = { 'ok': True }