#!/usr/bin/env python
"""Build processing utilities: fetch, process builds/projects, stats."""
import json
import os
import re
from datetime import datetime, timedelta
from time import sleep
from types import SimpleNamespace

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src import format as fmt
from src.ConsoleMultiplex import ConsoleMultiplex, TeeOutput
from src.error import handle_error
from src.generate import write_namespace
from src.run import ENDCMD, PANEL_LABEL, stream_command
from src.utils import get_interior_dict, process_log_null

console = ConsoleMultiplex()
pretendio = type('obj', (object,), {'write': lambda self, v: print(v)})()

def print_full_table(table: Table) -> None:
    """Print a table without ellipsizing it to a narrow terminal.

    Rich sizes a table to the console width, then clips cells. A pipe is 80
    columns, which turns the summary into "Fai…" and "0:0…". The width is
    restored so later output still follows the terminal.
    """
    saved = (console._width, console._height)
    console._width = 400
    console._height = 1024
    try:
        console.print(table, soft_wrap=True)
    finally:
        console._width, console._height = saved


# Child section headings. Their numbers restart at 1; the text is not
# output of the command that ran inside the previous section.
_HEADING = re.compile(r'^\s*\d+(?:\.\d+)* - ')
# CMake repeats the build directory and the tool command before ninja runs.
_SKIP_LINE = re.compile(r'^(?:Change Dir:|Run Build Command\(s\):)')
# A drive path ending at the first segment, e.g. C:\Program or "C:\Program.
# The next token (Files\...) belongs on the same line, quote included.
_PATH_TAIL = re.compile(r'"?[A-Za-z]:\\[^\\"\s]*$')
_PATH_HEAD = re.compile(r'^(.*?)("?[A-Za-z]:\\[^\\"\s]*)$')
# Widest command box. The live box follows the terminal, and build_log.log
# gets that same box. A pipe reports 80. File consoles still use this so a
# dumb terminal does not fall back to 80 for tables.
LOG_WIDTH = 240


def _screen_width() -> int:
    """Columns for the command box on screen and in build_log.log.

    A wider line is wrapped by the terminal, which pulls the right border
    into the middle of the next row. Legacy mode already reports one
    column less. A modern terminal needs that column left spare, or the
    newline after a full-width row opens a blank line.
    """
    spare = 0 if console.legacy_windows or console.is_dumb_terminal else 1
    width = console.width - spare
    if width > LOG_WIDTH:
        width = LOG_WIDTH
    if width < 20:
        width = 20
    return width


def panel_title(section: str, label: str) -> str:
    """The section name, plus the command's own name when it sent one.

    A test phase is a single section. The label is what distinguishes the
    panels inside it: "Test: doctest", "Test: fibers-engine".
    """
    label = label.strip()
    if not label:
        return section
    return f'{section}: {label}'


def _display_line(text: str) -> Text:
    """One captured line, with tool color kept and markup left off.

    The child is a pipe, so cmake and ninja send ANSI instead of painting
    the terminal themselves. Square brackets stay literal: [1/83] is not a tag.
    """
    return Text.from_ansi(text)


