import os
import pathlib
import re
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

def newline():
    print()

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
    while len(line) < width: line += filler
    return line[0:width]

def align(msg:str='align', ratio:float=0.5, line:str=fill() ):
    if len(msg) > len(line): return msg # just return msg if we overwrite everything.
    pos:int = round((len(line) - len(msg)) * ratio)
    if pos < 0: return msg
    return f'{line[:pos]}{msg}{line[pos+len(msg):]}'

# setattr(align, 'left', 0)
# align.right = 0.5
# align.right = 0

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
    from rich.align import Align
    Align.center(f'- {msg} -')
    string = f'{'\n' if newline else ''}{align( f'- {msg} -' , line=fill('='))}'
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