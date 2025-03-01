import os
import re
import typing
from textwrap import indent
from typing import Deque

from pyfiglet import Figlet
from pyfiglet import FontNotFound
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

# Padding
class Padding:
    def __init__(self):
        self.padchar = ' '
        self._level = 1
        self.indent = 2
        self.bullets = ['', '--', '*', '-']

    @property
    def level(self):  # Getter
        return self._level
    @level.setter
    def level(self, value):
        self._level = value if value >= 0 else 0

    def str( self ) -> str:
        return self.padchar * self.indent * self.level

    def size( self ) -> int:
        return len( self.str() )
    def sizeu( self ) -> int:
        return len( self.str() ) + self.indent

pad = Padding()

try:
    columns:int = os.get_terminal_size().columns
except OSError:
    columns:int = 80

# Horizontal Rule
def hr( filler:str=' ', width:int=columns ):
    line:str = filler
    while len(line) < width: line += filler
    return line[0:width]


# Align some text within a line
def align(msg:str='align', ratio:float=0.5, line:str=hr() ):
    if len(msg) > len(line): return msg # just return msg if we overwrite everything.
    pos:int = round((len(line) - len(msg)) * ratio)
    if pos < 0: return msg
    return f'{line[:pos]}{msg}{line[pos+len(msg):]}'

def bend( start:str, end:str, line:str=hr()):
    line = align( start, ratio=0, line=line ) # Left
    return align( end, ratio=1, line=line ) # Right

# MARK: Titles
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____ _ _   _                                                             │
# │ |_   _(_) |_| |___ ___                                                     │
# │   | | | |  _| / -_|_-<                                                     │
# │   |_| |_|\__|_\___/__/                                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

# Titles
def t1( msg:str = 'Title One', endl:str=os.linesep ):
    title = Figlet(font='standard', justify='center', width=columns).renderText(msg)
    pad.level = 1
    print( endl.join( [s for s in title.splitlines() if not re.match( r'^\s*$', s)] ) )


def t2(msg:str = 'Title Two',  endl:str=os.linesep ):
    title = Figlet(font='small', justify='left', width=columns).renderText(msg)
    pad.level = 1
    print(endl.join( [s for s in title.splitlines() if not re.match( r'^\s*$', s)] ))


def t3(msg:str = 'Title Three',  endl:str=os.linesep):
    pad.level = 1
    print(f'{'\n' if endl else ''} == {msg} ==')

# MARK: Sections
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _   _                                                         │
# │ / __| ___ __| |_(_)___ _ _  ___                                            │
# │ \__ \/ -_) _|  _| / _ \ ' \(_-<                                            │
# │ |___/\___\__|\__|_\___/_||_/__/                                            │
# ╰────────────────────────────────────────────────────────────────────────────╯

sections:Deque = Deque[str]()

class Section:
    def __init__(self, title=None ):
        self.title = title

    def start( self ):
        pad.level = 1
        title = Figlet(font='small', justify='left', width=columns).renderText(self.title)
        lines = [s for s in title.splitlines() if not re.match( r'^\s*$', s)]
        print( '\n'.join(lines) )

    def end( self ):
        pad.level = 1
        print( align( f'> End: {self.title} <' , line=hr('- ', 80)) )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.end()
        return False

# Sections
def s1(msg:str = 'Section One'):
    pad.level = 1
    sections.append( msg )
    print( align( f'[ {msg} ]' , line=hr('=', 80)) )


def s2(msg:str = 'Section two'):
    pad.level = 1
    sections.append( msg )
    print( align( f'- {msg} -' , line=hr('-', 80)) )

def send():
    pad.level = 1
    if not len(sections): raise Exception()
    print( align( f'> End: {sections.pop()} <' , line=hr('- ', 80)) )

# MARK: Headings
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  _             _ _                                                      │
# │ | || |___ __ _ __| (_)_ _  __ _ ___                                        │
# │ | __ / -_) _` / _` | | ' \/ _` (_-<                                        │
# │ |_||_\___\__,_\__,_|_|_||_\__, /__/                                        │
# │                           |___/                                            │
# ╰────────────────────────────────────────────────────────────────────────────╯

def h1(msg:str = 'Heading One' ):
    pad.level = 1
    h(msg)

def h2(msg:str = 'Heading two' ):
    pad.level = 2
    h(msg)

def hu( msg:str = '' ):
    if msg: h(msg, pad.level + 1)
    else: pad.level += 1

def hd( msg:str = '' ):
    if msg: h(msg, pad.level - 1)
    else: pad.level -= 1

def h(msg:str = 'Heading', level:int=None ):
    if level is None:level = pad.level
    padding:str = pad.padchar * level * pad.indent
    if level < len( pad.bullets ):
        bullet = pad.bullets[level]
    else:
        bullet = pad.bullets[-1]
    print(  f'{padding}{bullet} {msg}' )

