"""
Configuration settings and build definitions for the Godot project.
"""

import copy
import pathlib
import re

from src.config import gopts, project_base, git_base, scons_base, godot_platforms, godot_arch
from src.expand_config import expand_func, short_host, expand_attr_list
from share.script_preamble import *

# MARK: Notes
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  _     _                                                                │
# │ | \| |___| |_ ___ ___                                                      │
# │ | .` / _ \  _/ -_|_-<                                                      │
# │ |_|\_\___/\__\___/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
# =======================[ Emscripten ]========================-
# latest version gives this error
# scons: *** [bin\.web_zip\godot.editor.worker.js] The system cannot find the file specified
# https://forum.godotengine.org/t/error-while-building-godot-4-3-web-template/86368

# Official Requirements:
# godotengine - 4.0+     | Emscripten 1.39.9
# godotengine - 4.2+     | Emscripten 3.1.39
# godotengine - master   | Emscripten 3.1.62

# But in the github action runner, it's 3.1.64
# And all the issues related show 3.1.64

# MARK: Notes

origin = SimpleNamespace({**vars(git_base), **{
    'name':'origin',
    'url': "https://github.com/godotengine/godot.git/",
    'ref': 'master'
}})

# The Tracy fork comes from the local Godot clone on the box, not the internet.
# Fetching from a local repo only sees its branches (refs/heads/*), so the ref is
# the clone's local `tracy` branch.
TRACY_SOURCE_PATH = "C:/Godot/src/godot-private"
TRACY_REF = 'enetheru/4.7-tracy'

# The Tracy profiler sources, pinned to one release. config_tracy checks the
# version header so a different Tracy in that folder can't slip into a build.
TRACY_VERSION = '0.14.1'
TRACY_PROFILER_PATH = "C:/git/wolfpld/tracy"

# Tools and harnesses for the test step (box defaults). The generated build
# script only carries the body of test_scons, so configure_scons copies these
# onto the build as build['tracy_test']. A missing tool or harness makes its
# stage skip with a message.
TRACY_TOOLS_PATH = "C:/Users/nicho/AppData/Local/Microsoft/WinGet/Packages/wolfpld.tracy_Microsoft.Winget.Source_8wekyb3d8bbwe"
TRACY_CAPTURE = f"{TRACY_TOOLS_PATH}/tracy-capture.exe"
TRACY_CSVEXPORT = f"{TRACY_TOOLS_PATH}/tracy-csvexport.exe"
# Notes, toggle harness and libTracyServer analyser source from the silent-client run.
TRACY_SILENT_CLIENT_LOGS = "C:/build/godot/logs/godot-tracy-build-logs/silent-client-f4c9c31"
TRACY_ANALYZER_SRC = f"{TRACY_SILENT_CLIENT_LOGS}/trace-analyzer.cpp"
# Built once by the test step when missing, against the csvexport build's libTracyServer.a.
TRACY_ANALYZER = f"{TRACY_TOOLS_PATH}/trace-analyzer.exe"
TRACY_FIBERS_GD = "/workspace/fiber-trace-harness/fibers.gd"
TRACY_TOGGLE_GD = f"{TRACY_SILENT_CLIENT_LOGS}/toggle.gd"
TRACY_CAPTURE_ADDR = '127.0.0.1'
TRACY_CAPTURE_PORT = '8086'
TRACY_TEST_FEATURES = 'zones,plots,messages,frames,gdscript_zones_auto,gdscript_zones_manual'
TRACY_TEST_TIMEOUT = 300    # seconds for one engine run

TRACY_TEST = {
    'version': TRACY_VERSION,
    'profiler_path': TRACY_PROFILER_PATH,
    'tools_path': TRACY_TOOLS_PATH,
    'capture': TRACY_CAPTURE,
    'csvexport': TRACY_CSVEXPORT,
    'analyzer': TRACY_ANALYZER,
    'analyzer_src': TRACY_ANALYZER_SRC,
    'fibers_gd': TRACY_FIBERS_GD,
    'toggle_gd': TRACY_TOGGLE_GD,
    'address': TRACY_CAPTURE_ADDR,
    'port': TRACY_CAPTURE_PORT,
    'features': TRACY_TEST_FEATURES,
    'timeout': TRACY_TEST_TIMEOUT,
}

sources:dict = {
    'origin': origin,
    '4.5': SimpleNamespace({**vars(origin), **{
        'ref': '4.5'
    }}),
    '4.6': SimpleNamespace({**vars(origin), **{
        'ref': '4.6'
    }}),
    '4.7': SimpleNamespace({**vars(origin), **{
        'ref': '4.7'
    }}),
    'tracy': SimpleNamespace({**vars(origin), **{
        'remote':'godot-private',
        'url': TRACY_SOURCE_PATH,
        'ref': TRACY_REF
    }}),
}

project = SimpleNamespace({**vars(project_base), **{
    'name': 'godot',
    'verbs': ['fetch'],
    'sources': sources
}})

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

_VERSION_NUM = re.compile(r'^(\d+\.\d+(?:\.\d+)?)')


def _describe_version(repo: pathlib.Path, ref: str) -> str | None:
    """Tag name when `ref` is that tag, otherwise `<version>~`.

    `<version>~` is the numeric part of the closest ancestor tag. The tilde
    means the ref has commits after that tag. Both forms are filename-safe.
    """
    import git
    from git.exc import GitCommandError

    g = git.cmd.Git(repo)
    try:
        return g.describe('--tags', '--exact-match', ref)
    except GitCommandError:
        pass
    try:
        tag = g.describe('--tags', '--abbrev=0', ref)
    except GitCommandError:
        return None
    match = _VERSION_NUM.match(tag)
    version = match.group(1) if match else tag.replace('/', '-')
    return f'{version}~'


