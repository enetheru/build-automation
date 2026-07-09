
import os
import sys
from types import SimpleNamespace

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