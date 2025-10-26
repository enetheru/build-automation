import os
import re
import typing
from copy import deepcopy
from dataclasses import dataclass
from typing import Deque, Callable

import rich
from pyfiglet import Figlet
from pyfiglet import FontNotFound
from rich import print
from rich.pretty import pprint


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

    def __add__(self, other) -> str:
        return self.padchar * self.indent * self.level + other

    def __str__(self):
        return self.padchar * self.indent * self.level

    @property
    def level(self):  # Getter
        return self._level

    @level.setter
    def level(self, value):
        self._level = value if value >= 0 else 0

    def size( self ) -> int:
        return len( str(self) )

    def sizeu( self ) -> int:
        return len( str(self) ) + self.indent

pad = Padding()


# Horizontal Rule
def hr( filler:str=' ', width:int=rich.get_console().width ):
    """Generate a horizontal rule string.

    Args:
        filler (str, optional): The character to repeat. Defaults to ' '.
        width (int, optional): The width of the rule. Defaults to terminal width.

    Returns:
        str: The horizontal rule string.
    """
    line:str = filler
    while len(line) < width: line += filler
    return line[0:width]


# Align some text within a line
def align(msg:str='align', ratio:float=0.5, line:str=hr() ):
    """Align text within a line at a specified position.

    Args:
        msg (str, optional): The text to align. Defaults to 'align'.
        ratio (float, optional): The alignment position (0.0 for left, 1.0 for right). Defaults to 0.5.
        line (str, optional): The background line to align within. Defaults to a horizontal rule.

    Returns:
        str: The aligned text within the line.
    """
    if len(msg) > len(line): return msg # just return msg if we overwrite everything.
    pos:int = round((len(line) - len(msg)) * ratio)
    if pos < 0: return msg
    return f'{line[:pos]}{msg}{line[pos+len(msg):]}'

def bend( start:str, end:str, line:str=hr()):
    """Place text at both ends of a line.

    Args:
        start (str): Text to place at the start of the line.
        end (str): Text to place at the end of the line.
        line (str, optional): The background line. Defaults to a horizontal rule.

    Returns:
        str: The line with text at both ends.
    """
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
    """Display a large title using the 'standard' figlet font.

    Args:
        msg (str, optional): The title text. Defaults to 'Title One'.
        endl (str, optional): The line ending character. Defaults to os.linesep.

    Returns:
        None: Prints the title to the console.
    """
    title = Figlet(font='standard', justify='center', width=rich.get_console().width).renderText(msg)
    print( endl.join( [s for s in title.splitlines() if not re.match( r'^\s*$', s)] ) )


def t2(msg:str = 'Title Two',  endl:str=os.linesep ):
    """Display a medium title using the 'small' figlet font.

    Args:
        msg (str, optional): The title text. Defaults to 'Title Two'.
        endl (str, optional): The line ending character. Defaults to os.linesep.

    Returns:
        None: Prints the title to the console.
    """
    title = Figlet(font='small', justify='left', width=rich.get_console().width).renderText(msg)
    
    print(endl.join( [s for s in title.splitlines() if not re.match( r'^\s*$', s)] ))


def t3(msg:str = 'Title Three',  endl:str=os.linesep):
    """Display a small title with simple formatting.

    Args:
        msg (str, optional): The title text. Defaults to 'Title Three'.
        endl (str, optional): The line ending character. Defaults to os.linesep.

    Returns:
        None: Prints the title to the console.
    """
    
    print(f'{'\n' if endl else ''} == {msg} ==')

# MARK: Sections
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _   _                                                         │
# │ / __| ___ __| |_(_)___ _ _  ___                                            │
# │ \__ \/ -_) _|  _| / _ \ ' \(_-<                                            │
# │ |___/\___\__|\__|_\___/_||_/__/                                            │
# ╰────────────────────────────────────────────────────────────────────────────╯

def style_start_fallback(self) -> str:
    depth = '.'.join(str(i+1) for i in self.path)
    return pad + f"{depth} - {self.name}"

def style_end_fallback(self) -> str:
    # return align(f'> End: {self.name} <', ratio=0, line=hr('- '))
    return ''

# 2D Index dataclass
@dataclass
class SectionIndex:
    depth: int = 0
    item: int = 0

    def increment(self):
        self.depth += 1
        self.item += 1

    def __str__(self) -> str:
        return f"{self.depth}.{self.item}"