def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    """
    Generate the project build configuration.
    :param opts:
    :return:
    """
    import platform
    from src.config import build_base

    from share.snippets import show_stats

    setattr(project, 'path', opts.path / 'godot')       # type: ignore[attr-defined]
    setattr(project, 'buildtools', {             # type: ignore[attr-defined]
        'scons': SimpleNamespace({**vars(scons_base), **{
            'expand':expand_scons,
            'configure':configure_scons,
        }}),
    })

    # Expand the source definitions.
    builds:list[SimpleNamespace] = expand_func(
        [build_base],
        expand_attr_list,
        'source_def',
        sources.values() )

    # Expand toolchains (each toolchain expand sets arch × platform)
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'toolchain',
        gopts.toolchains.values() )

    # generic_toolchain_expand records the pair on the toolchain.
    # Variant filters and the mingw arch checks read build.arch.
    # Android's expand records the ABI on the build and leaves the pair unset.
    for build in builds:
        tc = build.toolchain
        if not hasattr(tc, 'host'):
            tc.host = platform.system()
        if hasattr(tc, 'target_arch'):
            build.arch = tc.target_arch
            build.platform = tc.target_platform
        else:
            tc.target_arch = build.arch
            tc.target_platform = build.platform

    # Expand build tools
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'buildtool',
        project.buildtools.values() )

    builds = expand_func( builds, expand_variations )
    builds = expand_func( builds, expand_dev )
    builds = expand_func( builds, expand_tests )

    # Configure the builds.
    builds = [
        b for b in builds
        if all( f(b) for f in getattr(b, 'configure_funcs', []) )
    ]

    # Naming up to now.
    # origin/4.7 is also past 4.7.2-stable, so describing every ref would
    # give the private branch and the 4.7 branch the same suffix.
    version_labels: dict[str, str | None] = {}
    for build in builds:

        # buildtool = build.buildtool
        tc = build.toolchain
        ref = build.source_def.ref
        if ref == TRACY_REF:
            if ref not in version_labels:
                repo = pathlib.Path(build.source_def.url)
                version_labels[ref] = _describe_version(repo, ref) if repo.exists() else None
            version = version_labels[ref]
        else:
            version = ref.replace('/', '-')

        # A dev copy of the default variant keeps the name `dev_build`.
        # The other variants keep their label and gain a dev_build tag.
        variant = build.variant
        dev = getattr(build, 'dev_build', None)
        if variant == 'default' and dev:
            variant = None
        name_parts = [
            short_host(),
            # buildtool.name, this is always "scons" for godot.
            tc.name,
            tc.target_arch if tc.target_platform not in ['emscripten'] else None,
            godot_platforms[tc.target_platform] if tc.target_platform not in ['android', 'emscripten'] else None,
            build.target,
            variant,
            dev,
            getattr(build, 'tests', None),
            version,
        ]

        build.name = '.'.join(filter(None, name_parts))
        build.source_dir =  build.name

        build.script_parts += [show_stats]

    project.build_configs = { v.name:v for v in builds }
    return project


# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

# MARK: Mingw32
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __ _                  _______                                         │
# │ |  \/  (_)_ _  __ ___ __ _|__ /_  )                                        │
# │ | |\/| | | ' \/ _` \ V  V /|_ \/ /                                         │
# │ |_|  |_|_|_||_\__, |\_/\_/|___/___|                                        │
# │               |___/                                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯
# When mignw32 attempts to compile files that include the *translations.gen.h
# files it spits out this error
#
#   cc1plus.exe: out of memory allocating 536875007 bytes
#
# I personally see it manifest specifically when:
#   [ 72%] Compiling editor/editor_translation.cpp ...
# A quick and dirty way to solve this for now is to just delete the translations.
# The default language is english.

def delete_translations():
    """
    Delete translation files to avoid memory issues.
    """
    build:dict = {}
    # start_script

    # MARK: Delete Translations
    #[=========================[ Delete Translations ]=========================]
    console.rule("Removing Translations")
    fmt.h( ' '.join(os.listdir(build['source_path'] / 'doc/translations/') ) )
    for file in Path(build['source_path'] / 'doc/translations/').glob('*.po'):
        os.remove( file )


# MARK: SCons Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___  ___               ___         _      _                               │
# │ / __|/ __|___ _ _  ___ / __| __ _ _(_)_ __| |_                             │
# │ \__ \ (__/ _ \ ' \(_-< \__ \/ _| '_| | '_ \  _|                            │
# │ |___/\___\___/_||_/__/ |___/\__|_| |_| .__/\__|                            │
# │                                      |_|                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯
def check_scons():
    """
    Check if SCons can be run.
    """
    build:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: SCons Check
    #[=============================[ SCons Check ]=============================]
    ## FIXME scons clean also needs the platform set
    scons = buildtool

    # Figure out the build path
    if "build_dir" in scons.keys():
        scons['build_dir'] = project['path'] / build['source_dir'] / scons['build_dir']
    else:
        scons['build_dir'] = project['path'] / build['source_dir']

    build_dir = Path(scons['build_dir'])

    try: os.chdir(build_dir)
    except FileNotFoundError as fnf:
        fnf.add_note( f'\nMissing Folder {build_dir}' )
        fnf.add_note( f'\nProbably need to source the build first.' )
        raise fnf

    # requires SConstruct file existing in the current directory.
    if not (build_dir / "SConstruct").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"[red]Missing SConstruct in {build_dir}")
        raise fnf

