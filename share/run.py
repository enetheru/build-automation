import os
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from subprocess import PIPE, CalledProcessError, CompletedProcess, Popen
from rich import print

# https://www.devgem.io/posts/capturing-realtime-output-from-a-subprocess-in-python
# https://stackoverflow.com/questions/54091396/live-output-stream-from-python-subprocess
# https://docs.python.org/3.12/library/shlex.html#shlex.split
def stream_command(
    args,
    *,
    dry=False,
    stdout_handler=print,
    stderr_handler=print,
    check=True,
    text=True,
    stdout=PIPE,
    stderr=PIPE,
    **kwargs,
):
    print(f"""
  CWD: {os.getcwd()}
     $ {args}""")
    if dry: return 0
    """Mimic subprocess.run, while processing the command output in real time."""
    with (
        Popen(args, text=text, stdout=stdout, stderr=stderr, **kwargs, encoding='utf-8') as process,
        ThreadPoolExecutor(2) as pool,  # two threads to handle the (live) streams separately
    ):
        exhaust = partial(deque, maxlen=0)  # collections recipe: exhaust an iterable at C-speed
        exhaust_async = partial(pool.submit, exhaust)  # exhaust non-blocking in a background thread
        exhaust_async(stdout_handler(line.rstrip()) for line in process.stdout)
        exhaust_async(stderr_handler(line.rstrip()) for line in process.stderr)
    retcode = process.poll()  # block until both iterables are exhausted (process finished)
    if check and retcode:
        raise CalledProcessError(
            retcode,
            process.args
        )
    return CompletedProcess( process.args, retcode )