class Section:
    last_index : SectionIndex = SectionIndex(-1,-1)
    _styles:list[dict[str,Callable]] = [] # each depth can have its own style

    _table_of_contents:dict['Section','Section'] = {}
    _breadcrumbs : Deque['Section'] = Deque()

    _style_fallback:dict[str,Callable] = {
        'start':style_start_fallback,
        'end':style_end_fallback,
    }

    def __init__(self, name=str()):
        self.idx : SectionIndex = SectionIndex(depth=-1,item=-1)
        self.name:str = name
        self.parent = None
        self.children = []
        self.defunct = False
        self.path : list[int] = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.end()
        return False

    def start( self ):
        # Set parent from breadcrumbs
        crumbs = Section._breadcrumbs
        self.parent = crumbs[-1] if len(crumbs) else None

        # Walk the table of contents to get the current level.
        toc : dict = Section._table_of_contents
        for crumb in crumbs:
            toc = toc[crumb]
            self.path.append(crumb.idx.item)

        self.idx = deepcopy(Section.last_index)
        self.idx.depth += 1
        self.idx.item = len(toc)
        self.path.append(self.idx.item)
        Section.last_index = self.idx

        toc[self] = {}
        self.print('start')

        Section._breadcrumbs.append(self)
        pad.level += 1



    def end( self ):
        if self.defunct: return
        self.defunct = True

        # Take ourselves off the deck
        Section._breadcrumbs.pop()

        # latest should be our parent
        latest = Section.last()
        if latest != self.parent:
            raise Exception("these should be the same.")

        Section.last_index = SectionIndex(-1,-1) if latest is None else latest.idx

        self.print('end')
        pad.level -=1

    def print( self, mode:str ):
        style_func:Callable

        styles = Section._styles
        style = styles[self.idx.depth] if 0 <= self.idx.depth < len(styles) else None

        if style is None:
            style_func = Section._style_fallback[mode]
        else:
            style_func = style.get(mode, Section._style_fallback[mode])

        print( style_func(self) )

    @staticmethod
    def last() -> 'Section':
        return Section._breadcrumbs[-1] if len(Section._breadcrumbs) else None

    @staticmethod
    def pop() -> 'Section':
        section : Section = Section.last()
        if not section: raise Exception()
        section.end()
        return section

    @staticmethod
    def set_styles( styles:list[dict[str,Callable]]):
        Section._styles = styles

    @staticmethod
    def get_toc(section : dict = None) -> dict:
        if section is None:
            section = Section._table_of_contents
        return { f'{k.idx} - {k.name}': Section.get_toc(v) for k,v in section.items() }


# Sections
def s1(msg:str = 'Section One') -> Section:
    while Section.last_index.depth > 0:
        Section.pop()
    return Section( msg )


def s2(msg:str = 'Section two') -> Section:
    while Section.last_index.depth > 1:
        Section.pop()
    return Section( msg )

# MARK: Headings
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  _             _ _                                                      │
# │ | || |___ __ _ __| (_)_ _  __ _ ___                                        │
# │ | __ / -_) _` / _` | | ' \/ _` (_-<                                        │
# │ |_||_\___\__,_\__,_|_|_||_\__, /__/                                        │
# │                           |___/                                            │
# ╰────────────────────────────────────────────────────────────────────────────╯

def h1(msg:str = 'Heading One' ):
    
    h(msg)

def h2(msg:str = 'Heading two' ):
    
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
def code_box(msg:str = 'CodeBox',
             comment:str = '#',
             padding:str = ' ',
             border:str = "╭─╮│ │╰─╯",
             width:int = rich.get_console().width,
             compact:bool = True,
             above:str = '',
             below:str = '',
             ratio:float=0,
             ffont:str='small') -> str:
    """Generate a formatted code box with ASCII art borders.

    Args:
        msg (str, optional): The text to display in the box. Defaults to 'CodeBox'.
        comment (str, optional): The comment character for borders. Defaults to '#'.
        padding (str, optional): Padding character for borders. Defaults to ' '.
        border (str, optional): Nine-character string defining the box borders. Defaults to '╭─╮│ │╰─╯'.
        width (int, optional): The box width. Defaults to terminal width.
        compact (bool, optional): If True, omit middle border lines. Defaults to True.
        above (str, optional): Text to place above the box. Defaults to ''.
        below (str, optional): Text to place below the box. Defaults to ''.
        ratio (float, optional): Text alignment ratio within the box. Defaults to 0.
        ffont (str, optional): Figlet font for the text. Defaults to 'small'.

    Returns:
        str: The formatted code box string.
    """

    if  len(border) < 9:
        edges:list[str] = list(border[0] * 9)
        edges[4] = ' '
    else:
        edges = list(border)

    if comment != edges[3]:
        for i in 0,3,6:
            edges[i] = f"{comment}{padding}{edges[i]}"

    lines:list = [ f"{comment}{padding}MARK: {msg}"]

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

def style_s1(self) -> str:
    return align( f'[ {self.name} ]' , line=hr('='))

def style_s2(self) -> str:
    return align( f'- {self.name} -' , line=hr('-'))

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

    with Section('Fetching Projects'):
        print( "Anything goes in the interior.")
        print( pad +  "Anything goes in the interior.")
        with Section('nested Sections'):
            print( "Further to the interior.")

        with Section('Sibling Sections'):
            print( "Further to the interior.")

        with Section('Breaking'):
            with Section('Out'):
                with Section('Of'):
                    with Section('Deeply'):
                        with s1('Nested'):
                            with Section('Sections'):
                                print("OK")

    Section.set_styles(  [
        { 'start':style_s1 },
        { 'start':style_s2 }
    ])
    with Section('Section Styles'):
        with Section('per Level'):
            print("OK")

    Section.set_styles([])

    pprint( Section.get_toc(), expand_all=True )



if __name__ == "__main__":
    main()