def build_scons():
    """
    Execute the SCons build process.
    """
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    build:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: SCons Build
    #[=================================[ Build ]=================================]
    scons:dict = buildtool

    if config['ok'] and 'build' in build['verbs'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')

        with Timer(name='build') as timer, fmt.Section('Scons Build'):
            try: os.chdir( scons['build_dir'] )
            except FileNotFoundError as fnf:
                fnf.add_note( f'Missing Folder {scons['build_dir']}' )
                raise fnf

            # The Windows letter moves. Find the volume by label at build time.
            # A configured path is used as-is when that path is already there.
            def scons_cache_dir():
                configured = scons.get('cache_path')
                if configured and pathlib.Path(configured).exists():
                    return pathlib.Path(configured)
                label = scons.get('cache_volume')
                if not label or os.name != 'nt':
                    return None
                import ctypes
                kernel = ctypes.windll.kernel32
                name = ctypes.create_unicode_buffer(261)
                serial = ctypes.c_ulong()
                maxcomp = ctypes.c_ulong()
                flags = ctypes.c_ulong()
                fsname = ctypes.create_unicode_buffer(261)
                rel = scons.get('cache_relpath', 'godot/scons_cache')
                # SEM_FAILCRITICALERRORS. An empty reader must not pop a dialog.
                previous_mode = kernel.SetErrorMode(1)
                try:
                    found = _windows_cache_volume(kernel, name, serial, maxcomp, flags, fsname, label, rel)
                finally:
                    kernel.SetErrorMode(previous_mode)
                return found

            def _windows_cache_volume(kernel, name, serial, maxcomp, flags, fsname, label, rel):
                import ctypes
                import string
                for letter in string.ascii_uppercase:
                    root = f'{letter}:\\'
                    if kernel.GetDriveTypeW(root) == 1:
                        continue
                    if not kernel.GetVolumeInformationW(
                        root, name, len(name),
                        ctypes.byref(serial), ctypes.byref(maxcomp), ctypes.byref(flags),
                        fsname, len(fsname)):
                        continue
                    if name.value.casefold() != str(label).casefold():
                        continue
                    candidate = pathlib.Path(root) / rel
                    if candidate.is_dir():
                        return candidate
                return None

            cache_dir = scons_cache_dir()
            if cache_dir is not None:
                print(f'SCons cache: {cache_dir.as_posix()}')
                scons['build_vars'].append(f'cache_path={cache_dir.as_posix()}')
                scons['build_vars'].append(f'cache_limit={scons["cache_limit"]}')
            else:
                print('SCons cache: not connected')

            jobs = opts["jobs"]
            cmd_chunks = [
                "scons",
                "--clean -s" if 'clean' in opts['build_actions'] else None,
                f"-j {jobs}" if jobs > 0 else None,
                "verbose=yes" if opts["verbose"] else None,
            ]
            if "build_vars" in scons.keys():
                cmd_chunks += scons["build_vars"]

            build_command: str = " ".join(filter(None, cmd_chunks))

            # FIXME  I found that if i dont clean the repository then files are unfortunately wrong.
            #  However if I am working on something then this is an unnecessary step most of the time.
            #  [REASON] This is because the clean command depends on the other options
            stream_command(build_command, dry=opts['dry'])

        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()

def clean_scons():
    """
    Clean the SCons build artifacts.
    """
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    from subprocess import CalledProcessError

    #[=================================[ Clean ]=================================]
    if config['ok'] and 'clean' in opts['build_actions']:
        console.set_window_title(f'Clean - {build['name']}')

        with Timer(name='clean', push=False) as timer, fmt.Section("SCons Clean"):
            try:
                proc = stream_command( "scons --clean -s" , dry=opts['dry'])
                # Change status depending on the truthiness of returnvalue
                # where False is Success and True is Failure.
                timer.status = TaskStatus.FAILED if proc.returncode else TaskStatus.COMPLETED
            except CalledProcessError as e:
                # FIXME should this be more generic and handled elsewhere?
                print( '[red]subprocess error')
                print( f'[red]{e}' )
                timer.status = TaskStatus.FAILED
        stats['clean'] = timer.get_dict()
        config['ok'] = timer.ok()


def _host_can_run(host: str, platform_name: str, arch: str) -> bool:
    """True when this machine can execute that Godot binary."""
    import platform
    machine = platform.machine().lower()
    host_arch = {
        'amd64': 'x86_64',
        'x86_64': 'x86_64',
        'x86': 'x86_32',
        'i686': 'x86_32',
        'arm64': 'arm64',
        'aarch64': 'arm64',
    }.get(machine, godot_arch.get(machine, machine))

    if host == 'Windows' and platform_name == 'windows':
        if arch == host_arch:
            return True
        if host_arch == 'x86_64' and arch == 'x86_32':
            return True
        if host_arch == 'arm64' and arch in ('x86_64', 'x86_32'):
            return True
    if host == 'Darwin' and platform_name == 'macos':
        if arch == host_arch:
            return True
        if host_arch == 'arm64' and arch == 'x86_64':
            return True
    if host == 'Linux' and platform_name in ('linux', 'linuxbsd'):
        return arch == host_arch
    return False


def test_scons():
    """
    Test a tests=yes binary the way godot-build tests it by hand:
    version check, Tracy version and defines, the [Profiling] doctests, then
    on profiler=tracy builds a fibers capture with zone counts, a silenced run
    and a capture toggle run. Logs and summary.json go to
    <build_dir>/test-logs/<short-commit>/.
    """
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    buildtool:dict = {}
    project:dict = {}
    toolchain:dict = {}
    # start_script

    if config['ok'] and 'test' in opts['build_actions']:
        console.set_window_title(f'Test - {build["name"]}')

        test_summary = None
        with Timer(name='test') as timer, fmt.Section('Test'):
            from subprocess import CalledProcessError

            if not build.get('can_test'):
                host = toolchain.get('host', '')
                fmt.h(f'Skip test: {host} cannot run this binary')
            else:
                def scons_opt(name):
                    value = None
                    for item in buildtool.get('build_vars', []):
                        key, sep, val = str(item).partition('=')
                        if sep and key == name:
                            value = val
                    return value

                # Same suffix SConstruct builds, including detect.py's .llvm prefix.
                platform_name = scons_opt('platform') or ''
                if platform_name in ('linux', 'bsd'):
                    platform_name = 'linuxbsd'
                target = scons_opt('target') or build.get('target', '')
                arch = scons_opt('arch') or ''
                parts = ['godot', platform_name, target]
                if scons_opt('dev_build') == 'yes':
                    parts.append('dev')
                if scons_opt('precision') == 'double':
                    parts.append('double')
                parts.append(arch)
                if scons_opt('threads') == 'no':
                    parts.append('nothreads')
                extra = scons_opt('extra_suffix') or ''
                if scons_opt('use_llvm') == 'yes':
                    extra = f'llvm.{extra}' if extra else 'llvm'
                if extra:
                    parts.append(extra)

                stem = '.'.join(part for part in parts if part)
                build_dir = buildtool.get('build_dir') or (project['path'] / build['source_dir'])
                bin_dir = Path(build_dir) / 'bin'
                if platform_name == 'windows':
                    exe = bin_dir / f'{stem}.console.exe'
                    if not exe.is_file():
                        exe = bin_dir / f'{stem}.exe'
                else:
                    exe = bin_dir / stem

                if not exe.is_file():
                    fmt.h(f'Missing test binary {exe.as_posix()}')
                    timer.status = TaskStatus.FAILED
                else:
                    # Helpers are nested defs: the generated script keeps only the body
                    # after `# start_script`, so module-level names are not there.
                    import csv
                    import hashlib
                    import json
                    import re
                    import shutil
                    import socket
                    import subprocess
                    import sys
                    import time

                    tt = dict(build.get('tracy_test') or {})
                    dry = bool(opts['dry'])
                    source_dir = Path(build_dir)
                    run_timeout = int(tt.get('timeout') or 300)
                    is_tracy = scons_opt('profiler') == 'tracy'
                    on_linux = sys.platform.startswith('linux')
                    stages = {}
                    order = []

                    def stage(name):
                        rec = {'status': 'pass'}
                        stages[name] = rec
                        order.append(name)
                        return rec

                    def skip(rec, why):
                        rec['status'] = 'skip'
                        rec['reason'] = why
                        fmt.h(f'Skip: {why}')

                    def fail(rec, why):
                        rec['status'] = 'fail'
                        rec.setdefault('failures', []).append(why)
                        fmt.h(f'FAIL: {why}')

                    def tail(text, n=20):
                        for line in text.rstrip().splitlines()[-n:]:
                            print(f'    {line}')

                    def run(name, args, timeout, echo=20):
                        # Like stream_command: print the command, launch nothing when dry.
                        args = [str(a) for a in args]
                        print(f'  $ {args}')
                        if dry:
                            return None
                        started = time.monotonic()
                        try:
                            proc = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                                                  errors='backslashreplace', timeout=timeout, stdin=subprocess.DEVNULL)
                            rc, out, err = proc.returncode, proc.stdout, proc.stderr
                        except subprocess.TimeoutExpired as e:
                            out = e.stdout.decode('utf-8', 'backslashreplace') if isinstance(e.stdout, bytes) else (e.stdout or '')
                            err = e.stderr.decode('utf-8', 'backslashreplace') if isinstance(e.stderr, bytes) else (e.stderr or '')
                            rc = f'timeout after {timeout} s'
                        except OSError as e:
                            rc, out, err = f'launch error: {e}', '', ''
                        secs = round(time.monotonic() - started, 3)
                        (logdir / f'{name}.cmd').write_text(subprocess.list2cmdline(args) + '\n', encoding='utf-8')
                        (logdir / f'{name}.stdout.log').write_text(out, encoding='utf-8')
                        (logdir / f'{name}.stderr.log').write_text(err, encoding='utf-8')
                        if echo:
                            tail(out + err, echo)
                        return {'rc': rc, 'out': out, 'err': err, 'secs': secs}

                    def git_head():
                        if dry:
                            return None
                        try:
                            proc = subprocess.run(['git', '-C', str(source_dir), 'rev-parse', 'HEAD'],
                                                  capture_output=True, text=True, timeout=30)
                        except (OSError, subprocess.SubprocessError):
                            return None
                        head = proc.stdout.strip()
                        return head if proc.returncode == 0 and re.fullmatch(r'[0-9a-f]{40}', head) else None

                    # Same parsing as _tracy_version_at, which the script cannot import.
                    def tracy_version_at(path):
                        try:
                            text = (Path(path) / 'public/common/TracyVersion.hpp').read_text()
                        except OSError:
                            return None
                        parts = [re.search(rf'{name}\s*=\s*(\d+)', text) for name in ('Major', 'Minor', 'Patch')]
                        if not all(parts):
                            return None
                        return '.'.join(m.group(1) for m in parts)

                    def tool(key):
                        value = tt.get(key)
                        return Path(value) if value and Path(value).is_file() else None

                    def port_busy(address, port):
                        try:
                            with socket.create_connection((address, int(port)), timeout=1):
                                return True
                        except OSError:
                            return False

                    def capture_run(rec, name, harness, unsilence):
                        # tracy-capture in the background, then the engine with a subprocess timeout.
                        trace = logdir / f'{name}.tracy'
                        cap_cmd = [str(tool('capture')), '-o', str(trace), '-a', tt['address'], '-p', tt['port'], '-f']
                        eng_cmd = [str(exe), '--headless'] + (['--tracy'] if unsilence else []) + [
                            '--script', str(harness), '--tracy-features', tt['features']]
                        rec['capture_cmd'] = subprocess.list2cmdline(cap_cmd)
                        rec['engine_cmd'] = subprocess.list2cmdline(eng_cmd)
                        print(f'  $ {cap_cmd} &')
                        if dry:
                            print(f'  $ {eng_cmd}')
                            rec['status'] = 'dry'
                            return None, ''
                        if port_busy(tt['address'], tt['port']):
                            fail(rec, f"{tt['address']}:{tt['port']} already has a Tracy client; another engine is running")
                            return None, ''
                        started = time.monotonic()
                        cap_log_path = logdir / f'{name}-capture.log'
                        with open(cap_log_path, 'w', encoding='utf-8') as cap_log:
                            cap = subprocess.Popen(cap_cmd, stdout=cap_log, stderr=subprocess.STDOUT,
                                                   stdin=subprocess.DEVNULL)
                            time.sleep(2)   # the manual flow starts the capture 2 s ahead
                            eng = run(f'{name}-engine', eng_cmd, run_timeout)
                            try:
                                cap_rc = cap.wait(timeout=60)
                            except subprocess.TimeoutExpired:
                                cap.terminate()
                                try:
                                    cap.wait(timeout=10)
                                except subprocess.TimeoutExpired:
                                    cap.kill()
                                    cap.wait()
                                cap_rc = 'timeout: capture still running 60 s after the engine exited'
                        rec['secs'] = round(time.monotonic() - started, 3)
                        cap_text = cap_log_path.read_text(encoding='utf-8', errors='backslashreplace')
                        fmt.h(f'{name} capture:')
                        tail(cap_text, 12)
                        rec['engine_rc'] = eng['rc']
                        rec['capture_rc'] = cap_rc
                        m = re.search(r'^Zones:\s*([\d,]+)', cap_text, re.M)
                        rec['capture_zones'] = int(m.group(1).replace(',', '')) if m else None
                        m = re.search(r'^Frames:\s*([\d,]+)', cap_text, re.M)
                        rec['capture_frames'] = int(m.group(1).replace(',', '')) if m else None
                        if eng['rc'] != 0:
                            fail(rec, f'engine exited {eng["rc"]}')
                        if cap_rc != 0:
                            fail(rec, f'tracy-capture exited {cap_rc}')
                        for label, text in (('engine', eng['out'] + eng['err']), ('capture', cap_text)):
                            if 'Instrumentation failure' in text:
                                fail(rec, f'"Instrumentation failure" in {label} output')
                        size = trace.stat().st_size if trace.is_file() else 0
                        rec['trace'] = trace.as_posix()
                        rec['trace_bytes'] = size
                        if not size:
                            fail(rec, f'{trace.as_posix()} is missing or empty')
                            return None, eng['out']
                        return trace, eng['out']

                    def zone_csv(name, trace):
                        # tracy-csvexport: name,src_file,src_line,total_ns,total_perc,counts,mean,min,max,std
                        res = run(f'{name}-csvexport', [tool('csvexport'), trace], 120, echo=0)
                        if res is None or res['rc'] != 0:
                            return None
                        csv_path = logdir / f'{name}-zones.csv'
                        csv_path.write_text(res['out'], encoding='utf-8')
                        rows = list(csv.reader(res['out'].splitlines()))[1:]
                        total = 0
                        unknown = 0
                        names = set()
                        for row in rows:
                            if len(row) < 10:
                                continue
                            zname = ','.join(row[:-9])
                            count = int(row[-5])
                            total += count
                            names.add(zname)
                            if zname == '???':
                                unknown += count
                        return {'zones_csv': csv_path.as_posix(), 'zones': total,
                                'distinct_zone_names': len(names), 'unknown_zones': unknown}

                    def ensure_analyzer():
                        # The libTracyServer analyser from the silent-client run, built once.
                        binary = Path(tt.get('analyzer') or '')
                        if binary.is_file():
                            return binary, None
                        src = Path(tt.get('analyzer_src') or '')
                        tools_dir = Path(tt.get('tools_path') or '') / 'csvexport'
                        libs = [tools_dir / 'libTracyServer.a',
                                tools_dir / '_deps/capstone-build/libcapstone.a',
                                tools_dir / '_deps/zstd-build/lib/libzstd.a']
                        cxx = shutil.which('g++')
                        missing = [p.as_posix() for p in [src, *libs] if not p.is_file()]
                        if not cxx or missing or not tt.get('analyzer'):
                            return None, f'cannot build the analyser (g++={cxx}, missing {missing})'
                        # Reuse the include paths CMake gave csvexport, so the headers match the library.
                        includes = []
                        try:
                            ninja = (tools_dir / 'build.ninja').read_text(encoding='utf-8')
                            m = re.search(r'csvexport\.cpp\.o:.*?\n(?:  .*\n)*?  INCLUDES = (.*)\n', ninja)
                            includes = m.group(1).split() if m else []
                        except OSError:
                            pass
                        if not includes:
                            profiler = Path(tt.get('profiler_path') or '')
                            includes = [f'-I{profiler / "public/common"}', f'-I{profiler / "server"}']
                        binary.parent.mkdir(parents=True, exist_ok=True)
                        partial = binary.with_name(binary.name + '.partial')
                        cmd = [cxx, '-O2', '-std=gnu++20', '-flto=auto', *includes, '-o', partial, src,
                               *libs, '-lpthread']
                        res = run('analyzer-build', cmd, 900, echo=10)
                        if res is None:
                            return None, 'dry'
                        if res['rc'] != 0 or not partial.is_file():
                            return None, f'analyser build exited {res["rc"]}'
                        partial.replace(binary)
                        return binary, None

                    def analyse(name, trace):
                        binary, why = ensure_analyzer()
                        if binary is None:
                            return None, why
                        res = run(f'{name}-analysis', [binary, trace], 300, echo=0)
                        if res is None:
                            return None, 'dry'
                        (logdir / f'{name}-analysis.txt').write_text(res['out'], encoding='utf-8')
                        if res['rc'] != 0:
                            return None, f'analyser exited {res["rc"]}'
                        text = res['out']
                        info = {'analysis': (logdir / f'{name}-analysis.txt').as_posix()}
                        m = re.search(r'^first time ([\d.]+) s', text, re.M)
                        info['first_time'] = float(m.group(1)) if m else None
                        frames = [(int(c), float(last) if last else None) for c, last in
                                  re.findall(r"^frame set .*?: (\d+) frames(?: first [\d.]+ last ([\d.]+))?", text, re.M)]
                        info['frames'] = sum(c for c, _ in frames)
                        info['last_frame'] = max((last for _, last in frames if last is not None), default=None)
                        m = re.search(r'^zonesCnt\(worker\)=(\d+).*?(?: first ([\d.]+) last ([\d.]+))?$', text, re.M)
                        info['zones'] = int(m.group(1)) if m else None
                        info['first_zone'] = float(m.group(2)) if m and m.group(2) else None
                        info['last_zone'] = float(m.group(3)) if m and m.group(3) else None
                        info['message_list'] = [(float(t), int(srcid), msg) for t, srcid, msg in
                                                re.findall(r"^  MSG ([\d.]+) .*? src=(\d+) sev=\d+ '(.*)'$", text, re.M)]
                        m = re.search(r'^messages: (\d+)', text, re.M)
                        info['messages'] = int(m.group(1)) if m else None
                        plots = [(ptype, pname, float(last) if last else None) for ptype, pname, last in
                                 re.findall(r"^  PLOT type=(\w+) name='(.*?)' points=\d+(?: first [\d.]+ last ([\d.]+))?", text, re.M)]
                        info['plots'] = len(plots)
                        info['engine_plots'] = sum(1 for ptype, _, _ in plots if ptype != 'SysTime')
                        info['plot_list'] = plots
                        return info, None

                    def public(info):
                        return {k: v for k, v in (info or {}).items() if k not in ('message_list', 'plot_list')}

                    head = git_head()
                    short = head[:10] if head else ('dry' if dry else 'unknown')
                    log_root = Path(tt['log_root']) if tt.get('log_root') else source_dir / 'test-logs'
                    logdir = log_root / short
                    if not dry:
                        logdir.mkdir(parents=True, exist_ok=True)
                    fmt.h(f'Test binary: {exe.as_posix()}')
                    fmt.h(f'Test logs: {logdir.as_posix()}')
                    flow_started = time.monotonic()

                    try:
                        # 1. Version: the binary must carry the source's commit.
                        rec = stage('version')
                        fmt.h('Version check')
                        res = run('version', [exe, '--headless', '--version'], 60)
                        if res is None:
                            rec['status'] = 'dry'
                        else:
                            version = (res['out'] or res['err']).strip().splitlines()
                            rec['output'] = version[-1] if version else ''
                            rec['source_commit'] = head
                            hashes = re.findall(r'\b([0-9a-f]{7,40})\b', rec['output'])
                            if res['rc'] != 0:
                                fail(rec, f'--version exited {res["rc"]}')
                            elif not head:
                                fail(rec, f'cannot read HEAD of {source_dir.as_posix()}')
                            elif not any(head.startswith(h) for h in hashes):
                                fail(rec, f'version {rec["output"]!r} does not name commit {head[:10]}')
                            else:
                                fmt.h(f'{rec["output"]} matches {head[:10]}')

                        # 2. Tracy version and the generated profiling defines.
                        rec = stage('tracy_defines')
                        fmt.h('Tracy version and defines')
                        if is_tracy:
                            profiler_path = scons_opt('profiler_path') or tt.get('profiler_path')
                            found = tracy_version_at(profiler_path) if profiler_path else None
                            rec['tracy_path'] = profiler_path
                            rec['tracy_version'] = found
                            if found != tt.get('version'):
                                fail(rec, f'expected Tracy {tt.get("version")} at {profiler_path}, found {found}')
                        gen_h = source_dir / 'core/profiling/profiling.gen.h'
                        rec['gen_h'] = gen_h.as_posix()
                        if gen_h.is_file():
                            data = gen_h.read_bytes()
                            rec['gen_h_sha256'] = hashlib.sha256(data).hexdigest()
                            defines = {}
                            for dname, dvalue in re.findall(
                                    r'^#define\s+((?:TRACY|GODOT_TRACY|GODOT_PROFILER|GODOT_USE_TRACY)\w*)[ \t]*(.*)$',
                                    data.decode('utf-8', 'replace'), re.M):
                                defines[dname] = dvalue.strip()
                            rec['defines'] = defines
                            fmt.h(f'{len(defines)} defines, sha256 {rec["gen_h_sha256"][:16]}')
                            if is_tracy:
                                if 'TRACY_ENABLE' not in defines or 'GODOT_USE_TRACY' not in defines:
                                    fail(rec, 'profiler=tracy build but profiling.gen.h does not enable Tracy')
                                pinned = [defines.get(f'GODOT_TRACY_PINNED_VERSION_{p}') for p in ('MAJOR', 'MINOR', 'PATCH')]
                                if all(pinned) and '.'.join(pinned) != tt.get('version'):
                                    fail(rec, f'profiling.gen.h pins Tracy {".".join(pinned)}')
                        elif dry:
                            rec['status'] = 'dry'
                        elif is_tracy:
                            fail(rec, f'missing {gen_h.as_posix()}')
                        else:
                            skip(rec, f'no {gen_h.as_posix()} (not a profiler build)')

                        # 3. [Profiling] doctests.
                        rec = stage('doctest')
                        fmt.h('Doctests [Profiling]')
                        res = run('doctest', [exe, '--headless', '--test', '--test-case=*[Profiling]*'], 900, echo=12)
                        if res is None:
                            rec['status'] = 'dry'
                        else:
                            rec['rc'] = res['rc']
                            rec['secs'] = res['secs']
                            text = res['out'] + res['err']
                            m = re.search(r'test cases:\s*(\d+)\s*\|\s*(\d+) passed\s*\|\s*(\d+) failed\s*\|\s*(?:(\d+) skipped)?', text)
                            if m:
                                rec['test_cases'] = {'total': int(m.group(1)), 'passed': int(m.group(2)),
                                                     'failed': int(m.group(3)), 'skipped': int(m.group(4) or 0)}
                            m = re.search(r'assertions:\s*(\d+)\s*\|\s*(\d+) passed\s*\|\s*(\d+) failed\s*\|\s*(?:(\d+) skipped)?', text)
                            if m:
                                rec['assertions'] = {'total': int(m.group(1)), 'passed': int(m.group(2)),
                                                     'failed': int(m.group(3)), 'skipped': int(m.group(4) or 0)}
                            if res['rc'] != 0:
                                fail(rec, f'doctest exited {res["rc"]}')
                            if 'test_cases' not in rec or 'assertions' not in rec:
                                fail(rec, 'no doctest summary in the output')
                            elif rec['test_cases']['failed'] or rec['assertions']['failed']:
                                fail(rec, 'doctest reported failures')
                            elif not rec['test_cases']['total']:
                                fail(rec, 'no test case matched *[Profiling]*')

                        # Tracy capture stages share these gates.
                        tracy_gate = None
                        if not is_tracy:
                            tracy_gate = 'not a profiler=tracy build'
                        elif not on_linux:
                            tracy_gate = f'Tracy capture stages run on Linux only (host {sys.platform})'
                        elif not tool('capture'):
                            tracy_gate = f'no tracy-capture at {tt.get("capture")}'
                        silent_client = None
                        if tracy_gate is None and not dry:
                            # The silent-client feature adds the --tracy launch flag.
                            res = run('help', [exe, '--headless', '--help'], 60, echo=0)
                            plain = re.sub(r'\x1b\[[0-9;]*m', '', res['out'] + res['err'])
                            silent_client = bool(re.search(r'^\s*--tracy\s', plain, re.M))
                            fmt.h(f'silent-client support (--tracy in --help): {silent_client}')

                        # 4. Fibers capture.
                        rec = stage('fibers_capture')
                        fmt.h('Fibers capture')
                        fibers_trace = None
                        if tracy_gate:
                            skip(rec, tracy_gate)
                        elif not tool('fibers_gd'):
                            skip(rec, f'no fibers harness at {tt.get("fibers_gd")}')
                        else:
                            fibers_trace, _ = capture_run(rec, 'fibers', tool('fibers_gd'),
                                                          unsilence=silent_client or dry)
                            if rec['status'] != 'pass':
                                fibers_trace = None

                        # 5. Counts from the fibers trace.
                        rec = stage('counts')
                        fmt.h('Zone, message, plot and frame counts')
                        if stages['fibers_capture']['status'] == 'dry':
                            rec['status'] = 'dry'
                            print(f"  $ {[tt.get('csvexport'), str(logdir / 'fibers.tracy')]}")
                        elif fibers_trace is None:
                            skip(rec, 'no fibers trace')
                        elif not tool('csvexport'):
                            skip(rec, f'no tracy-csvexport at {tt.get("csvexport")}')
                        else:
                            counts = zone_csv('fibers', fibers_trace)
                            if counts is None:
                                fail(rec, 'tracy-csvexport failed')
                            else:
                                rec.update(counts)
                                info, why = analyse('fibers', fibers_trace)
                                if info is None:
                                    rec['analyser'] = f'skipped: {why}'
                                    fmt.h(f'No message/plot/frame counts: {why}')
                                else:
                                    rec.update({k: v for k, v in public(info).items() if k != 'zones'})
                                    rec['analyser_zones'] = info['zones']
                                fmt.h(f"zones {rec['zones']}, distinct {rec['distinct_zone_names']}, "
                                      f"??? {rec['unknown_zones']}, messages {rec.get('messages')}, "
                                      f"plots {rec.get('plots')}, frames {rec.get('frames')}")
                                if not rec['zones']:
                                    fail(rec, 'fibers trace has 0 zones')
                                if rec['unknown_zones']:
                                    fail(rec, f"fibers trace has {rec['unknown_zones']} ??? zones")

                        # 6. Silenced run: launched without --tracy, the engine sends nothing.
                        rec = stage('silenced')
                        fmt.h('Silenced run')
                        if tracy_gate:
                            skip(rec, tracy_gate)
                        elif silent_client is False:
                            skip(rec, 'build has no silent-client support (--tracy missing from --help)')
                        elif not tool('fibers_gd'):
                            skip(rec, f'no fibers harness at {tt.get("fibers_gd")}')
                        else:
                            trace, _ = capture_run(rec, 'silenced', tool('fibers_gd'), unsilence=False)
                            if trace is not None and rec['status'] == 'pass':
                                info, why = analyse('silenced', trace)
                                if info is None:
                                    skip(rec, f'cannot inspect the trace: {why}')
                                else:
                                    rec.update(public(info))
                                    if rec['capture_zones']:
                                        fail(rec, f"tracy-capture reports {rec['capture_zones']} zones")
                                    if info['zones']:
                                        fail(rec, f"{info['zones']} zones while silenced")
                                    if info['messages']:
                                        fail(rec, f"{info['messages']} messages while silenced")
                                    if info['engine_plots']:
                                        fail(rec, f"{info['engine_plots']} engine plots while silenced")
                                    # Allowed: Tracy's CPU-usage plot (SysTime) and the 3 frames the
                                    # 0.14.1 server adds at handshake and connect, all at or before
                                    # the client's first time.
                                    first = info['first_time']
                                    if info['frames'] > 3 or (info['frames'] and first is not None
                                                              and info['last_frame'] > first + 1e-6):
                                        fail(rec, f"{info['frames']} frames, beyond the 3 server frames")

                        # 7. Toggle run: Profiler.set_capture_enabled on at frame 100, off at 200.
                        rec = stage('toggle')
                        fmt.h('Toggle run')
                        if tracy_gate:
                            skip(rec, tracy_gate)
                        elif silent_client is False:
                            skip(rec, 'build has no silent-client support (--tracy missing from --help)')
                        elif not tool('toggle_gd'):
                            skip(rec, f'no toggle harness at {tt.get("toggle_gd")}')
                        else:
                            trace, eng_out = capture_run(rec, 'toggle', tool('toggle_gd'), unsilence=False)
                            if trace is not None and rec['status'] == 'pass':
                                for line in ('UNSILENCE request at frame 100', 'SILENCE request at frame 200',
                                             'END at frame 300'):
                                    if line not in eng_out:
                                        fail(rec, f'engine output lacks {line!r}')
                                info, why = analyse('toggle', trace)
                                if info is None:
                                    skip(rec, f'cannot inspect the trace: {why}')
                                else:
                                    rec.update(public(info))
                                    msgs = info['message_list']
                                    starts = [t for t, _, msg in msgs if msg == 'Godot Tracy capture started']
                                    stops = [t for t, _, msg in msgs if msg == 'Godot Tracy capture stopped']
                                    rec['capture_started_at'] = starts[0] if starts else None
                                    rec['capture_stopped_at'] = stops[-1] if stops else None
                                    if not starts:
                                        fail(rec, "no 'Godot Tracy capture started' message")
                                    if not stops:
                                        fail(rec, "no 'Godot Tracy capture stopped' message")
                                    if not info['zones']:
                                        fail(rec, 'no zones between the boundaries')
                                    if stops:
                                        stop_t = stops[-1]
                                        late_msgs = [msg for t, _, msg in msgs if t > stop_t]
                                        rec['messages_after_stop'] = len(late_msgs)
                                        rec['zones_after_stop'] = int(info['last_zone'] is not None
                                                                      and info['last_zone'] > stop_t)
                                        # Plot points after the stop are recorded, not judged.
                                        rec['engine_plots_after_stop'] = sum(
                                            1 for ptype, _, last in info['plot_list']
                                            if ptype != 'SysTime' and last is not None and last > stop_t)
                                        if late_msgs:
                                            fail(rec, f'{len(late_msgs)} messages after capture stopped: {late_msgs[:3]}')
                                        if rec['zones_after_stop']:
                                            fail(rec, f"a zone starts at {info['last_zone']}, after the stop at {stop_t}")
                                    if starts:
                                        rec['engine_messages_before_start'] = sum(
                                            1 for t, srcid, _ in msgs if t < starts[0] and srcid == 0)
                    except (OSError, subprocess.SubprocessError) as e:
                        rec = stages.get('error') or stage('error')
                        fail(rec, f'{type(e).__name__}: {e}')

                    failed = [n for n in order if stages[n]['status'] == 'fail']
                    test_summary = {
                        'ok': not failed,
                        'binary': exe.as_posix(),
                        'commit': head,
                        'log_dir': logdir.as_posix(),
                        'secs': round(time.monotonic() - flow_started, 3),
                        'stages': stages,
                    }
                    if not dry:
                        (logdir / 'summary.json').write_text(json.dumps(test_summary, indent=2, default=str),
                                                             encoding='utf-8')
                    for n in order:
                        fmt.h(f"{n}: {stages[n]['status']}")
                    timer.status = TaskStatus.FAILED if failed else TaskStatus.COMPLETED

        stats['test'] = timer.get_dict()
        if test_summary is not None:
            stats['test']['summary'] = test_summary
        config['ok'] = timer.ok() and config['ok']