class CommandFrame:
    """A command panel that stays open while the command's lines arrive.

    The screen and build_log.log get the same box, wrapped to the terminal.
    Lines wrap on spaces. A single token longer than the box is split so
    the border stays aligned. The screen keeps ANSI color. The log gets the
    same characters with the codes removed. Blank lines are dropped.
    """

    def __init__(self, cmd: str, title: str):
        self.screen_width = _screen_width()
        self._emit(self._title(title, self.screen_width))
        self.line(cmd)

    def line(self, text: str) -> None:
        styled = _display_line(text)
        plain = styled.plain
        if not plain.strip():
            return
        # Per-build logs keep the compiler line whole. The box is only for
        # the session log and the screen, and those two match.
        self._plain(plain)
        for part in self._wrap_styled(styled, self.screen_width - 4):
            self._emit(self._row_text(part, self.screen_width))

    def _wrap_styled(self, styled: Text, inner: int) -> list[Text]:
        """Wrap on spaces, keeping the styles on each slice.

        A quoted span stays together, and so does a Windows path such as
        C:\\Program Files\\.... Cmd quote toggling would otherwise swallow
        the rest of a link line into one token and slice it mid-path.
        A span that cannot fit breaks at the previous space.
        """
        lines: list[Text] = []
        current = Text()
        for token in self._atom_texts(styled, inner):
            piece = token
            while len(piece.plain) > inner:
                if current.plain:
                    lines.append(current)
                    current = Text()
                lines.append(piece[:inner])
                piece = piece[inner:]
            if not piece.plain:
                continue
            extra = len(piece.plain) if not current.plain else len(piece.plain) + 1
            if current.plain and len(current.plain) + extra > inner:
                lines.append(current)
                current = piece
            elif current.plain:
                current.append(' ')
                current.append(piece)
            else:
                current = piece
        if current.plain:
            lines.append(current)
        return lines

    def _atom_texts(self, styled: Text, inner: int) -> list[Text]:
        plain = styled.plain
        spans: list[tuple[int, int]] = []
        i = 0
        n = len(plain)
        while i < n:
            if plain[i] == ' ':
                i += 1
                continue
            j = i + 1
            while j < n and plain[j] != ' ':
                j += 1
            spans.append((i, j))
            i = j

        atoms: list[Text] = []
        buf: Text | None = None
        for start, end in spans:
            part = styled[start:end]
            if buf is None or not buf.plain:
                buf = part
                continue
            buf_plain = buf.plain
            part_plain = part.plain
            joined = len(buf_plain) + 1 + len(part_plain)
            keep = self._quote_open(buf_plain) or self._continues_path(buf_plain, part_plain)
            if keep and joined <= inner:
                buf.append(' ')
                buf.append(part)
                continue
            if self._continues_path(buf_plain, part_plain):
                head, tail = self._split_path_head(buf_plain)
                if head:
                    atoms.append(buf[:len(head)])
                if tail:
                    buf = buf[len(buf_plain) - len(tail):]
                    buf.append(' ')
                    buf.append(part)
                else:
                    buf = part
                continue
            atoms.append(buf)
            buf = part
        if buf is not None and buf.plain:
            atoms.append(buf)
        return atoms

    @staticmethod
    def _quote_open(text: str) -> bool:
        """True when a double quote is still open. \\\" is not a toggle."""
        count = 0
        i = 0
        while i < len(text):
            if text[i] == '\\' and i + 1 < len(text) and text[i + 1] == '"':
                i += 2
                continue
            if text[i] == '"':
                count += 1
            i += 1
        return count % 2 == 1

    @staticmethod
    def _continues_path(left: str, right: str) -> bool:
        if not right or right[0] in '-/':
            return False
        if _PATH_TAIL.search(left) is None:
            return False
        return '\\' in right or '/' in right

    @staticmethod
    def _split_path_head(buf: str) -> tuple[str, str]:
        match = _PATH_HEAD.match(buf)
        if match is None:
            return buf, ''
        return match.group(1).rstrip(), match.group(2)

    def close(self) -> None:
        self._emit(self._edge('└', '┘', self.screen_width))

    def _row_text(self, part: Text, width: int) -> Text:
        inner = width - 4
        gap = inner - len(part.plain)
        if gap < 0:
            gap = 0
        row = Text('│ ')
        row.append(part)
        if gap:
            row.append(' ' * gap)
        row.append(' │')
        return row

    def _title(self, title: str, width: int) -> str:
        label = f' {title} '
        inner = width - 4
        if len(label) > inner:
            label = label[: max(inner, 0)]
        return '┌─' + label + '─' * (inner - len(label)) + '─┐'

    @staticmethod
    def _edge(left: str, right: str, width: int) -> str:
        return left + '─' * (width - 2) + right

    def _emit(self, text: str | Text) -> None:
        self._screen(text)
        self._log(text.plain if isinstance(text, Text) else text)

    def _screen(self, text: str | Text) -> None:
        if console.quiet:
            return
        if isinstance(text, Text):
            Console.print(console, text, soft_wrap=True)
            return
        Console.print(console, text, markup=False, highlight=False, soft_wrap=True)

    def _log(self, text: str) -> None:
        dest = console.outputs.get('build_log')
        if dest is not None:
            dest.print(text, markup=False, highlight=False, soft_wrap=True)

    def _plain(self, text: str) -> None:
        for name, dest in console.outputs.items():
            if name == 'build_log':
                continue
            dest.print(text, markup=False, highlight=False, soft_wrap=True)


