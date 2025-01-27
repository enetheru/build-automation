import itertools
import math
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import typing

from rich import print

# MARK: FORMAT
###################################- Format -###################################
#                                                                              #
#             ███████  ██████  ██████  ███    ███  █████  ████████             #
#             ██      ██    ██ ██   ██ ████  ████ ██   ██    ██                #
#             █████   ██    ██ ██████  ██ ████ ██ ███████    ██                #
#             ██      ██    ██ ██   ██ ██  ██  ██ ██   ██    ██                #
#             ██       ██████  ██   ██ ██      ██ ██   ██    ██                #
#                                                                              #
################################################################################

# Simplest to read from all the junk surrounding this question.
# # https://stackoverflow.com/a/51268514
# function DisplayInBytes()
# {
#     param(
#         [int]$num
#     )
#     $suffix = "oct", "Kib", "Mib", "Gib", "Tib", "Pib", "Eib", "Zib", "Yib"
#     $index = 0
#     while ($num -gt 1kb)
#     {
#         $num = $num / 1kb
#         $index++
#     }
#
#     $sFmt="{0:N"
#     if ($index -eq 0) {$sFmt += "0"} else {$sFmt += "1"}
#     $sFmt += "} {1}"
#     $sFmt -f $num, $suffix[$index]
# }

try:
    columns:int = os.get_terminal_size().columns
except OSError:
    columns:int = 80

# If we dont have figlet then just replace it with something else
custom_figlet = pathlib.Path("C:/git/cmatsuoka/figlet/figlet.exe")

def figlet(message:str, options:dict=None):
    if options is None: options = {}

    defaults = {
        'columns':columns,
        'align':'l', #l=left, r=right, c=centre
        'font':'standard'
    }
    # other figlet fonts I like are 'standard','Ogre', 'Stronger Than All' and 'ANSI Regular'
    opts = defaults | options

    # figlet_path = shutil.which("figlet")
    figlet_path = shutil.which( custom_figlet )
    args = [figlet_path,
            f'-{opts['align']}',
            '-w', str(opts['columns']),
            '-f', opts['font'],
            f'{message}']

    if figlet_path:
        result = subprocess.run( args, stdout=subprocess.PIPE).stdout.decode('utf-8')
        # When I output text with figlet it inserts a completely useles character as the space.
        # [char] 0x2001  # [MQSP]
        # This might not be a problem in python
        return result
    else:
        return f"==== {message} ===="

# Fill Command
def fill( filler:str=' ', width:int=columns ):
    line:str = filler
    while len(line) < width:
        line += filler
    return line[0:width]

def centre( msg:str='Centre', line:str='' ):
    if not line: line = fill()
    pos:int = math.floor((len(line) - len(msg)) / 2)
    if pos < 0: return msg
    return f'{line[:pos]}{msg}{line[pos+len(msg):]}'


def left( msg:str='Left', line:str='' ):
    if not line: line = fill()
    return f'{msg}{line[len(msg):]}'

def right( msg:str='Right', line:str='' ):
    if not line: line = fill()
    return f'{line[:-len(msg)]}{msg}'

# MARK: HEADING
##################################- Headings -##################################
#                                                                              #
#        ██   ██ ███████  █████  ██████  ██ ███    ██  ██████  ███████         #
#        ██   ██ ██      ██   ██ ██   ██ ██ ████   ██ ██       ██              #
#        ███████ █████   ███████ ██   ██ ██ ██ ██  ██ ██   ███ ███████         #
#        ██   ██ ██      ██   ██ ██   ██ ██ ██  ██ ██ ██    ██      ██         #
#        ██   ██ ███████ ██   ██ ██████  ██ ██   ████  ██████  ███████         #
#                                                                              #
################################################################################

def h1( msg:str = 'heading 1', file:typing.IO=None ):
    title = figlet( msg, {'align':'c','font':'big'} )
    string = os.linesep.join([s for s in title.splitlines() if not re.match( r'^\s*$', s)])

    if file: file.write(string)
    else: print( string )
    return string

def h2(msg:str = 'heading 2', newline=True,file:typing.IO=None):
    string = f'{'\n' if newline else ''}{centre( f'- {msg} -' , fill('='))}'
    if file: file.write(string)
    else: print( string )
    return string

#
def h3(msg:str = 'heading 3', newline=True, file:typing.IO=None):
    string =  f'{'\n' if newline else ''} == {msg} =='
    if file: file.write(string)
    else: print( string )
    return string


def h4(msg:str = 'heading 4', file:typing.IO=None):
    string =  f'  => {msg}'
    if file: file.write(string)
    else: print( string )
    return string

# MARK: COMMAND
##################################- Command -###################################
#                                                                              #
#        ██████  ██████  ███    ███ ███    ███  █████  ███    ██ ██████        #
#       ██      ██    ██ ████  ████ ████  ████ ██   ██ ████   ██ ██   ██       #
#       ██      ██    ██ ██ ████ ██ ██ ████ ██ ███████ ██ ██  ██ ██   ██       #
#       ██      ██    ██ ██  ██  ██ ██  ██  ██ ██   ██ ██  ██ ██ ██   ██       #
#        ██████  ██████  ██      ██ ██      ██ ██   ██ ██   ████ ██████        #
#                                                                              #
################################################################################

# function Format-Command {
#     param(
#         [Parameter( ValueFromRemainingArguments = $true )]$args
#     )
#     Write-Output ""
#     Write-Output "  󰝰:$((get-location).Path)"
#     Write-Output "  󰞷 $args"
# }
#

# https://www.devgem.io/posts/capturing-realtime-output-from-a-subprocess-in-python
# https://stackoverflow.com/questions/54091396/live-output-stream-from-python-subprocess
# https://docs.python.org/3.12/library/shlex.html#shlex.split
def print_eval( command:str,
                dry:bool=False,
                noexcept=False,
                quiet=False,
                output:list=None,
                outerr:list=None) -> int:
    print(f"""
  CWD: {os.getcwd()}
     $ {command}""")
    if dry: return 0

    if not output: output = []
    if not outerr: outerr = []
    proc = subprocess.Popen( shlex.split(command),
                             encoding='utf-8',
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE )
    with proc:
        for (line_out, line_err) in itertools.zip_longest(proc.stdout, proc.stderr, fillvalue=''):
            output.append( line_out )
            outerr.append( line_err )
            if not quiet:
                if line_out: print( line_out.rstrip() )
                if line_err: print(f'[color=red]{line_err.rstrip()}[/color]' )

    if noexcept:
        return proc.returncode
    elif proc.returncode:
        raise subprocess.CalledProcessError(
            returncode=proc.returncode,
            cmd=command,
            output=''.join(output),
            stderr=''.join(outerr))
    else:
        return 0