# MARK: ToolChains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ _____         _  ___ _         _                                           │
# │|_   _|__  ___| |/ __| |_  __ _(_)_ _  ___                                  │
# │  | |/ _ \/ _ \ | (__| ' \/ _` | | ' \(_-<                                  │
# │  |_|\___/\___/_|\___|_||_\__,_|_|_||_/__/                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def configure_toolchain(config:SimpleNamespace) -> list[SimpleNamespace]:
    """
    Configure the toolchain settings.
    :param config:
    :return:
    """
    if config.toolchain.name == 'android':
        tc = config.toolchain
        ndk_version = '28.1.13356709'
        setattr(tc, 'packages', {
            'platform-tools':'',
            "build-tools":"35.0.0",
            "platforms":"android-35",
            "cmdline-tools":"latest",
            "cmake":"3.10.2.4988404",
            'ndk':ndk_version,
        })
        setattr(tc, 'ndk_path', f'{tc.sdk_path}\\ndk\\{ndk_version}')
        setattr(tc, 'api_level', '35')

    return [config]

# MARK: BuildTools
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___      _ _    _ _____         _                                         │
# │ | _ )_  _(_) |__| |_   _|__  ___| |___                                     │
# │ | _ \ || | | / _` | | |/ _ \/ _ \ (_-<                                     │
# │ |___/\_,_|_|_\__,_| |_|\___/\___/_/__/                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Scons
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                                                                       │
# │ / __| __ ___ _ _  ___                                                      │
# │ \__ \/ _/ _ \ ' \(_-<                                                      │
# │ |___/\__\___/_||_/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_scons( config:SimpleNamespace ) -> list[SimpleNamespace]:
    """
    Expand SCons configuration into multiple targets.
    :param config:
    :return:
    """
    # Split the compile up into individual targets
    configs_out = []
    for target in ["template_release", "template_debug", "editor"]:
        cfg = copy.deepcopy(config)
        setattr(cfg, 'target', target)

        scons = cfg.buildtool
        scons.target = target
        scons.build_vars.append(f'target={target}')

        configs_out.append( cfg )

    return configs_out

