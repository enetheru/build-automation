"""
This module provides functionality to execute system commands while streaming their output in
real time, mimicking the behavior of `subprocess.run`.

The `stream_command` function allows for handling of command output (both stdout and stderr)
with real-time processing, optional simulation (dry runs), and simplified integration with
custom environment variables or output handlers.

References:
- https://www.devgem.io/posts/capturing-realtime-output-from-a-subprocess-in-python
- https://stackoverflow.com/questions/54091396/live-output-stream-from-python-subprocess
- https://docs.python.org/3.12/library/shlex.html#shlex.split
"""
import os
import shlex
import sys
from collections import deque
from typing import cast, BinaryIO, TextIO

from concurrent.futures import ThreadPoolExecutor
from subprocess import PIPE, CalledProcessError, CompletedProcess, Popen
from functools import partial

import rich
from rich.panel import Panel
from rich.text import Text

# The parent closes a command panel when it sees this line.
ENDCMD = '\x1eENDCMD'

def _write_out(line: str) -> None:
    """Write a child stdout line and flush. A pipe is block-buffered, so an
    unflushed compiler diagnostic is gone when the build then raises."""
    sys.stdout.write(line + '\n')
    sys.stdout.flush()

def _end_marker() -> None:
    print(ENDCMD)
    sys.stdout.flush()


def _print_tty_panel(cmd: str, title: str, lines: list[str]) -> None:
    body = cmd if not lines else cmd + '\n' + '\n'.join(lines)
    longest = max([len(cmd), len(title) + 2, *(len(line) for line in lines)], default=0)
    rich.print(Panel(
        Text(body, no_wrap=True, overflow='ignore'),
        title=Text(title, no_wrap=True, overflow='ignore'),
        title_align='left',
        expand=True,
        width=max(80, longest + 4),
        padding=(0, 1),
    ))


def _write_err(line: str) -> None:
    """Keep child stderr on stderr. rich.print would send it to stdout and
    treat square brackets as markup."""
    sys.stderr.write(line + '\n')
    sys.stderr.flush()

# https://www.devgem.io/posts/capturing-realtime-output-from-a-subprocess-in-python
# https://stackoverflow.com/questions/54091396/live-output-stream-from-python-subprocess
# https://docs.python.org/3.12/library/shlex.html#shlex.split
def stream_command(
    args,
    *,
    dry=False,
    quiet=False,
    env=None,
    stdout_handler=_write_out,
    stderr_handler=_write_err,
    check=True,
    text=True,
    stdout=PIPE,
    stderr=PIPE,
    **kwargs,
):
    """Execute a command and stream its output in real time.
    Mimic subprocess.run, while processing the command output in real time.

    Args:
        args (str or list): The command to execute, as a string or list of arguments.
        dry (bool, optional): If True, simulate execution without running the command. Defaults to False.
        quiet (bool, optional): If True, suppress command output. Defaults to False.
        env (dict, optional): Environment variables for the command. Defaults to None.
        stdout_handler (callable, optional): Function to handle stdout lines. Defaults to print.
        stderr_handler (callable, optional): Function to handle stderr lines. Defaults to print.
        check (bool, optional): If True, raise an error on non-zero exit codes. Defaults to True.
        text (bool, optional): If True, treat output as text. Defaults to True.
        stdout (file, optional): Standard output destination. Defaults to subprocess.PIPE.
        stderr (file, optional): Standard error destination. Defaults to subprocess.PIPE.
        **kwargs: Additional arguments for subprocess.Popen.

    Returns:
        CompletedProcess: The result of the command execution.

    Raises:
        CalledProcessError: If check is True and the command exits with a non-zero code.
    """

    shown = args if isinstance(args, str) else str(args)
    cwd = os.getcwd()
    piped = not sys.stdout.isatty()
    # A pipe prints two plain lines and an end marker. The parent puts the
    # command and the lines that follow into one panel. A terminal draws
    # that panel here, after the command, because nothing else is reading.
    if not quiet and piped:
        print(f'CWD {cwd}')
        print(f'  $ {shown}')
        sys.stdout.flush()

    if isinstance(args, str): # If the command is a string Split into a list
        args = shlex.split( args )

    if dry: # pretend the command executed successfully
        if not quiet and not piped:
            _print_tty_panel(shown, cwd, [])
        elif not quiet:
            _end_marker()
        return CompletedProcess( args, 0 )

    tty_panel = not quiet and not piped
    captured: list[str] = []

    def out_handler(line: str) -> None:
        if tty_panel:
            captured.append(line)
            if stdout_handler is not _write_out:
                stdout_handler(line)
            return
        stdout_handler(line)

    def err_handler(line: str) -> None:
        if tty_panel:
            captured.append(line)
            if stderr_handler is not _write_err:
                stderr_handler(line)
            return
        stderr_handler(line)

    try:
        with (
            # errors: 'strict', 'replace', 'ignore', 'backslashreplace'
            Popen(args, bufsize=1, stdout=stdout, stderr=stderr, env=env, **kwargs, text=text, encoding='utf-8', errors='backslashreplace') as process,
            ThreadPoolExecutor(2) as pool,  # two threads to handle the (live) streams separately
        ):
            exhaust = partial(deque, maxlen=0)  # collections recipe: exhaust an iterable at C-speed
            exhaust_async = partial(pool.submit, exhaust)  # exhaust non-blocking in a background thread
            # NOTE: The use of cast here is to shit up pycharm warnings which cant discern that the process.stdout/err
            #   can be iterated over, with error: "Expected type 'collections.Iterable', got 'int' instead"
            exhaust_async(out_handler(line.rstrip()) for line in cast(TextIO if text else BinaryIO, process.stdout))
            exhaust_async(err_handler(line.rstrip()) for line in cast(TextIO if text else BinaryIO, process.stderr))
        retcode = process.poll()  # block until both iterables are exhausted (process finished)
        if check and retcode:
            raise CalledProcessError(
                retcode,
                process.args
            )
        return CompletedProcess( process.args, retcode )
    finally:
        if tty_panel:
            _print_tty_panel(shown, cwd, captured)
        elif not quiet:
            _end_marker()