def _parse_duration(value) -> timedelta | None:
    if isinstance(value, timedelta):
        return value
    text = str(value).strip()
    if text.count(':') != 2:
        return None
    try:
        hours, minutes, seconds = text.split(':')
        return timedelta(
            hours=int(hours),
            minutes=int(minutes),
            seconds=float(seconds),
        )
    except ValueError:
        return None


def _format_duration(delta: timedelta) -> str:
    text = str(delta)
    if '.' not in text:
        return text
    head, frac = text.split('.', 1)
    return f'{head}.{frac[:3]}'


def _startup(stats: dict) -> str:
    """Time in the script outside the timed sections.

    Section timers start after import. The row total is the parent's wall
    clock, so the difference is startup plus the gaps between steps.
    """
    total = _parse_duration(stats.get('duration'))
    if total is None:
        return 'n/a'
    spent = timedelta(0)
    for sub in stats.get('subs', {}).values():
        part = _parse_duration(sub.get('duration') if isinstance(sub, dict) else None)
        if part is None:
            return 'n/a'
        spent += part
    gap = total - spent
    if gap < timedelta(0):
        gap = timedelta(0)
    return _format_duration(gap)


def log_console(log_file):
    """Plain, wide console for a log file.

    force_terminal writes ANSI into the file. Rich also ignores a width
    unless height is set, when the console is a dumb terminal, and then
    lays tables out at 80 columns. soft_wrap keeps long lines intact.
    """
    return Console(
        file=log_file,
        color_system=None,
        soft_wrap=True,
        # Both dimensions are required. A dumb terminal ignores width alone
        # and goes back to 80. Wider than a status row, short of a full-width
        # box of padding. soft_wrap still keeps PATH and compiler lines whole.
        width=LOG_WIDTH,
        height=1024,
    )




# (fetch_project / git_fetch_project / process_* moved to src/build_utils.py)
# MARK: Build
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___      _ _    _                             │
# │ | _ \_ _ ___  __ ___ ______ | _ )_  _(_) |__| |                            │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< | _ \ || | | / _` |                            │
# │ |_| |_| \___/\__\___/__/__/ |___/\_,_|_|_\__,_|                            │
# ╰────────────────────────────────────────────────────────────────────────────╯
"""Process a single build configuration: generate script, execute actions (source/build/etc.), monitor.

Args:
    opts (SimpleNamespace): Global opts.
    build (SimpleNamespace): Build object.

Side effects:
    Runs pwsh/python script, captures logs/stats.
"""
def _escalate_cancel() -> None:
    """Wait so another CTRL+C can cancel the next larger scope.

    Re-raise with a bare ``raise``. ``except KeyboardInterrupt as e: raise e``
    chains a new exception onto the first, and a context manager that then
    fails prints that chain instead of the next cancel line.
    """
    try:
        sleep(3)
    except KeyboardInterrupt:
        raise


