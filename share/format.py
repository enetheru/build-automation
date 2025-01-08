#!/usr/bin/env python3
import math
import os
import pathlib
import shlex
import shutil
import subprocess
import typing

# # Update output buffer size to prevent clipping in Visual Studio output window.
# if( $Host -and $Host.UI -and $Host.UI.RawUI ) {
#     $rawUI = $Host.UI.RawUI
#     #    $bufSize = $rawUI.BufferSize
#     [int]$columns = $rawUI.BufferSize.Width
#     #    $rows = $rawUI.BufferSize.height
#     #    $typeName = $bufSize.GetType( ).FullName
#     #    $newSize = New-Object $typeName (120, $rows)
#     #    $rawUI.BufferSize = $newSize
# } else {
#     [int]$columns = 120
# }

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
    opts = {**defaults,**options}

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


def terminal_title( message ):
    print( f"\033]0;{message}\007" )

def h1(msg:str = 'heading 1', file:typing.IO=None):
    string = figlet( msg, {'align':'c','font':'big'} )
    if file:
        file.write(string)
        return string
    print( string )

def h2(msg:str = 'heading 2', file:typing.IO=None):
    string = f'\n{centre( f'- {msg} -' , fill('='))}\n'
    if file:
        file.write(string)
        return string
    print( string )

#
def h3(msg:str = 'heading 3'):
    print( f'\n == {msg} ==')


def h4(msg:str = 'heading 4'):
    print( f"  => {msg}")

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
def print_eval( command:str, dry:bool=False ):
    print(f"""
  󰝰 {os.getcwd()}
  󰞷 {command}""")
    if dry: return
    with subprocess.Popen( shlex.split(command), stdout=subprocess.PIPE ) as proc:
        for line in proc.stdout:
            print(line.decode('utf8').rstrip())

# function Print-Last-Error {
#     H4 "last exit?     = $LASTEXITCODE"
#     H4 "auto var `$?   = $?"
#     H4 "Error?         = $Error"
# }

# MARK: AGGREGATE
##################################- Aggregate -#################################
#                                                                              #
#  █████   ██████   ██████  ██████  ███████  ██████   █████  ████████ ███████  #
# ██   ██ ██       ██       ██   ██ ██      ██       ██   ██    ██    ██       #
# ███████ ██   ███ ██   ███ ██████  █████   ██   ███ ███████    ██    █████    #
# ██   ██ ██    ██ ██    ██ ██   ██ ██      ██    ██ ██   ██    ██    ██       #
# ██   ██  ██████   ██████  ██   ██ ███████  ██████  ██   ██    ██    ███████  #
#                                                                              #
################################################################################
#
# function BigBox {
#     Fill '#' | Center "- $args -"
#     Right '#' | Left ' #'
#     figlet -l -f "ANSI Regular" "$args" | ForEach-Object {
#         Fill | Center $_ | Left ' #' | Right '#'
#     }
#     Right '#' | Left ' #'
#     Fill '#'
# }
#
# function CMakeH1 {
#     $width=80
#     if( ("$args".length % 2) -eq 1 ){
#         $width = 79
#     }
#     Fill '=' $width | Left '#[' | Center "[ $args ]" | Right '] '
# }