def configure_scons( config:SimpleNamespace ) -> bool:
    """
    Configure SCons build variables.
    :param config:
    :return:
    """
    config.verbs += ['build', 'clean']
    config.script_parts +=  [check_scons, clean_scons, build_scons]

    tc = config.toolchain
    scons = config.buildtool
    scons.build_dir = ''

    # == Build Cache ==
    # Windows resolves cache_volume at build time because the letter changes.
    # Darwin mounts that same volume at a stable /Volumes path.
    match tc.host:
        case 'Windows':
            setattr(scons, 'cache_volume', 'Cache')
            setattr(scons, 'cache_relpath', 'godot/scons_cache')
            setattr(scons, 'cache_limit', 100)
        case 'Darwin':
            setattr(scons, 'cache_path', Path("/Volumes/Cache/godot/scons_cache"))
            setattr(scons, 'cache_limit', 100)

    # == Default Options ==
    scons.build_vars += [
        "verbose=yes",
        "compiledb=yes",
        "debug_symbols=yes",
        "separate_debug_symbols=yes",
        f"platform={godot_platforms[tc.target_platform]}",
        f"arch={godot_arch[tc.target_arch]}",
    ]

    match godot_platforms[tc.target_platform]:
        case 'windows':
            scons.build_vars.append('winrt=no')
            scons.build_vars.append('accesskit=no')
            scons.build_vars.append('d3d12=no')
            scons.build_vars.append('angle=no')
        case 'macos':
            scons.build_vars.append('accesskit=no')
            scons.build_vars.append('angle=no')
            scons.build_vars.append('generate_bundle=yes')
        case 'ios':
            # TODO consider supporting simulator builds
            scons.build_vars.append('generate_bundled=yes')
            if tc.host_arch != tc.target_arch:
                return False

    match tc.name:
        case 'msvc' | 'appleclang':
            pass
        case 'emscripten':
            # emscripten builds appear to be broken
            return False
        case 'android':
            ndk_version = '28.1.13356709'
            setattr(tc, 'packages', {
                'platform-tools':'',
                "build-tools":"35.0.0",
                "platforms":"android-35",
                "cmdline-tools":"latest",
                "cmake":"3.10.2.4988404",
                'ndk':ndk_version,
            })
            setattr(tc, 'ndk_path', f'{tc.sdk_path}\\ndk\\{ndk_version}')
            setattr(tc, 'api_level', '35')
        case "llvm":
            if config.arch != 'x86_64': return False
            scons.build_vars.append("use_llvm=yes")

        case "llvm-mingw":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")
            scons.build_vars.append(f"mingw_prefix={tc.sysroot.as_posix()}")
            if config.arch == 'armv7':
                # ERROR: In file included from thirdparty\misc\r128.c:2:
                # thirdparty\misc/r128.h:674:11: error: call to undeclared function '_arm_umull';
                # ISO C99 and later do not support implicit function declarations
                # [-Wimplicit-function-declaration]
                #   674 |    return _arm_umull(a, b);
                #       |           ^
                # 1 error generated.
                return False

        case "mingw64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append(f"mingw_prefix={tc.sysroot.as_posix()}")

        case "msys2-clang64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")

        case "msys2-ucrt64" | "msys2-mingw32" | "msys2-mingw64":
            scons.build_vars.append("use_mingw=yes")

        case _:
            return False

    if getattr(config, 'tests', None):
        config.can_test = _host_can_run(
            tc.host,
            godot_platforms[tc.target_platform],
            godot_arch[tc.target_arch],
        )
        config.verbs.append('test')
        config.tracy_test = dict(TRACY_TEST)
        config.script_parts.append(test_scons)

    return True