def process_build( opts:SimpleNamespace, build:SimpleNamespace ):
    """

    :param opts:
    :param build:
    :return:
    """
    project = build.project

    if opts.verbose:
        console.line()
        fmt.t2( f'Process: {build.name}' )
        write_namespace( pretendio, build, 'build')
        write_namespace( pretendio, build.toolchain, 'toolchain')
        write_namespace( pretendio, build.buildtool, 'buildtool')

    setattr( build, 'stats', { # type: ignore[attr-defined]
        'status': "dnf",
        'duration':"dnr",
        'subs':{}
    })
    stats = build.stats

    # Skip the build config if there are no actions to perform
    skip:bool=True
    for k in opts.build_actions:
        if k in build.verbs:
            skip = False

    if skip:
        build.stats |= {"status":'Skipped'}
        return

    if build.disabled:
        build.stats |= {"status":'Disabled'}
        return

    # =====================[ stdout Logging ]======================-
    log_path = project.path / f"logs-raw/{build.name}.log"
    with (
        open( file=log_path, mode='w', buffering=1, encoding="utf-8" ) as build_log,
        TeeOutput(console, log_console(build_log), build.name ),
        fmt.Section(build.name)
    ):

        # =================[ Build Heading / Config ]==================-
        fmt.h( "Script: " + build.script_path.as_posix() )

        # ==================[ Print Configuration ]====================-
        from rich.panel import Panel
        from rich.syntax import Syntax

        # Show the script.
        if opts.show:
            with open(build.script_path, "rt") as code_file:
                syntax = Syntax(code_file.read(),
                                lexer="python",
                                code_width=110,
                                line_numbers=True,
                                tab_size=2,
                                dedent=True,
                                word_wrap=True)
            print( Panel( syntax,
                          title=str(build.script_path),
                          title_align='left',
                          expand=False,
                          width=120 ) )

        # ====================[ Run Build Script ]=====================-
        # The child is another process, so its headings restart at 1.
        # A command panel stays open until that command ends, and the lines
        # it prints are rows in the same box.
        current: dict[str, CommandFrame | None] = {'frame': None}
        step = {'title': 'command', 'label': ''}

        def write_line(line: str) -> None:
            # Outside the frame. ANSI still paints on screen; a file console
            # with no color system stores the plain text. Markup stays off.
            console.print(Text.from_ansi(line), soft_wrap=True)

        def close_frame() -> None:
            frame = current['frame']
            if frame is None:
                return
            frame.close()
            current['frame'] = None

        def emit(line: str) -> None:
            if line == ENDCMD:
                close_frame()
                return

            # Names the next panel. Not output, and not a heading.
            if line.startswith(PANEL_LABEL):
                step['label'] = line[len(PANEL_LABEL):].strip()
                return

            # The working directory is already in the command text.
            if line.startswith('CWD ') or _SKIP_LINE.match(line):
                return

            if _HEADING.match(line):
                close_frame()
                shown = line.strip()
                # The child printed this blank line already. Blank lines are
                # dropped on the way through, so write it again here.
                write_line('')
                write_line(shown)
                step['title'] = shown.split(' - ', 1)[-1]
                step['label'] = ''
                return

            if line.startswith('  $ ') or line.startswith('$ '):
                cmd = line.split('$ ', 1)[1]
                close_frame()
                current['frame'] = CommandFrame(cmd, panel_title(step['title'], step['label']))
                step['label'] = ''
                return

            if current['frame'] is not None:
                current['frame'].line(line)
                return

            if not line.strip():
                return

            write_line(line)

        def monitor_output( line ):
            """

            :param line:
            """
            if line.startswith('json:'): stats['subs'].update(json.loads( line[6:] ))
            else: emit(line)

        errors:list = []
        def capture_error(line: str) -> None:
            errors.append(line)
            emit(line)

        shell = getattr(build.toolchain, 'shell', [])
        env = getattr(build.toolchain, 'env', None )

        cmd = f'python {build.script_path.as_posix()}'
        run_cmd = ' '.join( shell + [f'"{cmd}"']) if shell else cmd
        # The script path is already on the Script line. A shell wrapper is
        # the invocation that is not shown there.
        if shell:
            current['frame'] = CommandFrame(run_cmd, 'RunCmd')
        try:
            stats |= { 'start_time':datetime.now() }
            # quiet: this invocation is the panel above. The script prints
            # its own commands, and emit frames those.
            proc = stream_command( run_cmd, env=env, quiet=True,
                                   stdout_handler=monitor_output,
                                   stderr_handler=capture_error
                                   )
            end_time = datetime.now()
            stats |= {
                'status': "Dry-Run" if opts.dry else "Completed",
                'end_time': end_time,
                'duration': end_time - stats["start_time"]
            }
            proc.check_returncode()
        except KeyboardInterrupt:
            close_frame()
            end_time = datetime.now()
            stats |= {
                "status": "Cancelled",
                "end_time": end_time,
                "duration": end_time - stats["start_time"]
            }

            # Leave the build log attached. The with-block closes it.
            # Popping it here made that close raise over the KeyboardInterrupt.
            console.print(
                "Build cancelled. Continuing in 3s. CTRL+C cancels this project.",
                markup=False,
            )
            _escalate_cancel()
            console.print("Continuing.", markup=False)
        except Exception as e:
            end_time = datetime.now()
            stats |= {
                "status": "Failed",
                "end_time": end_time,
                "duration": end_time - stats["start_time"]
            }
            close_frame()
            handle_error(f"process_build cmd={run_cmd}", e, opts)
            if errors:
                console.print(Panel(Text('\n'.join(errors)), title='stderr', style="red"))
        finally:
            close_frame()

        # TODO create a timeout for the processing, something reasonable.
        #   this should be defined in the build config as the largest possible build time that is expected.
        #   that way it can trigger a check of the system if it is failing this test.

    # The clean copy writes a file and prints nothing.
    cleanlog_path = (project.path / f"logs-clean/{build.name}.txt")
    if 'clean_log' in  get_interior_dict(build).keys():
        clean_log = build.clean_log
    else: clean_log = process_log_null

    with (open(log_path, encoding='utf-8') as log_raw,
          open( cleanlog_path, "w", encoding='utf-8' ) as log_clean):
        clean_log( log_raw, log_clean )


