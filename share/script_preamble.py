
import os
import sys
from types import SimpleNamespace

import os
os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = r"C:\Program Files\Git\bin\git.exe"
import git

from pathlib import Path



from share import format as fmt
from share.run import stream_command
from share.Timer import Timer, TaskStatus

import rich
from rich.console import Console
from rich.pretty import pprint