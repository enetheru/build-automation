import os
import shlex
from collections import deque
from typing import cast, BinaryIO, TextIO

from rich import print

from concurrent.futures import ThreadPoolExecutor
from subprocess import PIPE, CalledProcessError, CompletedProcess, Popen
from functools import partial

# https://www.devgem.io/posts/capturing-realtime-output-from-a-subprocess-in-python
# https://stackoverflow.com/questions/54091396/live-output-stream-from-python-subprocess
# https://docs.python.org/3.12/library/shlex.html#shlex.split
def stream_command(
    args,
    *,
    dry=False,
    quiet=False,
    env=None,
    stdout_handler=print,
    stderr_handler=print,
    check=True,
    text=True,
    stdout=PIPE,
    stderr=PIPE,
    **kwargs,
):
    """Mimic subprocess.run, while processing the command output in real time."""

    if not quiet:
        for l in [f'CWD {os.getcwd()}',f'  $ {args}']: print(l)

    if isinstance(args, str): # If the command is a string Split into a list
        args = shlex.split( args )

    if dry: # pretend the command executed successfully
        CompletedProcess( args, 0 )

    with (
        # errors: 'strict', 'replace', 'ignore', 'backslashreplace'
        Popen(args, bufsize=1, stdout=stdout, stderr=stderr, env=env, **kwargs, text=text, encoding='utf-8', errors='backslashreplace') as process,
        ThreadPoolExecutor(2) as pool,  # two threads to handle the (live) streams separately
    ):
        exhaust = partial(deque, maxlen=0)  # collections recipe: exhaust an iterable at C-speed
        exhaust_async = partial(pool.submit, exhaust)  # exhaust non-blocking in a background thread
        # NOTE: The use of cast here is to shit up pycharm warnings which cant discern that the process.stdout/err
        #   can be iterated over, with error: "Expected type 'collections.Iterable', got 'int' instead"
        exhaust_async(stdout_handler(line.rstrip()) for line in cast(TextIO if text else BinaryIO, process.stdout))
        exhaust_async(stderr_handler(line.rstrip()) for line in cast(TextIO if text else BinaryIO, process.stderr))
    retcode = process.poll()  # block until both iterables are exhausted (process finished)
    if check and retcode:
        raise CalledProcessError(
            retcode,
            process.args
        )
    return CompletedProcess( process.args, retcode )