# def config_tracy_dbg( cfg:SimpleNamespace ) -> bool:
#     cfg.source_dir.append( 'tracy' )
#     cfg.scons['build_vars'].append('debug_symbols=yes')
#     cfg.scons['build_vars'].append('separate_debug_symbols=yes')
#     cfg.scons['build_vars'].append('extra_suffix=tracy.dbg')
#     return True

# MARK: Variant Config
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _          _      ___           __ _                        │
# │ \ \ / /_ _ _ _(_)__ _ _ _| |_   / __|___ _ _  / _(_)__ _                   │
# │  \ V / _` | '_| / _` | ' \  _| | (__/ _ \ ' \|  _| / _` |                  │
# │   \_/\__,_|_| |_\__,_|_||_\__|  \___\___/_||_|_| |_\__, |                  │
# │                                                    |___/                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

def config_minim( cfg:SimpleNamespace ) -> bool:
    """
    Configure a minimum build profile.
    :param cfg:
    :return:
    """
    cfg.buildtool.build_profile = 'minimum'
    cfg.buildtool.build_vars.append('extra_suffix=min')
    return True


# SConstruct BoolVariables. tracy_memory is yes here because
# profiler_track_memory=yes also defines TRACY_MEMORY_ENABLED.
_TRACY_FEATURES = (
    ("tracy_zones", "yes"),
    ("tracy_plots", "yes"),
    ("tracy_messages", "yes"),
    ("tracy_memory", "yes"),
    ("tracy_locks", "yes"),
    ("tracy_gpu", "yes"),
    ("tracy_gdscript_zones", "no"),
    ("tracy_frames", "yes"),
    ("tracy_frame_images", "no"),
)