def p( msg:typing.Any = 'Heading', level:int=None, pretty:bool=False ):
    from rich.pretty import pretty_repr

    if level is None:level = pad.level + 2
    padding:str = pad.padchar * level * pad.indent

    string = pretty_repr(msg) if pretty else repr(msg)
    for line in string.splitlines():
        print(  f'{padding}{line}' )

# MARK: CodeBox
# ╓────────────────────────────────────────────────────────────────────────────╖
# ║         ██████  ██████  ██████  ███████ ██████   ██████  ██   ██           ║
# ║        ██      ██    ██ ██   ██ ██      ██   ██ ██    ██  ██ ██            ║
# ║        ██      ██    ██ ██   ██ █████   ██████  ██    ██   ███             ║
# ║        ██      ██    ██ ██   ██ ██      ██   ██ ██    ██  ██ ██            ║
# ║         ██████  ██████  ██████  ███████ ██████   ██████  ██   ██           ║
# ╙────────────────────────────────────────────────────────────────────────────╜
# The above with:  CodeBox "CodeBox" -border "╓─╖║ ║╙─╜" -compact
# Support surrounding border | 012 | ╓─╖ | ╭─╮ | ▛▀▜
# and background             | 3B5 | ║ ║ | │ │ | ▌ ▐
# using nine characters.     | 678 | ╙─╜ | ╰─╯ | ▙▄▟
# Eg.
# "╓─╖║ ║╙─╜", "╔═╗║ ║╚═╝", "╭─╮│ │╰─╯", "▛▀▜▌ ▐▙▄▟",
# "┌─┐│ │└─┘", "┏━┓┃ ┃┗━┛", "╒═╕│ │╘═╛"
def code_box( msg:str = 'CodeBox',
    comment:str = '#',
    pad:str = ' ',
    border:str = "╭─╮│ │╰─╯",
    width:int = columns,
    compact:bool = True,
    above:str = '',
    below:str = '',
    ratio:float=0,
    ffont:str='small') -> str:

    if  len(border) < 9:
        edges:list[str] = list(border[0] * 9)
        edges[4] = ' '
    else:
        edges = list(border)

    if comment != edges[3]:
        for i in 0,3,6:
            edges[i] = f"{comment}{pad}{edges[i]}"

    lines:list = [ f"{comment}{pad}MARK: {msg}" ]

    top = bend( edges[0], edges[2], hr(edges[1], width=width) )
    if above: top = align( above, line= top )
    lines.append( top )

    mid = bend( edges[3], edges[5], hr(edges[4], width=width) )
    if not compact: lines.append( mid )

    try:
        f = Figlet( font=ffont )
    except FontNotFound:
        f = Figlet()

    for l in [s for s in f.renderText( msg ).splitlines() if not re.match( r'^\s*$', s)]:
        inner_width = width - len(edges[3]) - len(edges[5])
        line = hr(edges[4], width=inner_width)
        lines.append( ''.join([edges[3], align( l, ratio=ratio, line=line ), edges[5]]) )

    if not compact: lines.append( mid )

    end = bend( edges[6], edges[8], hr(edges[7], width=width) )
    if below: lines[3] = align( below, line= lines[3] )
    lines.append( end )

    return os.linesep.join(lines)


def main():
    t1("Format Test")
    print()
    print( os.linesep.join(["Testing share.format module",
        "This module uses the Python Rich library for additional things."]) )

    from rich.text import Text
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.console import Group

    group = Group(
        Text("If I want to modify rich renderables, I need to transform them into plain text using this kind of snippet:"),
        "",
        Syntax("""console = Console(color_system=None)
with console.capture() as capture:
    console.print("[bold magenta]Hello World[/]")
print( capture.get() )""",
            lexer='python', background_color="#444444") )
    print( Panel( group,  title="NOTE:", title_align='left') )


    # Fill

    print( align("format.fill") )
    print( hr("-=") )

    # Rich has the horizontal line class, but I feel like it isnt as flexible.


    # Align
    line = hr('-')
    print( align( "Alignment 0.5", line=line ) )
    print( align( "Alignment 0", ratio=0, line=line ) )
    print( align( "Alignment 1", ratio=1, line=line ) )
    stack = line
    for r in range(10):
        stack  = align( "|", ratio=r/10, line=stack )
    stack  = align( "[ align ]", ratio=0.5, line=stack )
    print( stack )

    t1("Title One - t1")
    t2("Title Two - t2")
    t3("Title Three - t3")

    s1("Section One - s1")
    s2("Section Two - s2")

    h1("Heading One - h1")
    h2("Heading Two - h2")
    hu("Heading up")
    hu("Heading up")
    hu("Heading up")
    hu("Heading up")
    hd("Heading down")
    hd("Heading down")
    hd("Heading down")

    print( code_box("CodeBox Aj%@!9") )

    with Section('Fetching Projects') as section:
        print( "Anything goes in the interior.")

if __name__ == "__main__":
    main()