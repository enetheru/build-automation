import os
import re

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

# Titles
def t1( msg:str = 'Title One', endl:str=os.linesep ):
    title = Figlet(font='standard', justify='center', width=columns).renderText(msg)
    return endl.join( [s for s in title.splitlines() if not re.match( r'^\s*$', s)] )


def t2(msg:str = 'Title Two',  endl:str=os.linesep ):
    title = Figlet(font='small', justify='left', width=columns).renderText(msg)
    return endl.join( [s for s in title.splitlines() if not re.match( r'^\s*$', s)] )


def t3(msg:str = 'Title Three',  endl:str=os.linesep):
    return  f'{'\n' if endl else ''} == {msg} =='


# Sections
def s1(msg:str = 'Section One',  endl:str=os.linesep ):
    return f'{'\n' if endl else ''}{align( f'[ {msg} ]' , line=hr('='))}'


def s2(msg:str = 'Section two',  endl:str=os.linesep ):
    return f'{'\n' if endl else ''}{align( f'- {msg} -' , line=hr('-'))}'

def send(msg:str = 'Section two',  endl:str=os.linesep ):
    return f'{'\n' if endl else ''}{align( f' {msg} ' , line=hr('- '))}'


# Headings
class Headings:
    def __init__(self):
        self.padchar = ' '
        self._level = 0
        self.indent = 2
        self.bullets = ['==', '--', '*', '-']

    @property
    def level(self):  # Getter
        return self._level
    @level.setter
    def level(self, value):
        self._level = value if value >= 0 else 0

headings = Headings()
def h1(msg:str = 'Heading One' ):
    headings.level = 0
    return  h(msg)

def h2(msg:str = 'Heading two' ):
    headings.level = 1
    return  h(msg)

def hu(msg:str = '' ) -> str:
    headings.level += 1
    return  h(msg) if msg else ''

def hd(msg:str = '' ):
    headings.level -= 1
    return  h(msg) if msg else ''

def h(msg:str = 'Heading' ):
    level:int = headings.level
    padding:str = headings.padchar * level * headings.indent
    if level < len( headings.bullets ):
        bullet = headings.bullets[level]
    else:
        bullet = headings.bullets[-1]
    return  f'{padding}{bullet} {msg}'

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

    print( t1("Title One - t1") )
    print( t2("Title Two - t2") )
    print( t3("Title Three - t3") )
    # print( t4("Title Four - t4") )

    print( s1("Section One - s1") )
    print( s2("Section Two - s2") )
    # print( s3("Section Three - s3") )
    # print( s4("Section Four - s4") )

    print( h1("Heading One - h1") )
    print( h2("Heading Two - h2") )
    print( hu("Heading up") )
    print( hu("Heading up") )
    print( hu("Heading up") )
    print( hu("Heading up") )
    print( hd("Heading down") )
    print( hd("Heading down") )
    print( hd("Heading down") )
    # print( h3("Heading Three - h3") )
    # print( h4("Heading Four - h4") )

    print( code_box("CodeBox Aj%@!9") )

if __name__ == "__main__":
    main()