def _append_tracy_features( scons ) -> None:
    for name, value in _TRACY_FEATURES:
        scons.build_vars.append(f"{name}={value}")


def _tracy_version_at( path:str ) -> str | None:
    """
    Read the Tracy version from public/common/TracyVersion.hpp under path.
    :return: The version as 'major.minor.patch', or None if it can't be read.
    """
    header = pathlib.Path(path) / 'public/common/TracyVersion.hpp'
    try:
        text = header.read_text()
    except OSError:
        return None
    parts = [re.search(rf'{name}\s*=\s*(\d+)', text) for name in ('Major', 'Minor', 'Patch')]
    if not all(parts):
        return None
    return '.'.join(m.group(1) for m in parts)


def config_tracy( cfg:SimpleNamespace ) -> bool:
    """
    Configure build with Tracy profiler, linked into the engine.
    :param cfg:
    :return:
    """
    # This branch lives only in godot-private. Upstream refs do not get it.
    if cfg.source_def.ref != TRACY_REF:
        return False
    scons = cfg.buildtool

    # Enable the tracy profiler.
    scons.build_vars.append("profiler=tracy")

    # profiler_path: Path to the Profiler framework. Only tracy and perfetto are supported at the moment.
    found = _tracy_version_at(TRACY_PROFILER_PATH)
    if found != TRACY_VERSION:
        print(f"Skipping tracy build: expected Tracy {TRACY_VERSION} at {TRACY_PROFILER_PATH}, found {found}")
        return False
    scons.build_vars.append(f"profiler_path={TRACY_PROFILER_PATH}")

    # profiler_sample_callstack: Profile random samples application-wide using a callstack based sampler. (yes|no)
    if cfg.target != 'template_release':
        scons.build_vars.append("profiler_sample_callstack=yes")

    # profiler_track_memory: Profile memory allocations, if the profiler supports it. (yes|no)
    scons.build_vars.append("profiler_track_memory=yes")

    _append_tracy_features(scons)

    cfg.buildtool.build_vars.append('extra_suffix=tracy')

    # if cfg.target == 'template_release':
    #     cfg.script_parts += [tracy_script]
    return True