def _build_will_run(opts: SimpleNamespace, build: SimpleNamespace) -> bool:
    """True when this config has a requested action and is not disabled."""
    if getattr(build, 'disabled', False):
        return False
    verbs = getattr(build, 'verbs', None) or []
    return any(action in verbs for action in opts.build_actions)


def _run_project_builds(opts: SimpleNamespace, project: SimpleNamespace) -> None:
    project_total = len(project.build_configs)
    build_num = 0
    for build in project.build_configs.values():
        build_num += 1
        console.set_window_title(f"{project.name}[{build_num}:{project_total}] - {build.name}")
        try:
            process_build(opts, build)
        except KeyboardInterrupt:
            console.print(
                f"Project {project.name} cancelled. Continuing in 3s. CTRL+C cancels the run.",
                markup=False,
            )
            _escalate_cancel()
            console.print("Continuing.", markup=False)


def process_project(opts: SimpleNamespace, project: SimpleNamespace):
    """Run the requested build actions for one project.

    Fetch is its own section in the caller, before scripts are generated.
    A config that will not run records a skipped row and does not open a heading.
    """
    os.chdir(project.path)

    os.makedirs(project.path / "logs-raw", exist_ok=True)
    os.makedirs(project.path / "logs-clean", exist_ok=True)

    actions = []
    for action in opts.build_actions:
        if any(action in (getattr(build, 'verbs', None) or [])
               for build in project.build_configs.values()
               if _build_will_run(opts, build)):
            actions.append(action)

    log_path = project.path / f"logs-raw/{project.name}.log"
    with (
        open(file=log_path, mode='w', buffering=1, encoding="utf-8") as log_file,
        TeeOutput(console, log_console(log_file), project.name),
    ):
        if opts.verbose:
            fmt.t2(project.name)
            console.rule("Project Config:")
            write_namespace(pretendio, project, 'project')
            console.rule("Build Configurations")
            for build in project.build_configs.values():
                fmt.h(build.name)

        if actions:
            with fmt.Section(f"{project.name} - {', '.join(actions)}"):
                _run_project_builds(opts, project)
        else:
            _run_project_builds(opts, project)



