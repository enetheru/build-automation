import sys

import git

from pathlib import Path

from share.format import *
from share.run import stream_command
from share.Timer import Timer, TaskStatus

sys.stdout.reconfigure(encoding='utf-8')

import rich
from rich.console import Console
rich._console = console = Console(soft_wrap=False, width=9000)

config:dict = {}