def tracy_script():
    """
    Environment setup for Tracy profiler.
    """
    # start_script
    # MARK: Tracy
    #[=================================[ Tracy ]=================================]
    os.environ["TRACY_NO_DBGHELP_INIT_LOAD"] = "1"


def config_libtracy( cfg:SimpleNamespace ) -> bool:
    """
    Tracy build that links Tracy as a shared library.
    :param cfg:
    :return:
    """
    if not config_tracy(cfg):
        return False
    cfg.buildtool.build_vars.append('tracy_as_shared=yes')
    return True


def expand_dev( config:SimpleNamespace ) -> list[SimpleNamespace]:
    """
    Each build, and on x86_64 and arm64 the same build with dev_build on.
    The dev copy carries a dev_build tag. The other copy keeps its name.
    :param config:
    :return:
    """
    configs_out = [copy.deepcopy(config)]
    setattr(configs_out[0], 'dev_build', None)
    if getattr(config, 'arch', None) not in ('x86_64', 'arm64'):
        return configs_out

    dev = copy.deepcopy(config)
    setattr(dev, 'dev_build', 'dev_build')
    dev.buildtool.build_vars.append('dev_build=yes')
    configs_out.append(dev)
    return configs_out


def expand_tests( config:SimpleNamespace ) -> list[SimpleNamespace]:
    """
    Each build, and the same build with the unit tests switched on.
    The tests copy carries a tests tag. The other copy keeps the existing name.
    :param config:
    :return:
    """
    configs_out = []
    for tests in (False, True):
        cfg = copy.deepcopy(config)
        setattr(cfg, 'tests', 'tests' if tests else None)
        if tests:
            cfg.buildtool.build_vars.append('tests=yes')
        configs_out.append(cfg)
    return configs_out


variations = {
    'default': lambda cfg: True,
    'minimum': config_minim,
    'tracy': config_tracy,
    'libtracy': config_libtracy,
}


# MARK: Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _                                                       │
# │  / __|___ _ _  / _(_)__ _ ___                                              │
# │ | (__/ _ \ ' \|  _| / _` (_-<                                              │
# │  \___\___/_||_|_| |_\__, /__/                                              │
# │                     |___/                                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def config_toolchains( cfg:SimpleNamespace ) -> SimpleNamespace:
    """
    Apply toolchain-specific configurations.
    :param cfg:
    :return:
    """
    match cfg.toolchain.name:
        case "llvm":
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "llvm-mingw" | "msys2-clang64":
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64":
            cfg.scons["build_vars"].append("use_mingw=yes")

        case 'msys2-mingw32':
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.script_parts.append( delete_translations )

        case 'appleclang':
            cfg.scons['build_vars'].append('generate_bundle=yes')

    return cfg

def expand_variations( config:SimpleNamespace ) -> list:
    """
    Expand build configuration into variants.
    :param config:
    :return:
    """
    configs_out:list = []
    for label, config_func in variations.items():
        cfg = copy.deepcopy(config)

        setattr(cfg, 'variant', label)

        if config_func( cfg ): # Only keep variants who's configuration step succeeds.
            configs_out.append( cfg )

    return configs_out