def has_statistics(opts: SimpleNamespace) -> bool:
    """True when a build has recorded a stats row."""
    return any(
        getattr(build, 'stats', None) is not None
        for project in opts.projects.values()
        for build in project.build_configs.values()
    )


# (show_statistics moved to src/build_utils.py)
def show_statistics( opts:SimpleNamespace ):
    """Display a table summarising build status and durations.

    Args:
        opts (SimpleNamespace): Configuration options containing project and build statistics.

    Returns:
        None: Prints a rich table with build status, duration, and sub-action durations.
    """
    if not has_statistics(opts):
        return

    table = Table( title="Stats", highlight=True, min_width=80 )

    # unique set of available data names
    column_set:set = set()
    for project in opts.projects.values():
        for build in project.build_configs.values():
            if not 'stats' in build.__dict__: continue
            if not 'subs' in build.stats: continue
            for key in build.stats['subs'].keys():
                column_set.add(key)

    table.add_column( "Project/Config", style="cyan", overflow="ignore", no_wrap=True )
    table.add_column( "Status", overflow="ignore", no_wrap=True )
    table.add_column( "Total Time", overflow="ignore", no_wrap=True )
    table.add_column( "Startup", overflow="ignore", no_wrap=True )

    sub_columns:list = []
    for action in opts.build_actions:
        if action in column_set:
            sub_columns.append( action )
            table.add_column( action, overflow="ignore", no_wrap=True )

    for project in opts.projects.values():
        for build in project.build_configs.values():
            if not getattr(build, 'stats', None): continue

            r:list = [f"{project.name}/{build.name}"]

            colour = "green"
            status = build.stats['status']
            match status:
                case 'Completed':
                    colour = "green"
                    pass
                case 'Cancelled' | 'Dry-Run' | 'Skipped', 'Disabled':
                    colour = "yellow"
                case 'Failed':
                    colour = "red"

            r.append(f"[{colour}]{status}[/{colour}]")
            r.append(str(build.stats['duration']))
            r.append(_startup(build.stats))

            subs = build.stats.get('subs', {})
            for column_name in sub_columns:
                sub = subs.get(column_name, None )
                if not sub: r.append( 'n/a' )
                elif sub.get('status', None) == 'Failed':
                    r.append(f"[red]{sub['duration']}[/red]")
                else: r.append( str(sub['duration']) )

            table.add_row( *r )
    print_full_table(table)


# MARK: Toolchain Actions
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____         _    _         _          _      _   _                      │
# │ |_   _|__  ___| |__| |_  __ _(_)_ _     /_\  __| |_(_)___ _ _  ___         │
# │   | |/ _ \/ _ \ / _| ' \/ _` | | ' \   / _ \/ _|  _| / _ \ ' \(_-<         │
# │   |_|\___/\___/_\__|_||_\__,_|_|_||_| /_/ \_\__|\__|_\___/_||_/__/         │
# ╰────────────────────────────────────────────────────────────────────────────╯

"""Execute toolchain-specific actions (e.g. 'update') for matching toolchains.

Args:
    opts (SimpleNamespace): Options with toolchain_actions.
"""
def process_toolchains( opts:SimpleNamespace ):
    """Process toolchain-specific actions based on provided options.

    Args:
        opts (SimpleNamespace): Configuration options containing toolchain actions and definitions.

    Returns:
        None: Executes toolchain-specific actions (e.g. update, script) for matching toolchains.
    """
    for verb in opts.toolchain_actions:
        for toolchain_name, toolchain in opts.toolchains.items():
            if verb in getattr( toolchain, 'verbs', [] ):
                with fmt.Section(f"{toolchain.name} - {verb}"):
                    getattr( toolchain, verb )( toolchain, opts, console )
