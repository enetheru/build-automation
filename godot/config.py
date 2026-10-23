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

# MARK: Tracy paths
# Machine-specific Tracy paths live in godot/paths.local.py, which is
# gitignored. To set up a machine, copy one of the committed examples:
#   godot/paths.local.box.example      (the Linux box)
#   godot/paths.local.windows.example  (Samuel's Windows machine)
# to godot/paths.local.py and edit it. Without that file the paths stay None,
# the `tracy` source is left out, config_tracy skips the tracy variants, and
# the test step skips every stage whose tool or harness is missing.

# Shared, machine-independent settings. config_tracy checks the version header
# so a different Tracy in TRACY_PROFILER_PATH can't slip into a build.
TRACY_VERSION = '0.14.1'
TRACY_CAPTURE_ADDR = '127.0.0.1'
# Listen port for tracy-capture and the engine's --tracy-port. After
# paths.local.py, an environment variable overrides it: TRACY_CAPTURE_PORT,
# then GODOT_TRACY_PORT, then TRACY_PORT. Each capture starts here and
# moves to the next free port when this one is already bound.
TRACY_CAPTURE_PORT = '8086'
TRACY_TEST_FEATURES = 'zones,plots,messages,frames,gdscript_auto,gdscript_zones_manual'
TRACY_TEST_TIMEOUT = 300    # seconds for one engine run
# --tracy-mask for the capture runs; None passes no --tracy-mask (build default).
TRACY_TEST_MASK: str | None = None
# Doctest selection for the doctest stage (doctest --test-case pattern).
TRACY_TEST_DOCTEST = '*[Profiling]*'
# The GPU late-start stage (runs A to D). It runs whenever the build has
# profiler=tracy with the GPU feature; it skips only when there is no display
# or no Vulkan device.
TRACY_TEST_GPU_FEATURES = 'zones,messages,gpu,frames'
TRACY_TEST_GPU_QUIT_AFTER = 320     # --quit-after; late_gpu.gd quits at frame 300
# Windowed frame-image stage. frame_images.gd runs 90 frames. The first
# thumbnails are not sent (the draw is deferred, the offset is 2, and an
# on-demand server drops the earliest indexes), so the floor is well under 90.
TRACY_TEST_FRAME_IMAGE_FEATURES = 'frames,frame_images'
TRACY_TEST_FRAME_IMAGE_MIN = 20
# Headless log stage. log.gd waits a second, then prints. The on run lists only log.
# The off run lists messages and not log, so those lines must not be messages.
TRACY_TEST_LOG_FEATURES = 'log'
TRACY_TEST_LOG_OFF_FEATURES = 'messages'
# Regression checks against the best previous run (logs-test/<build-name>/best.json).
# Counts that depend on timing may fall this far below the best before failing.
TRACY_TEST_BEST_TOLERANCE = 0.10
# Stages that must run for a variant. A required stage that skips makes the
# run inconclusive; an optional one does not. Missing variants use 'default'.
TRACY_TEST_REQUIRED = {
    'default': ['version', 'doctest'],
    'minimum': ['version', 'doctest'],
    'tracy': ['version', 'tracy_defines', 'doctest', 'fibers_capture', 'counts',
              'silenced', 'toggle', 'log', 'frame_images', 'gpu_late_start'],
    'libtracy': ['version', 'tracy_defines', 'doctest', 'fibers_capture', 'counts',
                 'silenced', 'toggle', 'log', 'frame_images', 'gpu_late_start'],
}

# The test harness lives in the Godot fork. Relative paths are resolved against
# the Godot source being built, so every host tests with the harness of the
# commit under test. paths.local.py may point them elsewhere (absolute paths).
TRACY_FIBERS_GD = 'tests/tracy_harness/fibers.gd'
TRACY_TOGGLE_GD = 'tests/tracy_harness/toggle.gd'
TRACY_FRAME_IMAGES_GD = 'tests/tracy_harness/frame_images.gd'
TRACY_LOG_GD = 'tests/tracy_harness/log.gd'
TRACY_LATE_GPU_PROJECT = 'tests/tracy_harness/late_gpu'
TRACY_ANALYZER_SRC = 'misc/scripts/tracy/trace_analyzer/trace_analyzer.cpp'

# Per-machine paths, all unset here. paths.local.py overrides them.
# TRACY_SOURCE_PATH: the Godot clone that carries the Tracy fork. Fetching from
#   a local repo only sees its branches (refs/heads/*), so TRACY_REF names a
#   branch in that clone.
# TRACY_PROFILER_PATH: the Tracy profiler sources, pinned to TRACY_VERSION. The
#   test step also builds the capture analyser against them.
# TRACY_TOOLS_PATH, TRACY_CAPTURE, TRACY_CSVEXPORT: tracy-capture and
#   tracy-csvexport for the capture stages.
TRACY_SOURCE_PATH: str | None = None
TRACY_REF: str | None = None
TRACY_PROFILER_PATH: str | None = None
TRACY_TOOLS_PATH: str | None = None
TRACY_CAPTURE: str | None = None
TRACY_CSVEXPORT: str | None = None
# A prebuilt trace_analyzer. Unset, the test step uses the cached analyser in
# godot/trace_analyzer/<tracy-version>/ (gitignored), next to this file. The
# analyser depends on the Tracy release, not on the Godot commit, so it is
# built once per Tracy version, in a short temporary folder (g++ against the
# csvexport build on Linux, else CMake), then copied into the cache. A change
# to the analyser source (sha256 in trace_analyzer.info) rebuilds it.
TRACY_ANALYZER: str | None = None
# CMake for the analyser build; None looks for cmake on PATH.
TRACY_CMAKE: str | None = None
# X display for the GPU stage on Linux; None uses $DISPLAY, or starts Xvfb
# (TRACY_XVFB) when $DISPLAY is unset.
TRACY_TEST_DISPLAY: str | None = None
TRACY_XVFB = 'Xvfb'
# Every Godot build. The install verb copies that build's launch files into
# GODOT_INSTALL_PATH after the earlier steps have succeeded. Builds share
# this one directory. None leaves the verb with nothing to copy.
GODOT_INSTALL_PATH: str | None = None

# Names paths.local.py may set. The shared settings above may be overridden too.
_LOCAL_OVERRIDES = (
    'TRACY_SOURCE_PATH', 'TRACY_REF', 'TRACY_PROFILER_PATH', 'TRACY_TOOLS_PATH',
    'TRACY_CAPTURE', 'TRACY_CSVEXPORT', 'TRACY_ANALYZER_SRC', 'TRACY_ANALYZER', 'TRACY_CMAKE',
    'TRACY_FIBERS_GD', 'TRACY_TOGGLE_GD', 'TRACY_FRAME_IMAGES_GD', 'TRACY_LOG_GD',
    'TRACY_LATE_GPU_PROJECT',
    'TRACY_VERSION', 'TRACY_CAPTURE_ADDR', 'TRACY_CAPTURE_PORT',
    'TRACY_TEST_FEATURES', 'TRACY_TEST_TIMEOUT', 'TRACY_TEST_MASK', 'TRACY_TEST_DOCTEST',
    'TRACY_TEST_GPU_FEATURES', 'TRACY_TEST_GPU_QUIT_AFTER',
    'TRACY_TEST_FRAME_IMAGE_FEATURES', 'TRACY_TEST_FRAME_IMAGE_MIN',
    'TRACY_TEST_LOG_FEATURES', 'TRACY_TEST_LOG_OFF_FEATURES',
    'TRACY_TEST_BEST_TOLERANCE',
    'TRACY_TEST_REQUIRED', 'TRACY_TEST_DISPLAY', 'TRACY_XVFB',
    'GODOT_INSTALL_PATH',
)


def _load_local_paths() -> None:
    """Apply godot/paths.local.py, when present, over the defaults above."""
    import importlib.util
    try:
        local = pathlib.Path(__file__).with_name('paths.local.py')
    except NameError:   # no __file__, nothing to look for
        return
    if not local.is_file():
        return
    spec = importlib.util.spec_from_file_location('godot_paths_local', local)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in _LOCAL_OVERRIDES:
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)


_load_local_paths()


def _port_from_environ() -> str | None:
    import os
    for name in ('TRACY_CAPTURE_PORT', 'GODOT_TRACY_PORT', 'TRACY_PORT'):
        value = os.environ.get(name)
        if value:
            return value
    return None


_env_port = _port_from_environ()
if _env_port:
    TRACY_CAPTURE_PORT = _env_port

# Built after the local overrides. The generated build script only carries the
# body of test_scons, so configure_scons copies this onto the build as
# build['tracy_test']. A missing tool or harness makes its stage skip with a
# message. The generated script drops empty values, so read it with .get().
TRACY_TEST = {
    'version': TRACY_VERSION,
    'profiler_path': TRACY_PROFILER_PATH,
    'tools_path': TRACY_TOOLS_PATH,
    'capture': TRACY_CAPTURE,
    'csvexport': TRACY_CSVEXPORT,
    'analyzer': TRACY_ANALYZER,
    'analyzer_src': TRACY_ANALYZER_SRC,
    # The generated script cannot find this file, so it gets the cache folder here.
    'analyzer_cache': (pathlib.Path(__file__).resolve().parent / 'trace_analyzer').as_posix(),
    'cmake': TRACY_CMAKE,
    'fibers_gd': TRACY_FIBERS_GD,
    'toggle_gd': TRACY_TOGGLE_GD,
    'frame_images_gd': TRACY_FRAME_IMAGES_GD,
    'log_gd': TRACY_LOG_GD,
    'late_gpu_project': TRACY_LATE_GPU_PROJECT,
    'address': TRACY_CAPTURE_ADDR,
    'port': TRACY_CAPTURE_PORT,
    'features': TRACY_TEST_FEATURES,
    'mask': TRACY_TEST_MASK,
    'doctest': TRACY_TEST_DOCTEST,
    'gpu_features': TRACY_TEST_GPU_FEATURES,
    'gpu_quit_after': TRACY_TEST_GPU_QUIT_AFTER,
    'frame_image_features': TRACY_TEST_FRAME_IMAGE_FEATURES,
    'frame_image_min': TRACY_TEST_FRAME_IMAGE_MIN,
    'log_features': TRACY_TEST_LOG_FEATURES,
    'log_off_features': TRACY_TEST_LOG_OFF_FEATURES,
    'best_tolerance': TRACY_TEST_BEST_TOLERANCE,
    'required': TRACY_TEST_REQUIRED,
    'display': TRACY_TEST_DISPLAY,
    'xvfb': TRACY_XVFB,
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
}

# The Tracy fork only exists where paths.local.py points at it.
if TRACY_SOURCE_PATH and TRACY_REF:
    sources['tracy'] = SimpleNamespace({**vars(origin), **{
        'remote':'godot-private',
        'url': TRACY_SOURCE_PATH,
        'ref': TRACY_REF
    }})

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
        if TRACY_REF and ref == TRACY_REF:
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
    Test a tests=yes binary the way godot-build tests it by hand, in stages:
    version, tracy_defines, doctest, then on profiler=tracy builds
    fibers_capture, counts, silenced, toggle, log, frame_images and
    gpu_late_start. The harness
    comes from the Godot source under test (tests/tracy_harness). Logs,
    summary.json, report.txt and one .cmd per command go to
    <project>/logs-test/<build-name>/<short-commit>/, next to logs-raw and
    logs-clean. Captured .tracy files are kept there; a rerun of the same
    commit replaces them. best.json in <project>/logs-test/<build-name>/
    holds the best counts so far for the regression checks.
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

    # MARK: Test
    #[=================================[ Test ]=================================]
    # The generated script keeps only the body after `# start_script`, so the
    # helpers and stages are nested defs. Every stage returns the same shape:
    #   {'status': 'pass'|'fail'|'skip'|'n/a'|'dry', 'reason': str|None,
    #    'facts': {...}, 'failures': [str], 'logs': [path]}
    # skip: the machine could not run it (a missing tool, display, Vulkan).
    # n/a: the build does not have what the stage tests (not profiler=tracy, ...).
    if config['ok'] and 'test' in opts['build_actions']:
        console.set_window_title(f'Test - {build["name"]}')

        test_summary = None
        with Timer(name='test') as timer, fmt.Section('Test'):
            import csv
            import hashlib
            import json
            import re
            import shutil
            import socket
            import subprocess
            import sys
            import tempfile
            import time
            from datetime import datetime

            tt = dict(build.get('tracy_test') or {})
            dry = bool(opts['dry'])
            run_timeout = int(tt.get('timeout') or 300)
            tolerance = float(tt.get('best_tolerance') or 0)
            runtime_case = '[Profiling] Report the runtime state'
            stage_names = ['version', 'tracy_defines', 'doctest', 'fibers_capture', 'counts',
                           'silenced', 'toggle', 'log', 'frame_images', 'gpu_late_start']

            # MARK: Helpers
            def scons_opt(name):
                value = None
                for item in buildtool.get('build_vars', []):
                    key, sep, val = str(item).partition('=')
                    if sep and key == name:
                        value = val
                return value

            def is_template():
                target = scons_opt('target') or build.get('target', '')
                return str(target).startswith('template')

            def path_overrides_disabled():
                # SConstruct defines OVERRIDE_PATH_ENABLED for editor builds and for
                # templates built with disable_path_overrides=no (expand_tests adds it).
                # Without it main.cpp rejects --path and --main-pack, ignores --script,
                # and a failed project load ends in OS::alert, a modal dialog on Windows.
                if not is_template():
                    return False
                value = scons_opt('disable_path_overrides')
                return value is None or value.lower() not in ('no', 'false', '0', 'n', 'f', 'off')

            def test_binary(bin_dir, platform_name):
                # Same suffix SConstruct builds, including detect.py's .llvm prefix.
                parts = ['godot', platform_name, scons_opt('target') or build.get('target', '')]
                if scons_opt('dev_build') == 'yes':
                    parts.append('dev')
                if scons_opt('precision') == 'double':
                    parts.append('double')
                parts.append(scons_opt('arch') or '')
                if scons_opt('threads') == 'no':
                    parts.append('nothreads')
                extra = scons_opt('extra_suffix') or ''
                if scons_opt('use_llvm') == 'yes':
                    extra = f'llvm.{extra}' if extra else 'llvm'
                if extra:
                    parts.append(extra)
                stem = '.'.join(part for part in parts if part)
                if platform_name == 'windows':
                    exe = bin_dir / f'{stem}.console.exe'
                    return exe if exe.is_file() else bin_dir / f'{stem}.exe'
                return bin_dir / stem

            def result():
                return {'status': 'pass', 'reason': None, 'facts': {}, 'failures': [], 'logs': []}

            def skip(res, why):
                res['status'] = 'skip'
                res['reason'] = why
                fmt.h(f'Skip: {why}')
                return res

            def not_applicable(res, why):
                res['status'] = 'n/a'
                res['reason'] = why
                fmt.h(f'n/a: {why}')
                return res

            def fail(res, why):
                res['status'] = 'fail'
                res['failures'].append(why)
                fmt.h(f'FAIL: {why}')
                return res

            def as_dry(res):
                res['status'] = 'dry'
                return res

            def tail(text, n=20):
                for line in text.rstrip().splitlines()[-n:]:
                    print(f'    {line}')

            def plain(text):
                return re.sub(r'\x1b\[[0-9;]*m', '', text)

            def cmdline(args, env=None):
                prefix = ''.join(f'{k}={v} ' for k, v in (env or {}).items())
                return prefix + subprocess.list2cmdline([str(a) for a in args])

            def write_cmd(res, name, args, env=None):
                # Every command a stage launches is saved as <name>.cmd.
                if dry:
                    return
                path = logdir / f'{name}.cmd'
                path.write_text(cmdline(args, env) + '\n', encoding='utf-8')
                res['logs'].append(path.as_posix())

            def run(res, name, args, timeout, echo=20, env=None):
                # Like stream_command: print the command, launch nothing when dry.
                args = [str(a) for a in args]
                print(f'  $ {cmdline(args, env)}')
                if dry:
                    return None
                write_cmd(res, name, args, env)
                started = time.monotonic()
                full_env = {**os.environ, **env} if env else None
                try:
                    proc = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                                          errors='backslashreplace', timeout=timeout,
                                          stdin=subprocess.DEVNULL, env=full_env)
                    rc, out, err = proc.returncode, proc.stdout, proc.stderr
                except subprocess.TimeoutExpired as e:
                    out = e.stdout.decode('utf-8', 'backslashreplace') if isinstance(e.stdout, bytes) else (e.stdout or '')
                    err = e.stderr.decode('utf-8', 'backslashreplace') if isinstance(e.stderr, bytes) else (e.stderr or '')
                    rc = f'timeout after {timeout} s'
                except OSError as e:
                    rc, out, err = f'launch error: {e}', '', ''
                secs = round(time.monotonic() - started, 3)
                for stream, text in (('stdout', out), ('stderr', err)):
                    path = logdir / f'{name}.{stream}.log'
                    path.write_text(text, encoding='utf-8')
                    res['logs'].append(path.as_posix())
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

            def harness(key):
                # Relative harness paths belong to the Godot source under test.
                value = tt.get(key)
                if not value:
                    return None
                path = Path(value)
                return path if path.is_absolute() else source_dir / path

            def port_busy(address, port):
                # A connect that succeeds means something is listening.
                # Refused means free. Binding to probe would leave the port
                # in TIME_WAIT, and the engine listen after that would fail.
                # Any other error counts as taken so a black-holed port is
                # not handed to Tracy.
                try:
                    with socket.create_connection((address, int(port)), timeout=1):
                        return True
                except ConnectionRefusedError:
                    return False
                except OSError:
                    return True

            def free_listen_port(address, preferred):
                # Leave tt['port'] alone. The next stage starts from the
                # configured port again once this capture has released it.
                try:
                    start = int(preferred)
                except (TypeError, ValueError):
                    return None
                if start < 1 or start > 65535:
                    return None
                spans = [range(start, 65536)]
                if start > 1024:
                    spans.append(range(1024, start))
                for span in spans:
                    for port in span:
                        if not port_busy(address, port):
                            return str(port)
                return None

            def option_value(args, name):
                args = [str(a) for a in args]
                return args[args.index(name) + 1] if name in args[:-1] else None

            def stub_project():
                # A template (no TOOLS_ENABLED) must load project data. Without --path it
                # tries the cwd, which has none, and the failed load ends in OS::alert
                # ("Couldn't load project data at path ..."), a modal dialog on Windows.
                # The editor runs a --script without a project, so it gets no stub.
                stub = (logdir / 'stub_project').resolve()
                if not dry and 'stub_project' not in ctx:
                    stub.mkdir(parents=True, exist_ok=True)
                    (stub / 'project.godot').write_text(
                        '; Minimal project for the --script test stages of template builds.\n'
                        'config_version=5\n\n[application]\n\nconfig/name="tracy_test_stub"\n',
                        encoding='utf-8')
                    ctx['stub_project'] = stub.as_posix()
                return stub

            def script_cmd(script, unsilence):
                cmd = [str(exe), '--headless']
                if is_template():
                    cmd += ['--path', str(stub_project())]
                cmd += ['--tracy'] if unsilence else []
                cmd += ['--script', str(Path(script).resolve()), '--tracy-features', tt['features']]
                if tt.get('mask') is not None:
                    cmd += ['--tracy-mask', tt['mask']]
                return cmd

            def capture_run(res, name, eng_cmd, env=None):
                # tracy-capture in the background, then the engine with a subprocess timeout.
                facts = res['facts']
                trace = logdir / f'{name}.tracy'
                eng_cmd = [str(a) for a in eng_cmd]
                # Pin tracy-capture -p and the engine to the same free port.
                # Without --tracy-port the client searches from 8086 and can
                # miss this capture, or meet an engine already listening.
                port = free_listen_port(tt['address'], tt.get('port'))
                if port is None:
                    fail(res, f"no free listen port on {tt['address']} from {tt.get('port')}")
                    return None, None
                if port != str(tt.get('port')):
                    print(f"  {tt['address']}:{tt.get('port')} is in use; using {port}")
                cap_cmd = [str(tool('capture')), '-o', str(trace), '-a', tt['address'], '-p', port, '-f']
                if '--tracy-port' in eng_cmd[:-1]:
                    eng_cmd[eng_cmd.index('--tracy-port') + 1] = port
                else:
                    eng_cmd += ['--tracy-port', port]
                facts['capture_cmd'] = cmdline(cap_cmd)
                facts['engine_cmd'] = cmdline(eng_cmd, env)
                facts['tracy_flag'] = '--tracy' in eng_cmd
                facts['tracy_features'] = option_value(eng_cmd, '--tracy-features')
                facts['tracy_mask'] = option_value(eng_cmd, '--tracy-mask')   # None: build default
                print(f'  $ {cmdline(cap_cmd)} &')
                if dry:
                    print(f'  $ {cmdline(eng_cmd, env)}')
                    as_dry(res)
                    return None, None
                write_cmd(res, f'{name}-capture', cap_cmd)
                started = time.monotonic()
                cap_log_path = logdir / f'{name}-capture.log'
                res['logs'].append(cap_log_path.as_posix())
                with open(cap_log_path, 'w', encoding='utf-8') as cap_log:
                    popen_kw = {}
                    if sys.platform == 'win32':
                        popen_kw['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
                    cap = subprocess.Popen(cap_cmd, stdout=cap_log, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, **popen_kw)
                    time.sleep(2)   # the manual flow starts the capture 2 s ahead
                    eng = run(res, f'{name}-engine', eng_cmd, run_timeout, echo=8, env=env)
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
                facts['secs'] = round(time.monotonic() - started, 3)
                cap_text = cap_log_path.read_text(encoding='utf-8', errors='backslashreplace')
                fmt.h(f'{name} capture:')
                tail(cap_text, 6)
                facts['engine_rc'] = eng['rc']
                facts['capture_rc'] = cap_rc
                m = re.search(r'^Zones:\s*([\d,]+)', cap_text, re.M)
                facts['capture_zones'] = int(m.group(1).replace(',', '')) if m else None
                m = re.search(r'^Frames:\s*([\d,]+)', cap_text, re.M)
                facts['capture_frames'] = int(m.group(1).replace(',', '')) if m else None
                if eng['rc'] != 0:
                    fail(res, f'engine exited {eng["rc"]}')
                if cap_rc != 0:
                    fail(res, f'tracy-capture exited {cap_rc}')
                for label, text in (('engine', eng['out'] + eng['err']), ('capture', cap_text)):
                    if 'Instrumentation failure' in text:
                        fail(res, f'"Instrumentation failure" in {label} output')
                size = trace.stat().st_size if trace.is_file() else 0
                facts['trace'] = trace.as_posix()
                facts['trace_bytes'] = size
                if not size:
                    fail(res, f'{trace.as_posix()} is missing or empty')
                    return None, eng
                return trace, eng

            def zone_csv(res, name, trace):
                # tracy-csvexport: name,src_file,src_line,total_ns,total_perc,counts,mean,min,max,std
                out = run(res, f'{name}-csvexport', [tool('csvexport'), trace], 120, echo=0)
                if out is None or out['rc'] != 0:
                    return None
                csv_path = logdir / f'{name}-zones.csv'
                csv_path.write_text(out['out'], encoding='utf-8')
                res['logs'].append(csv_path.as_posix())
                total = 0
                unknown = 0
                names = set()
                for row in list(csv.reader(out['out'].splitlines()))[1:]:
                    if len(row) < 10:
                        continue
                    zname = ','.join(row[:-9])
                    count = int(row[-5])
                    total += count
                    names.add(zname)
                    if zname == '???':
                        unknown += count
                return {'zones': total, 'distinct_zone_names': len(names), 'unknown_zones': unknown,
                        'zone_names': names}

            def gpu_zone_times(res, name, trace):
                # tracy-csvexport -g: name,src_file,Time from start of program,GPU execution time (ns).
                out = run(res, f'{name}-gpu-csvexport', [tool('csvexport'), '-g', trace], 120, echo=0)
                if out is None or out['rc'] != 0:
                    return None
                csv_path = logdir / f'{name}-gpu.csv'
                csv_path.write_text(out['out'], encoding='utf-8')
                res['logs'].append(csv_path.as_posix())
                times = []
                for row in list(csv.reader(out['out'].splitlines()))[1:]:
                    if len(row) >= 4 and row[-2].isdigit():
                        times.append(int(row[-2]) / 1e9)   # same base as the analyser's seconds
                return times

            def ensure_analyzer(res):
                # 1. A prebuilt TRACY_ANALYZER. 2. The cached analyser for this Tracy version
                # in godot/trace_analyzer/<version>/, built when it is missing or its source changed.
                prebuilt = tool('analyzer')
                if prebuilt:
                    return prebuilt, None
                if 'analyzer' not in ctx:
                    ctx['analyzer'] = build_analyzer(res)
                return ctx['analyzer']

            def analyzer_tracy_version(profiler):
                # TracyVersion.hpp of the sources it links against, else git describe of
                # that tree, else the pinned TRACY_VERSION.
                found = tracy_version_at(profiler) if tt.get('profiler_path') else None
                if not found and tt.get('profiler_path') and profiler.is_dir():
                    try:
                        proc = subprocess.run(['git', '-C', str(profiler), 'describe', '--tags', '--always'],
                                              capture_output=True, text=True, timeout=30)
                        found = proc.stdout.strip() if proc.returncode == 0 else None
                    except (OSError, subprocess.SubprocessError):
                        found = None
                found = found or tt.get('version') or 'unknown'
                return re.sub(r'[^0-9A-Za-z._-]', '_', found.lstrip('v'))

            def sha256_of(path):
                return hashlib.sha256(Path(path).read_bytes()).hexdigest()

            def analyzer_stale(src, info_path):
                # None while the cached analyser matches the source, else why it must be rebuilt.
                # The info records source_sha256 (trace_analyzer.cpp) and, after a CMake build,
                # cmakelists_sha256. Without a source to compare, the cached binary is kept.
                if not src or not src.is_file():
                    return None
                try:
                    recorded = dict(line.split(' ', 1) for line in
                                    info_path.read_text(encoding='utf-8').splitlines() if ' ' in line)
                except (OSError, ValueError):
                    return f'no readable {info_path.name}'
                if recorded.get('source_sha256') != sha256_of(src):
                    return f'source changed ({src.name})'
                cmakelists = src.parent / 'CMakeLists.txt'
                if 'cmakelists_sha256' in recorded and cmakelists.is_file() \
                        and recorded['cmakelists_sha256'] != sha256_of(cmakelists):
                    return 'source changed (CMakeLists.txt)'
                return None

            def build_analyzer(res):
                # The analyser depends on the Tracy release, not on the Godot commit, so one
                # build per Tracy version is cached next to godot/config.py and reused by
                # every build. It is built in a short temporary folder: the deep
                # logs-test/<build-name>/ path broke the CMake build on Windows
                # ("Filename too long" in the fetched dependencies).
                # g++ against the csvexport CMake build's libraries (Linux), else CMake with
                # the fork's CMakeLists.txt (Tracy's CMake fetches zstd, capstone, PPQSort).
                # A change to the analyser source (see analyzer_stale) rebuilds the cache entry.
                src = harness('analyzer_src')
                profiler = Path(tt.get('profiler_path') or '')
                exe_name = 'trace_analyzer.exe' if os.name == 'nt' else 'trace_analyzer'
                version = analyzer_tracy_version(profiler)
                cache_root = Path(tt.get('analyzer_cache') or (log_root / 'tools'))
                cache_dir = cache_root / version
                binary = cache_dir / exe_name
                info_path = cache_dir / 'trace_analyzer.info'
                res['facts']['analyzer_cache'] = binary.as_posix()
                if binary.is_file():
                    stale = analyzer_stale(src, info_path)
                    if stale is None:
                        fmt.h(f'Analyser: cached {binary.as_posix()} (Tracy {version})')
                        return binary, None
                    # The old binary stays until a new one replaces it, but is not used.
                    fmt.h(f'Analyser: rebuilding: {stale}')
                    res['facts']['analyzer_rebuild'] = stale
                if not src or not src.is_file():
                    return None, f'no analyser source at {src}'
                if not (profiler / 'server/TracyWorker.cpp').is_file():
                    return None, f'no Tracy server sources at {profiler.as_posix()} (TRACY_PROFILER_PATH)'
                if dry:
                    print(f'  (build {binary.as_posix()} from {src.as_posix()} in a temporary folder)')
                    return None, 'dry'
                work = Path(tempfile.mkdtemp(prefix='ta-'))
                fmt.h(f'Analyser: building for Tracy {version} in {work.as_posix()}')
                res['facts']['analyzer_build_dir'] = work.as_posix()
                built = None
                used_cmake = False
                tries = []
                try:
                    csv_dir = Path(tt.get('tools_path') or '') / 'csvexport'
                    libs = [csv_dir / 'libTracyServer.a', csv_dir / '_deps/capstone-build/libcapstone.a',
                            csv_dir / '_deps/zstd-build/lib/libzstd.a']
                    cxx = shutil.which('g++')
                    if cxx and all(p.is_file() for p in libs):
                        # Reuse the include paths CMake gave csvexport, so the headers match the library.
                        includes = []
                        try:
                            ninja = (csv_dir / 'build.ninja').read_text(encoding='utf-8')
                            m = re.search(r'csvexport\.cpp\.o:.*?\n(?:  .*\n)*?  INCLUDES = (.*)\n', ninja)
                            includes = m.group(1).split() if m else []
                        except OSError:
                            pass
                        if not includes:
                            includes = [f'-I{profiler / "public/common"}', f'-I{profiler / "server"}']
                        out_exe = work / exe_name
                        cmd = [cxx, '-O2', '-std=gnu++20', '-flto=auto', *includes, '-o', out_exe, src,
                               *libs, '-lpthread']
                        out = run(res, 'analyzer-build', cmd, 900, echo=10)
                        if out['rc'] == 0 and out_exe.is_file():
                            built = out_exe
                        else:
                            tries.append(f'g++ exited {out["rc"]}')
                    else:
                        tries.append(f'no g++ build (g++={cxx}, needs {csv_dir.as_posix()}/libTracyServer.a)')
                    cmake = shutil.which(tt.get('cmake') or 'cmake')
                    if built is None and cmake:
                        cmake_dir = work / 'b'
                        out = run(res, 'analyzer-cmake-configure',
                                  [cmake, '-S', src.parent, '-B', cmake_dir,
                                   f'-DTRACY_SOURCE_DIR={profiler.as_posix()}', '-DCMAKE_BUILD_TYPE=Release'],
                                  900, echo=10)
                        if out['rc'] == 0:
                            out = run(res, 'analyzer-cmake-build',
                                      [cmake, '--build', cmake_dir, '--target', 'trace_analyzer',
                                       '--config', 'Release'], 1800, echo=10)
                        found = [p for p in (cmake_dir / exe_name, cmake_dir / 'Release' / exe_name) if p.is_file()]
                        if out['rc'] == 0 and found:
                            built = found[0]
                            used_cmake = True
                        else:
                            tries.append(f'cmake exited {out["rc"]}')
                    elif built is None:
                        tries.append('no cmake (TRACY_CMAKE or PATH)')
                    if built is not None:
                        # Copy beside the cache entry, then rename, so a half-copied file is never used.
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        partial = cache_dir / (exe_name + '.partial')
                        shutil.copy2(built, partial)
                        partial.replace(binary)
                        cmakelists = src.parent / 'CMakeLists.txt'
                        info_path.write_text(
                            f'tracy_version {version}\ntracy_path {profiler.as_posix()}\n'
                            f'source {src.as_posix()}\nsource_commit {head}\n'
                            f'source_sha256 {sha256_of(src)}\n'
                            + (f'cmakelists_sha256 {sha256_of(cmakelists)}\n'
                               if used_cmake and cmakelists.is_file() else '')
                            + f'built {datetime.now().astimezone().isoformat(timespec="seconds")}\n',
                            encoding='utf-8')
                        fmt.h(f'Analyser: cached {binary.as_posix()}')
                finally:
                    shutil.rmtree(work, ignore_errors=True)
                if built is None:
                    return None, 'cannot build the analyser: ' + '; '.join(tries)
                return binary, None

            def tracy_message_rows(text):
                # One MSG row can hold newlines. An error is "ERROR: ..." then "   at: ...".
                # The closing quote is the last character of the row's last line.
                # color is the value the analyser prints (0xFFBBGGRR, or 0xFFFFFFFF
                # when the client sent no color).
                found = []
                current = None
                header = re.compile(
                    r"^  MSG ([\d.]+) thread=(.*?) color=([0-9a-fA-F]+) src=(\d+) sev=(\d+) '(.*)$")
                for line in text.splitlines():
                    m = header.match(line)
                    if m:
                        if current is not None:
                            found.append(current)
                        body = m.group(6)
                        closed = body.endswith("'")
                        current = {
                            'time': float(m.group(1)),
                            'color': int(m.group(3), 16),
                            'src': int(m.group(4)),
                            'sev': int(m.group(5)),
                            'text': body[:-1] if closed else body,
                        }
                        if closed:
                            found.append(current)
                            current = None
                        continue
                    if current is None:
                        continue
                    if line.endswith("'"):
                        current['text'] += '\n' + line[:-1]
                        found.append(current)
                        current = None
                    else:
                        current['text'] += '\n' + line
                if current is not None:
                    found.append(current)
                return found

            def analyse(res, name, trace):
                binary, why = ensure_analyzer(res)
                if binary is None:
                    return None, why
                out = run(res, f'{name}-analysis', [binary, trace], 300, echo=0)
                if out is None:
                    return None, 'dry'
                path = logdir / f'{name}-analysis.txt'
                path.write_text(out['out'], encoding='utf-8')
                res['logs'].append(path.as_posix())
                if out['rc'] != 0:
                    return None, f'analyser exited {out["rc"]}'
                text = out['out']
                info = {'analysis': path.as_posix()}
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
                info['tracy_msgs'] = tracy_message_rows(text)
                m = re.search(r'^messages: (\d+)', text, re.M)
                info['messages'] = int(m.group(1)) if m else None
                plots = [(ptype, pname, float(last) if last else None) for ptype, pname, last in
                         re.findall(r"^  PLOT type=(\w+) name='(.*?)' points=\d+(?: first [\d.]+ last ([\d.]+))?", text, re.M)]
                info['plots'] = len(plots)
                info['engine_plots'] = sum(1 for ptype, _, _ in plots if ptype != 'SysTime')
                info['plot_list'] = plots
                m = re.search(r'^gpu zones=(\d+) gpu ctx=(\d+)', text, re.M)
                info['gpu_zones'] = int(m.group(1)) if m else None
                info['gpu_contexts'] = int(m.group(2)) if m else None
                # One "ctx type=... name='...'" line per GPU context (the fork's analyser).
                ctx_lines = re.findall(r"^ctx type=(\S+) name='(.*?)'", text, re.M)
                info['gpu_context_names'] = [f'{n} ({t})' for t, n in ctx_lines]
                if info['gpu_contexts'] and not ctx_lines:
                    info['gpu_context_names'] = None   # an older analyser without ctx lines
                texts = [msg for _, _, msg in info['message_list']]
                info['capture_started_msg'] = 'Godot Tracy capture started' in texts
                info['capture_stopped_msg'] = 'Godot Tracy capture stopped' in texts
                info['capture_started_at'] = [t for t, _, msg in info['message_list']
                                              if msg == 'Godot Tracy capture started']
                info['capture_stopped_at'] = [t for t, _, msg in info['message_list']
                                              if msg == 'Godot Tracy capture stopped']
                m = re.search(r'frameimages=(\d+)', text)
                info['frame_images'] = int(m.group(1)) if m else None
                info['frame_image_sizes'] = [
                    {'w': int(w), 'h': int(h), 'flip': int(flip), 'count': int(count)}
                    for w, h, flip, count in re.findall(
                        r'^  FRAMEIMAGE (\d+)x(\d+) flip=(\d+) count=(\d+)', text, re.M)]
                return info, None

            def trace_facts(res, info):
                res['facts'].update({k: v for k, v in info.items()
                                     if k not in ('message_list', 'plot_list', 'tracy_msgs')})

            def metric(stage_name, key, value, exact):
                # Compared with best.json after all stages; exact counts may not drop at all.
                if value is not None:
                    ctx['metrics'].append({'stage': stage_name, 'key': key, 'value': value, 'exact': exact})

            def ensure_display():
                # The GPU runs need a window. Windows and macOS use the desktop. Linux uses
                # TRACY_TEST_DISPLAY or $DISPLAY, else starts Xvfb (Mesa llvmpipe gives Vulkan).
                if not sys.platform.startswith('linux'):
                    return {}, None
                display = tt.get('display') or os.environ.get('DISPLAY')
                if display:
                    return {'DISPLAY': display}, None
                xvfb = shutil.which(tt.get('xvfb') or 'Xvfb')
                if not xvfb:
                    return None, 'no display: $DISPLAY is unset and there is no Xvfb'
                num = next((n for n in range(99, 140) if not Path(f'/tmp/.X11-unix/X{n}').exists()
                            and not Path(f'/tmp/.X{n}-lock').exists()), None)
                if num is None:
                    return None, 'no free X display number for Xvfb'
                cmd = [xvfb, f':{num}', '-screen', '0', '1280x720x24', '-nolisten', 'tcp']
                print(f'  $ {cmdline(cmd)} &')
                ctx['xvfb_cmd'] = cmdline(cmd)
                if dry:
                    return {'DISPLAY': f':{num}'}, None
                (logdir / 'xvfb.cmd').write_text(cmdline(cmd) + '\n', encoding='utf-8')
                xlog = open(logdir / 'xvfb.log', 'w', encoding='utf-8')
                ctx['xvfb'] = subprocess.Popen(cmd, stdout=xlog, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
                for _ in range(100):
                    if Path(f'/tmp/.X11-unix/X{num}').exists():
                        break
                    if ctx['xvfb'].poll() is not None:
                        return None, f'Xvfb exited {ctx["xvfb"].returncode} (see xvfb.log)'
                    time.sleep(0.1)
                return {'DISPLAY': f':{num}'}, None

            def stop_display():
                proc = ctx.get('xvfb')
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()

            def probe_help():
                # --tracy in --help marks the silent-client feature; the note says
                # whether the build is on-demand or records from launch.
                out = run(ctx['help_res'], 'help', [exe, '--headless', '--help'], 60, echo=0)
                text = plain(out['out'] + out['err'])
                ctx['silent_client'] = bool(re.search(r'^\s*--tracy\s', text, re.M))
                m = re.search(r'This build (?:is on-demand|records from launch)[^\n]*', text)
                ctx['help_mode'] = m.group(0).strip() if m else None
                fmt.h(f'silent-client support (--tracy in --help): {ctx["silent_client"]}')
                fmt.h(f'--help mode: {ctx["help_mode"] or "(no on-demand/record-from-launch note)"}')

            def capture_gate(res, need_silent_client=False, needs_project=False):
                # None when the capture stages can run, otherwise the result to return.
                if not is_tracy:
                    return not_applicable(res, 'not a profiler=tracy build')
                if needs_project and path_overrides_disabled():
                    # Launching it would load no project and raise the alert dialog.
                    return not_applicable(res, 'template built without disable_path_overrides=no: '
                                               '--path and --script are not accepted')
                if not tool('capture'):
                    return skip(res, f'no tracy-capture at {tt.get("capture")} (TRACY_CAPTURE)')
                if need_silent_client and ctx['silent_client'] is False:
                    return not_applicable(res, 'build has no silent-client support (--tracy missing from --help)')
                return None

            # MARK: Stages
            def stage_version():
                # The binary must carry the source's commit.
                res = result()
                out = run(res, 'version', [exe, '--headless', '--version'], 60)
                if out is None:
                    return as_dry(res)
                lines = (out['out'] or out['err']).strip().splitlines()
                facts = res['facts']
                facts['output'] = lines[-1] if lines else ''
                facts['source_commit'] = head
                hashes = re.findall(r'\b([0-9a-f]{7,40})\b', facts['output'])
                if out['rc'] != 0:
                    fail(res, f'--version exited {out["rc"]}')
                elif not head:
                    fail(res, f'cannot read HEAD of {source_dir.as_posix()}')
                elif not any(head.startswith(h) for h in hashes):
                    fail(res, f'version {facts["output"]!r} does not name commit {head[:10]}')
                else:
                    fmt.h(f'{facts["output"]} matches {head[:10]}')
                return res

            def stage_tracy_defines():
                # Tracy version and the generated profiling defines.
                res = result()
                facts = res['facts']
                if is_tracy:
                    profiler_path = scons_opt('profiler_path') or tt.get('profiler_path')
                    found = tracy_version_at(profiler_path) if profiler_path else None
                    facts['tracy_path'] = profiler_path
                    facts['tracy_version'] = found
                    if found != tt.get('version'):
                        fail(res, f'expected Tracy {tt.get("version")} at {profiler_path}, found {found}')
                gen_h = source_dir / 'core/profiling/profiling.gen.h'
                facts['gen_h'] = gen_h.as_posix()
                if not gen_h.is_file():
                    if dry:
                        return as_dry(res)
                    if is_tracy:
                        return fail(res, f'missing {gen_h.as_posix()}')
                    return not_applicable(res, f'no {gen_h.as_posix()} (not a profiler build)')
                data = gen_h.read_bytes()
                facts['gen_h_sha256'] = hashlib.sha256(data).hexdigest()
                defines = {}
                for dname, dvalue in re.findall(
                        r'^#define\s+((?:TRACY|GODOT_TRACY|GODOT_PROFILER|GODOT_USE_TRACY)\w*)[ \t]*(.*)$',
                        data.decode('utf-8', 'replace'), re.M):
                    defines[dname] = dvalue.strip()
                facts['defines'] = defines
                ctx['defines'] = defines
                fmt.h(f'{len(defines)} defines, sha256 {facts["gen_h_sha256"][:16]}')
                if is_tracy:
                    if 'TRACY_ENABLE' not in defines or 'GODOT_USE_TRACY' not in defines:
                        fail(res, 'profiler=tracy build but profiling.gen.h does not enable Tracy')
                    pinned = [defines.get(f'GODOT_TRACY_PINNED_VERSION_{p}') for p in ('MAJOR', 'MINOR', 'PATCH')]
                    if all(pinned) and '.'.join(pinned) != tt.get('version'):
                        fail(res, f'profiling.gen.h pins Tracy {".".join(pinned)}')
                return res

            def stage_doctest():
                res = result()
                facts = res['facts']
                flt = ctx['doctest_filter']
                facts['filter'] = flt
                listing = run(res, 'doctest-list', [exe, '--headless', '--test', '--list-test-cases',
                                                    f'--test-case={flt}'], 300, echo=0)
                out = run(res, 'doctest', [exe, '--headless', '--test', f'--test-case={flt}'], 900, echo=12)
                if out is None:
                    return as_dry(res)
                # The listing prints the case names between two ===== rules.
                blocks = re.split(r'^={20,}\s*$', plain(listing['out'] + listing['err']), flags=re.M)
                names = [ln.strip() for ln in blocks[1].splitlines() if ln.strip()] if len(blocks) > 2 else []
                facts['listed_cases'] = len(names)
                text = plain(out['out'] + out['err'])
                facts['rc'] = out['rc']
                facts['secs'] = out['secs']
                m = re.search(r'test cases:\s*(\d+)\s*\|\s*(\d+) passed\s*\|\s*(\d+) failed\s*\|\s*(?:(\d+) skipped)?', text)
                if m:
                    facts['test_cases'] = {'total': int(m.group(1)), 'passed': int(m.group(2)),
                                           'failed': int(m.group(3)), 'skipped': int(m.group(4) or 0)}
                m = re.search(r'assertions:\s*(\d+)\s*\|\s*(\d+) passed\s*\|\s*(\d+) failed\s*\|\s*(?:(\d+) skipped)?', text)
                if m:
                    facts['assertions'] = {'total': int(m.group(1)), 'passed': int(m.group(2)),
                                           'failed': int(m.group(3)), 'skipped': int(m.group(4) or 0)}
                # One line from "[Profiling] Report the runtime state"; older commits lack it.
                m = re.search(r'^.*Tracy state:.*$', text, re.M)
                facts['tracy_state'] = m.group(0).split('MESSAGE:', 1)[-1].strip() if m else None
                ctx['tracy_state'] = facts['tracy_state']
                fmt.h(f"Tracy state: {facts['tracy_state'] or '(no Tracy state: line)'}")
                if out['rc'] != 0:
                    fail(res, f'doctest exited {out["rc"]}')
                if 'test_cases' not in facts or 'assertions' not in facts:
                    return fail(res, 'no doctest summary in the output')
                cases = facts['test_cases']
                if cases['failed'] or facts['assertions']['failed']:
                    fail(res, 'doctest reported failures')
                if not cases['total']:
                    return fail(res, f'no test case matched {flt}')
                if names and cases['total'] != len(names):
                    fail(res, f"{cases['total']} cases ran, {len(names)} listed for {flt}")
                facts['runtime_case'] = runtime_case in names
                if runtime_case in names:
                    if not facts['tracy_state']:
                        fail(res, f"'{runtime_case}' ran but printed no 'Tracy state:' line")
                elif is_tracy and flt == tt.get('doctest'):
                    fail(res, f"'{runtime_case}' is not among the {flt} cases")
                metric('doctest', f'doctest_cases[{flt}]', cases['total'], exact=True)
                return res

            def stage_fibers_capture():
                res = result()
                gate = capture_gate(res, needs_project=True)
                if gate:
                    return gate
                script = harness('fibers_gd')
                if not script or not script.is_file():
                    return skip(res, f'no fibers harness at {script}')
                trace, _ = capture_run(res, 'fibers', script_cmd(script, unsilence=ctx['silent_client'] or dry))
                if res['status'] == 'pass':
                    ctx['fibers_trace'] = trace
                return res

            def stage_counts():
                # Zones from tracy-csvexport, the rest from the analyser, on the fibers trace.
                res = result()
                facts = res['facts']
                fib = ctx['stages'].get('fibers_capture') or {}
                if fib.get('status') == 'dry':
                    print(f"  $ {tt.get('csvexport')} {logdir / 'fibers.tracy'}")
                    return as_dry(res)
                if fib.get('status') == 'n/a':
                    return not_applicable(res, fib.get('reason'))
                if ctx.get('fibers_trace') is None:
                    return skip(res, 'no fibers trace' + (f" ({fib.get('reason')})" if fib.get('reason') else ''))
                if not tool('csvexport'):
                    return skip(res, f'no tracy-csvexport at {tt.get("csvexport")} (TRACY_CSVEXPORT)')
                counts = zone_csv(res, 'fibers', ctx['fibers_trace'])
                if counts is None:
                    return fail(res, 'tracy-csvexport failed')
                zone_names = counts.pop('zone_names')
                facts.update(counts)
                facts['csv_zones'] = counts['zones']
                info, why = analyse(res, 'fibers', ctx['fibers_trace'])
                if info is None:
                    skip(res, f'cannot inspect the trace: {why}')
                else:
                    trace_facts(res, info)
                fmt.h(f"zones {facts['zones']} (csvexport {facts['csv_zones']}), distinct {facts['distinct_zone_names']}, "
                      f"??? {facts['unknown_zones']}, messages {facts.get('messages')}, "
                      f"plots {facts.get('plots')}, frames {facts.get('frames')}")
                if not facts['csv_zones']:
                    fail(res, 'fibers trace has 0 zones')
                if facts['unknown_zones']:
                    fail(res, f"fibers trace has {facts['unknown_zones']} ??? zones")
                # The zones fibers.gd makes (tests/tracy_harness/README.md, Fibers).
                expected = ('walker_step', 'wave_step', 'chain_before', 'inner_before', 'ping_handler', 'frame_work')
                missing = [z for z in expected if z not in zone_names]
                facts['harness_zones_missing'] = missing
                if missing:
                    fail(res, f'fibers trace lacks the harness zones {missing}')
                metric('counts', 'fibers_zones', facts['csv_zones'], exact=False)
                return res

            def stage_silenced():
                # Launched without --tracy, the engine sends nothing. A GPU context entry is allowed.
                res = result()
                gate = capture_gate(res, need_silent_client=True, needs_project=True)
                if gate:
                    return gate
                script = harness('fibers_gd')
                if not script or not script.is_file():
                    return skip(res, f'no fibers harness at {script}')
                trace, _ = capture_run(res, 'silenced', script_cmd(script, unsilence=False))
                if trace is None or res['status'] != 'pass':
                    return res
                info, why = analyse(res, 'silenced', trace)
                if info is None:
                    return skip(res, f'cannot inspect the trace: {why}')
                trace_facts(res, info)
                if res['facts']['capture_zones']:
                    fail(res, f"tracy-capture reports {res['facts']['capture_zones']} zones")
                if info['zones']:
                    fail(res, f"{info['zones']} zones while silenced")
                if info['gpu_zones']:
                    fail(res, f"{info['gpu_zones']} GPU zones while silenced")
                if info['messages']:
                    fail(res, f"{info['messages']} messages while silenced")
                if info['engine_plots']:
                    fail(res, f"{info['engine_plots']} engine plots while silenced")
                # Allowed: Tracy's CPU-usage plot (SysTime) and the 3 frames the 0.14.1
                # server adds at handshake and connect, all at or before the client's first time.
                first = info['first_time']
                if info['frames'] > 3 or (info['frames'] and first is not None
                                          and info['last_frame'] > first + 1e-6):
                    fail(res, f"{info['frames']} frames, beyond the 3 server frames")
                return res

            def stage_toggle():
                # Profiler.set_capture_enabled on at frame 100, off at 200: zones only in between.
                res = result()
                facts = res['facts']
                gate = capture_gate(res, need_silent_client=True, needs_project=True)
                if gate:
                    return gate
                script = harness('toggle_gd')
                if not script or not script.is_file():
                    return skip(res, f'no toggle harness at {script}')
                trace, eng = capture_run(res, 'toggle', script_cmd(script, unsilence=False))
                if trace is None or res['status'] != 'pass':
                    return res
                for line in ('UNSILENCE request at frame 100', 'SILENCE request at frame 200', 'END at frame 300'):
                    if line not in eng['out']:
                        fail(res, f'engine output lacks {line!r}')
                info, why = analyse(res, 'toggle', trace)
                if info is None:
                    return skip(res, f'cannot inspect the trace: {why}')
                trace_facts(res, info)
                msgs = info['message_list']
                starts, stops = info['capture_started_at'], info['capture_stopped_at']
                if not starts:
                    fail(res, "no 'Godot Tracy capture started' message")
                if not stops:
                    fail(res, "no 'Godot Tracy capture stopped' message")
                if not info['zones']:
                    fail(res, 'no zones between the boundaries')
                eps = 1e-5   # the analyser prints microseconds
                if starts and info['first_zone'] is not None and info['first_zone'] < starts[0] - eps:
                    fail(res, f"a zone starts at {info['first_zone']}, before the start at {starts[0]}")
                if stops:
                    stop_t = stops[-1]
                    late_msgs = [msg for t, _, msg in msgs if t > stop_t]
                    facts['messages_after_stop'] = len(late_msgs)
                    facts['zones_after_stop'] = int(info['last_zone'] is not None and info['last_zone'] > stop_t + eps)
                    # Plot points after the stop are recorded, not judged.
                    facts['engine_plots_after_stop'] = sum(
                        1 for ptype, _, last in info['plot_list']
                        if ptype != 'SysTime' and last is not None and last > stop_t)
                    if late_msgs:
                        fail(res, f'{len(late_msgs)} messages after capture stopped: {late_msgs[:3]}')
                    if facts['zones_after_stop']:
                        fail(res, f"a zone starts at {info['last_zone']}, after the stop at {stop_t}")
                if starts:
                    facts['engine_messages_before_start'] = sum(
                        1 for t, srcid, _ in msgs if t < starts[0] and srcid == 0)
                # Headless, so no GPU zones are expected; any there must be inside the window.
                if info['gpu_zones'] and starts and stops and tool('csvexport'):
                    times = gpu_zone_times(res, 'toggle', trace) or []
                    outside = [t for t in times if t < starts[0] - eps or t > stops[-1] + eps]
                    facts['gpu_zones_outside_window'] = len(outside)
                    if outside:
                        fail(res, f'{len(outside)} GPU zones outside the unsilenced window')
                return res

            def gpu_frame_gap(times):
                # Zones inside one GPU frame sit near the median gap. The gap
                # before the next frame is many times larger (about 0.05 ms
                # versus 0.64 ms on the late_gpu capture). 20x the median
                # falls between the two. The floor covers tied timestamps.
                xs = sorted(times)
                gaps = sorted(b - a for a, b in zip(xs, xs[1:]) if b > a)
                if not gaps:
                    return 1e-3
                return max(gaps[len(gaps) // 2] * 20.0, 1e-4)

            def gpu_frame_period(times, split_gap):
                # The median gap that separates frames. split_gap is the smaller
                # gap between zones inside one frame, so those are left out.
                xs = sorted(times)
                gaps = sorted(b - a for a, b in zip(xs, xs[1:]) if b - a > split_gap)
                if not gaps:
                    return 1e-3
                return gaps[len(gaps) // 2]

            def split_gpu_silence(times, stop_t, start_t, eps):
                # The stop message is written and capture turns off before the
                # frame mark. These times are when the GPU started the pass, so
                # a frame the CPU already submitted can start after the message.
                # frame_queue_size is 2 or 3 with a surface, so that many frames
                # can still start. A burst after that queue has drained was
                # submitted while silenced.
                before = [t for t in times if t <= stop_t + eps]
                mid = sorted(t for t in times if stop_t + eps < t < start_t - eps)
                after = [t for t in times if t >= start_t - eps]
                if len(mid) < 2:
                    return before, mid, [], after
                gap = gpu_frame_gap(before or mid)
                frame = gpu_frame_period(before or mid, gap)
                max_bursts = 3
                drain = max(frame * 3.0, 5e-3)
                bursts = [[mid[0]]]
                for t in mid[1:]:
                    if t - bursts[-1][-1] > gap:
                        bursts.append([t])
                    else:
                        bursts[-1].append(t)
                kept = []
                prev_end = stop_t
                for burst in bursts:
                    if len(kept) >= max_bursts or burst[0] - prev_end > drain:
                        break
                    kept.append(burst)
                    prev_end = burst[-1]
                in_flight = [t for burst in kept for t in burst]
                return before, in_flight, mid[len(in_flight):], after

            def gpu_run_checks(sub, mode, info, times):
                # tests/tracy_harness/README.md, "Late GPU start, runs A to D".
                sf = sub['facts']
                eps = 1e-5
                starts, stops = info['capture_started_at'], info['capture_stopped_at']
                if not info['gpu_contexts']:
                    fail(sub, 'no GPU context in the trace')
                elif info['gpu_context_names'] is not None and not any(
                        n.endswith('(Vulkan)') for n in info['gpu_context_names']):
                    fail(sub, f"no ctx type=Vulkan line (contexts: {info['gpu_context_names']})")
                if mode == 'A':
                    if not info['gpu_zones']:
                        fail(sub, 'no GPU zones with --tracy from launch')
                elif mode == 'B':
                    if not starts:
                        return fail(sub, "no 'Godot Tracy capture started' message")
                    sf['gpu_zones_before_start'] = sum(1 for t in times if t < starts[0] - eps)
                    sf['gpu_zones_after_start'] = len(times) - sf['gpu_zones_before_start']
                    if sf['gpu_zones_before_start']:
                        fail(sub, f"{sf['gpu_zones_before_start']} GPU zones before the unsilence")
                    if not sf['gpu_zones_after_start']:
                        fail(sub, 'no GPU zones after the late unsilence')
                    if info['first_zone'] is not None and info['first_zone'] < starts[0] - eps:
                        fail(sub, f"a CPU zone at {info['first_zone']}, before the unsilence at {starts[0]}")
                elif mode == 'C':
                    restart = [t for t in starts if stops and t > stops[0]]
                    if not stops or not restart:
                        return fail(sub, "missing 'Godot Tracy capture stopped' then 'started' messages")
                    stop_t, start_t = stops[0], restart[0]
                    before, in_flight, silenced, after = split_gpu_silence(times, stop_t, start_t, eps)
                    sf['gpu_zones_before_stop'] = len(before)
                    sf['gpu_zones_in_flight'] = len(in_flight)
                    sf['gpu_zones_while_silenced'] = len(silenced)
                    sf['gpu_zones_after_restart'] = len(after)
                    if silenced:
                        fail(sub, f"{len(silenced)} GPU zones while silenced")
                    if not before:
                        fail(sub, 'no GPU zones before the silence')
                    if not after:
                        fail(sub, 'no GPU zones after the unsilence')
                else:   # D: silenced throughout; only the GPU context entry may be there.
                    if info['gpu_zones']:
                        fail(sub, f"{info['gpu_zones']} GPU zones while silenced")
                    if info['zones']:
                        fail(sub, f"{info['zones']} CPU zones while silenced")
                    if info['messages']:
                        fail(sub, f"{info['messages']} messages while silenced")
                return sub

            def stage_log():
                # Headless. On lists only log: the harness lines are coloured log messages.
                # Off lists messages and not log: prints stay out. A warning or an error
                # still arrives as a Tracy message, with the log color and Info severity.
                # tests/tracy_harness/README.md, Log.
                # The analyser stores color as 0xFFBBGGRR. No color is 0xFFFFFFFF.
                res = result()
                facts = res['facts']
                gate = capture_gate(res, needs_project=True)
                if gate:
                    return gate
                defines = ctx.get('defines')
                log_built = ('TRACY_LOG_ENABLED' in defines) if defines else scons_opt('tracy_log') != 'no'
                if not log_built:
                    return not_applicable(res, 'build has no log bridge (no TRACY_LOG_ENABLED)')
                script = harness('log_gd')
                if not script or not script.is_file():
                    return skip(res, f'no log harness at {script}')

                def stored_color(rrggbb):
                    if not rrggbb:
                        return 0xFFFFFFFF
                    red, green, blue = (rrggbb >> 16) & 0xFF, (rrggbb >> 8) & 0xFF, rrggbb & 0xFF
                    return 0xFF000000 | (blue << 16) | (green << 8) | red

                # Info 2, Warning 3, Error 4. Colors are the Godot 0xRRGGBB values.
                expect = (
                    ('log harness plain', stored_color(0), 2, False),
                    ('log harness printerr', stored_color(0xE08040), 3, False),
                    ('log harness rich', stored_color(0), 2, True),
                    ('WARNING: log harness warning', stored_color(0xE0C040), 3, False),
                    ('ERROR: log harness error', stored_color(0xE05050), 4, False),
                )
                runs = {}
                facts['runs'] = runs
                modes = (
                    ('on', tt.get('log_features') or 'log', True),
                    ('off', tt.get('log_off_features') or 'messages', False),
                )
                for mode, features, want in modes:
                    fmt.h(f'Log {mode}')
                    sub = result()
                    runs[mode] = sub
                    eng_cmd = [str(exe), '--headless']
                    if is_template():
                        eng_cmd += ['--path', str(stub_project())]
                    if ctx['silent_client'] is not False:
                        eng_cmd.append('--tracy')
                    eng_cmd += ['--script', str(Path(script).resolve()), '--tracy-features', features]
                    if tt.get('mask') is not None:
                        eng_cmd += ['--tracy-mask', tt['mask']]
                    trace, eng = capture_run(sub, f'log_{mode}', eng_cmd)
                    res['logs'] += sub['logs']
                    if dry:
                        fmt.h(f'log {mode}: dry')
                        continue
                    if eng is not None:
                        out = plain(eng['out'] + eng['err'])
                        if 'LOG_HARNESS action=quit' not in out:
                            fail(sub, "log.gd never printed 'LOG_HARNESS action=quit'")
                    if trace is not None:
                        info, why = analyse(sub, f'log_{mode}', trace)
                        if info is None:
                            skip(sub, f'cannot inspect the trace: {why}')
                        else:
                            trace_facts(sub, info)
                            msgs = info.get('tracy_msgs') or []
                            if want:
                                matched = 0
                                for needle, color, sev, reject_ansi in expect:
                                    hits = [m for m in msgs if needle in m['text']]
                                    if not hits:
                                        fail(sub, f'missing log message containing {needle!r}')
                                        continue
                                    ok = [m for m in hits if m['color'] == color and m['sev'] == sev]
                                    if not ok:
                                        shown = hits[0]
                                        fail(sub, f'{needle!r} has color={shown["color"]:08x} sev={shown["sev"]}, '
                                                  f'expected color={color:08x} sev={sev}')
                                    elif reject_ansi and any('\x1b' in m['text'] or '[38;' in m['text'] for m in ok):
                                        fail(sub, 'rich log message still has ANSI color codes')
                                    else:
                                        matched += 1
                                sub['facts']['log_hits'] = matched
                            else:
                                # Prints stay on the log feature. Warnings and errors also
                                # go out as Tracy messages when messages is on, so a normal
                                # capture still shows them. Tracy messages have no log
                                # level, so the analyser keeps severity at Info (2).
                                raw = ''
                                analysis = info.get('analysis')
                                if analysis:
                                    raw = Path(analysis).read_text(encoding='utf-8', errors='replace')
                                for needle in (
                                        'LOG_HARNESS',
                                        'log harness plain',
                                        'log harness printerr',
                                        'log harness rich',
                                ):
                                    if needle in raw:
                                        fail(sub, f'log is off but the trace still has {needle!r}')
                                matched = 0
                                for needle, color, _sev, _reject_ansi in expect:
                                    if not (needle.startswith('WARNING:') or needle.startswith('ERROR:')):
                                        continue
                                    hits = [m for m in msgs if needle in m['text']]
                                    if not hits:
                                        fail(sub, f'missing Tracy message containing {needle!r}')
                                        continue
                                    ok = [m for m in hits if m['color'] == color and m['sev'] == 2]
                                    if not ok:
                                        shown = hits[0]
                                        fail(sub, f'{needle!r} has color={shown["color"]:08x} sev={shown["sev"]}, '
                                                  f'expected color={color:08x} sev=2')
                                    else:
                                        matched += 1
                                sub['facts']['log_hits'] = matched
                    fmt.h(f"log {mode}: {sub['status']}, hits {sub['facts'].get('log_hits')}")
                for mode, sub in runs.items():
                    for why in sub['failures']:
                        res['failures'].append(f'{mode}: {why}')
                    if sub['status'] == 'fail':
                        res['status'] = 'fail'
                    elif sub['status'] == 'skip' and res['status'] == 'pass':
                        skip(res, sub['reason'])
                return as_dry(res) if dry else res

            def stage_frame_images():
                # Windowed run must send 320x180 thumbnails. The headless run of the
                # same script must send none. tests/tracy_harness/README.md, Frame images.
                res = result()
                facts = res['facts']
                gate = capture_gate(res, needs_project=True)
                if gate:
                    return gate
                defines = ctx.get('defines')
                images_built = ('TRACY_FRAME_IMAGES_ENABLED' in defines) if defines else scons_opt('tracy_frame_images') != 'no'
                frames_built = ('TRACY_FRAMES_ENABLED' in defines) if defines else scons_opt('tracy_frames') != 'no'
                if not images_built:
                    return not_applicable(res, 'build has no frame images (no TRACY_FRAME_IMAGES_ENABLED)')
                if not frames_built:
                    return not_applicable(res, 'build has no frame marks (no TRACY_FRAMES_ENABLED)')
                script = harness('frame_images_gd')
                if not script or not script.is_file():
                    return skip(res, f'no frame image harness at {script}')
                display_env, why = ensure_display()
                if display_env is None:
                    return skip(res, why)
                facts['display'] = display_env.get('DISPLAY') or '(desktop)'
                facts['xvfb_cmd'] = ctx.get('xvfb_cmd')
                features = tt.get('frame_image_features') or 'frames,frame_images'
                minimum = int(tt.get('frame_image_min') or 20)
                runs = {}
                facts['runs'] = runs
                for mode, headless in (('window', False), ('headless', True)):
                    fmt.h(f'Frame images {mode}')
                    sub = result()
                    runs[mode] = sub
                    eng_cmd = [str(exe)]
                    if headless:
                        eng_cmd.append('--headless')
                    if is_template():
                        eng_cmd += ['--path', str(stub_project())]
                    # --tracy unsilences an on-demand build. A from-launch build has no such flag.
                    if ctx['silent_client'] is not False:
                        eng_cmd.append('--tracy')
                    eng_cmd += ['--script', str(Path(script).resolve()), '--tracy-features', features]
                    if tt.get('mask') is not None:
                        eng_cmd += ['--tracy-mask', tt['mask']]
                    trace, eng = capture_run(sub, f'frame_{mode}', eng_cmd, env=display_env)
                    res['logs'] += sub['logs']
                    if dry:
                        fmt.h(f'frame images {mode}: dry')
                        continue
                    if eng is not None:
                        out = plain(eng['out'] + eng['err'])
                        if 'action=quit' not in out:
                            fail(sub, "frame_images.gd never printed 'action=quit'")
                    if trace is not None:
                        info, why = analyse(sub, f'frame_{mode}', trace)
                        if info is None:
                            skip(sub, f'cannot inspect the trace: {why}')
                        else:
                            trace_facts(sub, info)
                            count = info.get('frame_images')
                            if count is None:
                                fail(sub, 'analyser printed no frameimages= count')
                            elif mode == 'headless':
                                if count:
                                    fail(sub, f'headless capture has {count} frame images')
                            else:
                                if not info.get('frames'):
                                    fail(sub, 'window capture has no frames')
                                sizes = info.get('frame_image_sizes') or []
                                if not sizes:
                                    fail(sub, 'analyser printed no FRAMEIMAGE lines')
                                sized = 0
                                for size in sizes:
                                    sized += size['count']
                                    if (size['w'], size['h'], size['flip']) != (320, 180, 0):
                                        fail(sub, f"frame image {size['w']}x{size['h']} flip={size['flip']}, "
                                                  f'expected 320x180 flip=0')
                                if sizes and sized != count:
                                    fail(sub, f'FRAMEIMAGE counts sum to {sized}, frameimages={count}')
                                if count < minimum:
                                    fail(sub, f'{count} frame images, expected at least {minimum}')
                                if sub['status'] == 'pass':
                                    metric('frame_images', 'frame_images', count, exact=False)
                    fmt.h(f"frame images {mode}: {sub['status']}, images {sub['facts'].get('frame_images')}")
                for mode, sub in runs.items():
                    for why in sub['failures']:
                        res['failures'].append(f'{mode}: {why}')
                    if sub['status'] == 'fail':
                        res['status'] = 'fail'
                    elif sub['status'] == 'skip' and res['status'] == 'pass':
                        skip(res, sub['reason'])
                return as_dry(res) if dry else res

            def stage_gpu_late_start():
                # The late_gpu project, runs A to D. On whenever the build has the GPU
                # feature; skips only without a display or a Vulkan device.
                res = result()
                facts = res['facts']
                gate = capture_gate(res, need_silent_client=True, needs_project=True)
                if gate:
                    return gate
                defines = ctx.get('defines')
                gpu_built = ('TRACY_GPU_ENABLED' in defines) if defines else scons_opt('tracy_gpu') != 'no'
                if not gpu_built:
                    return not_applicable(res, 'build has no GPU instrumentation (no TRACY_GPU_ENABLED)')
                if scons_opt('vulkan') == 'no':
                    return not_applicable(res, 'build has no Vulkan driver (vulkan=no)')
                src_project = harness('late_gpu_project')
                if not src_project or not (src_project / 'project.godot').is_file():
                    return skip(res, f'no late_gpu project at {src_project}')
                if not tool('csvexport'):
                    return skip(res, f'no tracy-csvexport at {tt.get("csvexport")} (TRACY_CSVEXPORT)')
                display_env, why = ensure_display()
                if display_env is None:
                    return skip(res, why)
                facts['display'] = display_env.get('DISPLAY') or '(desktop)'
                facts['xvfb_cmd'] = ctx.get('xvfb_cmd')
                # A copy keeps the import cache (.godot/) out of the source tree.
                proj = logdir / 'late_gpu-project'
                if not dry:
                    shutil.copytree(src_project, proj, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.godot'))
                runs = {}
                facts['runs'] = runs
                for mode, unsilence in (('A', True), ('B', False), ('C', True), ('D', False)):
                    fmt.h(f'GPU run {mode}')
                    sub = result()
                    runs[mode] = sub
                    eng_cmd = [str(exe), '--path', str(proj), '--rendering-driver', 'vulkan', '--verbose']
                    eng_cmd += ['--tracy'] if unsilence else []
                    eng_cmd += ['--tracy-features', tt.get('gpu_features') or 'zones,messages,gpu,frames']
                    if tt.get('mask') is not None:
                        eng_cmd += ['--tracy-mask', tt['mask']]
                    eng_cmd += ['--quit-after', str(tt.get('gpu_quit_after') or 320)]
                    trace, eng = capture_run(sub, f'gpu{mode}', eng_cmd, env={'LATE_GPU_MODE': mode, **display_env})
                    res['logs'] += sub['logs']
                    if dry:
                        continue
                    if eng is not None:
                        out = plain(eng['out'] + eng['err'])
                        m = re.search(r'^Vulkan [\d.]+ - .*? - Using Device.*$', out, re.M)
                        sub['facts']['vulkan_device'] = m.group(0).strip() if m else None
                        if not m:
                            # The machine has no usable Vulkan device: nothing to test here.
                            skip(sub, 'no Vulkan device line in the engine output')
                            return skip(res, f'no Vulkan device (run {mode}, see gpu{mode}-engine.stdout.log)')
                        if 'action=quit' not in out:
                            fail(sub, "late_gpu.gd never printed 'action=quit'")
                        if 'action=profiler_MISSING' in out:
                            fail(sub, 'no Profiler singleton')
                    if trace is not None:
                        info, why = analyse(sub, f'gpu{mode}', trace)
                        if info is None:
                            skip(sub, f'cannot inspect the trace: {why}')
                            return skip(res, f'cannot inspect the trace: {why}')
                        trace_facts(sub, info)
                        times = gpu_zone_times(sub, f'gpu{mode}', trace)
                        if times is None:
                            fail(sub, 'tracy-csvexport -g failed')
                            times = []
                        gpu_run_checks(sub, mode, info, times)
                        if mode in ('A', 'B', 'C') and sub['status'] == 'pass':
                            metric('gpu_late_start', f'gpu_{mode}_gpu_zones', info['gpu_zones'], exact=False)
                    for why in sub['failures']:
                        res['failures'].append(f'run {mode}: {why}')
                    if sub['status'] == 'fail':
                        res['status'] = 'fail'
                    fmt.h(f"run {mode}: {sub['status']}, gpu zones {sub['facts'].get('gpu_zones')}, "
                          f"contexts {sub['facts'].get('gpu_context_names')}")
                return as_dry(res) if dry else res

            # MARK: Best run
            def compare_best(stages):
                # best.json beside the per-commit folders keeps the best value of each count
                # so far. Under the best fails the stage: exact counts may not drop, timing
                # dependent ones may drop by the tolerance. A passing stage that beats the
                # best becomes the new best.
                best_path = log_root / 'best.json'
                try:
                    best = json.loads(best_path.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    best = {}
                best.setdefault('metrics', {})
                best['variant'] = build.get('variant')
                best['build'] = build.get('name')
                updated = []
                for m in ctx['metrics']:
                    res = stages[m['stage']]
                    prev = best['metrics'].get(m['key'])
                    entry = {'value': m['value'], 'best': prev['value'] if prev else None,
                             'best_commit': prev.get('commit') if prev else None}
                    if prev is not None and res['status'] == 'pass':
                        floor = prev['value'] if m['exact'] else prev['value'] * (1 - tolerance)
                        entry['floor'] = floor
                        if m['value'] < floor:
                            fail(res, f"{m['key']} {m['value']} is below the best run "
                                      f"({prev['value']} at {str(prev.get('commit'))[:10]}, floor {floor:g})")
                    res['facts'].setdefault('vs_best', {})[m['key']] = entry
                    if res['status'] == 'pass' and (prev is None or m['value'] > prev['value']):
                        best['metrics'][m['key']] = {
                            'value': m['value'], 'commit': head, 'log_dir': logdir.as_posix(),
                            'at': datetime.now().astimezone().isoformat(timespec='seconds')}
                        updated.append(m['key'])
                if updated and not dry:
                    best_path.write_text(json.dumps(best, indent=2) + '\n', encoding='utf-8')
                return {'path': best_path.as_posix(), 'updated': updated}

            # MARK: Report
            def capture_rows(stages):
                sources = [('fibers', stages.get('fibers_capture'), stages.get('counts')),
                           ('silenced', stages.get('silenced'), None),
                           ('toggle', stages.get('toggle'), None)]
                runs = ((stages.get('gpu_late_start') or {}).get('facts') or {}).get('runs') or {}
                sources += [(f'gpu{mode}', sub, None) for mode, sub in runs.items()]
                frame_runs = ((stages.get('frame_images') or {}).get('facts') or {}).get('runs') or {}
                sources += [(f'frame_{mode}', sub, None) for mode, sub in frame_runs.items()]
                log_runs = ((stages.get('log') or {}).get('facts') or {}).get('runs') or {}
                sources += [(f'log_{mode}', sub, None) for mode, sub in log_runs.items()]
                rows = []
                for name, cap, more in sources:
                    if not cap or 'engine_cmd' not in cap['facts']:
                        continue
                    facts = {**cap['facts'], **(more['facts'] if more else {})}
                    row = {'name': name, 'status': cap['status']}
                    for key in ('engine_cmd', 'tracy_flag', 'tracy_features', 'tracy_mask', 'vulkan_device',
                                'gpu_contexts', 'gpu_context_names', 'zones', 'gpu_zones', 'messages',
                                'plots', 'frames', 'frame_images', 'frame_image_sizes',
                                'capture_started_msg', 'capture_stopped_msg'):
                        row[key] = facts.get(key)
                    rows.append(row)
                return rows

            def yes_no(value):
                return '-' if value is None else ('yes' if value else 'no')

            def report_lines(summary):
                rep = summary['report']
                lines = [f"Tracy test report, {summary['finished']}",
                         f"binary:       {rep['binary']}",
                         f"commit:       {rep['commit']}",
                         f"build:        {rep['build']} (variant {rep['variant']})",
                         f"build_vars:   {' '.join(rep['build_vars'])}",
                         f"doctest:      {rep['doctest_filter']}",
                         f"--help mode:  {rep['help_mode']}",
                         f"runtime:      {rep['tracy_state'] or '(no Tracy state: line from the doctests)'}",
                         'captures:']
                for row in rep['captures']:
                    mask = row['tracy_mask']
                    names = row['gpu_context_names']
                    lines.append(f"  {row['name']} [{row['status']}]: {row['engine_cmd']}")
                    lines.append(f"    --tracy {yes_no(row['tracy_flag'])}, --tracy-features {row['tracy_features']}, "
                                 f"--tracy-mask {'(not passed)' if mask is None else mask}")
                    if row['vulkan_device']:
                        lines.append(f"    {row['vulkan_device']}")
                    lines.append(f"    gpu contexts {row['gpu_contexts']}{': ' + ', '.join(names) if names else ''}; "
                                 f"zones {row['zones']}, gpu zones {row['gpu_zones']}, messages {row['messages']}, "
                                 f"plots {row['plots']}, frames {row['frames']}, frame images {row['frame_images']}, "
                                 f"capture started/stopped msgs "
                                 f"{yes_no(row['capture_started_msg'])}/{yes_no(row['capture_stopped_msg'])}")
                    sizes = row.get('frame_image_sizes') or []
                    if sizes:
                        lines.append('    ' + ', '.join(
                            f"{s['count']} x {s['w']}x{s['h']} flip={s['flip']}" for s in sizes))
                lines.append('stages:')
                for name in stage_names:
                    res = summary['stages'][name]
                    need = 'required' if name in summary['required'] else 'optional'
                    lines.append(f"  {name:<15} {res['status']:<5} {need}"
                                 f"{'  (' + res['reason'] + ')' if res['reason'] else ''}")
                    for why in res['failures']:
                        lines.append(f'      - {why}')
                    for key, cmp in (res['facts'].get('vs_best') or {}).items():
                        lines.append(f"      {key} {cmp['value']} (best before this run: {cmp['best']})")
                best = summary['best']
                lines.append(f"best run:     {best['path']}"
                             f"{' (updated: ' + ', '.join(best['updated']) + ')' if best['updated'] else ''}")
                lines.append(f"logs:         {summary['log_dir']}")
                lines.append(summary['line'])
                return lines

            # MARK: Run
            if not build.get('can_test'):
                fmt.h(f"Skip test: {toolchain.get('host', '')} cannot run this binary")
            else:
                platform_name = scons_opt('platform') or ''
                if platform_name in ('linux', 'bsd'):
                    platform_name = 'linuxbsd'
                build_dir = buildtool.get('build_dir') or (project['path'] / build['source_dir'])
                source_dir = Path(build_dir)
                exe = test_binary(source_dir / 'bin', platform_name)
                if not exe.is_file():
                    fmt.h(f'Missing test binary {exe.as_posix()}')
                    timer.status = TaskStatus.FAILED
                else:
                    is_tracy = scons_opt('profiler') == 'tracy'
                    head = git_head()
                    short = head[:10] if head else ('dry' if dry else 'unknown')
                    log_root = (Path(tt['log_root']) if tt.get('log_root')
                                else Path(project['path']) / 'logs-test' / (build.get('name') or build['source_dir']))
                    # One folder per commit; captured .tracy files are kept there (a rerun replaces them).
                    logdir = log_root / short
                    if not dry:
                        logdir.mkdir(parents=True, exist_ok=True)
                    variant = build.get('variant') or 'default'
                    required_map = tt.get('required') or {}
                    required = list(required_map.get(variant, required_map.get('default', stage_names)))
                    ctx = {'stages': {}, 'metrics': [], 'silent_client': None, 'help_mode': None,
                           'tracy_state': None, 'defines': None, 'fibers_trace': None, 'help_res': result(),
                           'doctest_filter': tt.get('doctest') or '*[Profiling]*'}
                    flow_started = time.monotonic()
                    fmt.h(f'Test binary: {exe.as_posix()}')
                    fmt.h(f'Commit: {head}')
                    fmt.h(f"build_vars: {' '.join(buildtool.get('build_vars', []))}")
                    fmt.h(f"Variant {variant}, required stages: {', '.join(required)}")
                    fmt.h(f"Doctest filter: {ctx['doctest_filter']}")
                    fmt.h(f'Test logs: {logdir.as_posix()}')

                    stage_funcs = {'version': stage_version, 'tracy_defines': stage_tracy_defines,
                                   'doctest': stage_doctest, 'fibers_capture': stage_fibers_capture,
                                   'counts': stage_counts, 'silenced': stage_silenced, 'toggle': stage_toggle,
                                   'log': stage_log,
                                   'frame_images': stage_frame_images,
                                   'gpu_late_start': stage_gpu_late_start}
                    stages = ctx['stages']
                    try:
                        for name in stage_names:
                            fmt.h(f'Stage: {name}')
                            try:
                                if name == 'fibers_capture' and is_tracy and not dry:
                                    probe_help()
                                stages[name] = stage_funcs[name]()
                            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
                                stages[name] = fail(result(), f'{type(e).__name__}: {e}')
                    finally:
                        stop_display()
                    best_info = compare_best(stages)

                    counts = {}
                    for name in stage_names:
                        counts[stages[name]['status']] = counts.get(stages[name]['status'], 0) + 1
                    required_skips = [n for n in required if stages[n]['status'] == 'skip']
                    if counts.get('fail'):
                        outcome = 'fail'
                    elif required_skips:
                        outcome = 'inconclusive'
                    elif dry:
                        outcome = 'dry'
                    else:
                        outcome = 'pass'
                    parts = [f'{counts[s]} {s}' for s in ('pass', 'fail', 'skip', 'n/a', 'dry') if counts.get(s)]
                    grouped = {}
                    for n in required_skips:
                        grouped.setdefault(stages[n]['reason'], []).append(n)
                    reasons = '; '.join(f"{why} [{', '.join(names)}]" for why, names in grouped.items())
                    line = f"TEST {outcome} {', '.join(parts)}{f' ({reasons})' if reasons else ''}"

                    test_summary = {
                        'result': outcome,
                        'line': line,
                        'finished': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'binary': exe.as_posix(),
                        'commit': head,
                        'log_dir': logdir.as_posix(),
                        'secs': round(time.monotonic() - flow_started, 3),
                        'required': required,
                        'report': {'binary': exe.as_posix(), 'commit': head, 'build': build.get('name'),
                                   'variant': variant, 'build_vars': list(buildtool.get('build_vars', [])),
                                   'doctest_filter': ctx['doctest_filter'], 'help_mode': ctx['help_mode'],
                                   'silent_client': ctx['silent_client'], 'tracy_state': ctx['tracy_state'],
                                   'captures': capture_rows(stages)},
                        'stages': stages,
                        'best': best_info,
                    }
                    text = '\n'.join(report_lines(test_summary)) + '\n'
                    fmt.h('Report')
                    print(text, end='')
                    if not dry:
                        (logdir / 'summary.json').write_text(json.dumps(test_summary, indent=2, default=str),
                                                             encoding='utf-8')
                        (logdir / 'report.txt').write_text(text, encoding='utf-8')
                    # inconclusive is not a failure; only a failed stage fails the step.
                    timer.status = TaskStatus.FAILED if outcome == 'fail' else TaskStatus.COMPLETED

        stats['test'] = timer.get_dict()
        if test_summary is not None:
            stats['test']['summary'] = {k: test_summary[k] for k in ('result', 'line', 'log_dir', 'secs')}
            print(test_summary['line'])
        config['ok'] = timer.ok() and config['ok']

def install_scons():
    """
    Copy a build's launch files into GODOT_INSTALL_PATH.
    Last step. Runs when install was requested and every earlier step succeeded.
    """
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    buildtool:dict = {}
    project:dict = {}
    # start_script

    # MARK: Install
    #[================================[ Install ]================================]
    # Launch files only: the engine binary, its console twin, matching symbol
    # files, shared libraries next to them, and godot_profiling<suffix>.gen.h
    # when the build produced it. The suffix matches the engine binary so
    # several builds can share the install directory. Import libraries stay
    # in the build tree.
    if 'install' not in opts['build_actions']:
        pass
    else:
        test_result = ((stats.get('test') or {}).get('summary') or {}).get('result')
        if not config['ok'] or test_result not in (None, 'pass', 'dry'):
            why = f'test {test_result}' if test_result not in (None, 'pass', 'dry') else 'an earlier step failed'
            fmt.h(f'Skip install: {why}')
        else:
            console.set_window_title(f'Install - {build["name"]}')

            with Timer(name='install') as timer, fmt.Section('Install'):
                import shutil

                def scons_opt(name):
                    value = None
                    for item in buildtool.get('build_vars', []):
                        key, sep, val = str(item).partition('=')
                        if sep and key == name:
                            value = val
                    return value

                def engine_stem():
                    # Same suffix SConstruct builds, including detect.py's .llvm prefix.
                    platform_name = scons_opt('platform') or ''
                    if platform_name in ('linux', 'bsd'):
                        platform_name = 'linuxbsd'
                    parts = ['godot', platform_name, scons_opt('target') or build.get('target', '')]
                    if scons_opt('dev_build') == 'yes':
                        parts.append('dev')
                    if scons_opt('precision') == 'double':
                        parts.append('double')
                    parts.append(scons_opt('arch') or '')
                    if scons_opt('threads') == 'no':
                        parts.append('nothreads')
                    extra = scons_opt('extra_suffix') or ''
                    if scons_opt('use_llvm') == 'yes':
                        extra = f'llvm.{extra}' if extra else 'llvm'
                    if extra:
                        parts.append(extra)
                    stem = '.'.join(part for part in parts if part)
                    return platform_name, stem

                dest_root = build.get('godot_install')
                if not dest_root:
                    fmt.h('ERROR: GODOT_INSTALL_PATH is unset (godot/paths.local.py)')
                    timer.status = TaskStatus.FAILED
                else:
                    dest = Path(dest_root).expanduser()
                    if not dest.is_absolute():
                        dest = Path(project['path']) / dest
                    dest = dest.resolve()
                    build_dir = Path(buildtool.get('build_dir') or (Path(project['path']) / build['source_dir'])).resolve()
                    bin_dir = build_dir / 'bin'
                    fmt.h(f'Destination: {dest.as_posix()}')
                    if dest == build_dir or build_dir in dest.parents or dest in build_dir.parents:
                        fmt.h(f'ERROR: install path {dest.as_posix()} overlaps the build tree')
                        timer.status = TaskStatus.FAILED
                    elif not bin_dir.is_dir():
                        fmt.h(f'ERROR: missing {bin_dir.as_posix()}')
                        timer.status = TaskStatus.FAILED
                    else:
                        platform_name, stem = engine_stem()
                        files = []
                        apps = []
                        if platform_name == 'windows':
                            for path in bin_dir.iterdir():
                                if path.is_file() and (path.name == stem or path.name.startswith(stem + '.')):
                                    if path.suffix.lower() in ('.exe', '.pdb') or path.name.endswith('.debugsymbols'):
                                        files.append(path)
                        else:
                            binary = bin_dir / stem
                            if binary.is_file():
                                files.append(binary)
                            for path in bin_dir.iterdir():
                                if path.is_file() and path.name.startswith(stem + '.') and path.name.endswith('.debugsymbols'):
                                    files.append(path)
                            app = bin_dir / f'{stem}.app'
                            if app.is_dir():
                                apps.append(app)
                            if not apps:
                                apps = [path for path in bin_dir.iterdir() if path.is_dir() and path.suffix == '.app']
                        for path in bin_dir.iterdir():
                            if not path.is_file():
                                continue
                            name = path.name
                            if path.suffix.lower() == '.dll' or name.endswith('.dylib') or '.so' in name:
                                files.append(path)
                        # stem is "godot" plus the engine suffix. The header uses that suffix
                        # so a later install does not overwrite another build's copy.
                        header = bin_dir / f'godot_profiling{stem.removeprefix("godot")}.gen.h'
                        if header.is_file():
                            files.append(header)
                        files = sorted(set(files))
                        has_engine = bool(apps) or any(
                            path.suffix.lower() == '.exe' or path.name == stem for path in files)
                        if not has_engine:
                            fmt.h(f'ERROR: no engine binary named {stem} in {bin_dir.as_posix()}')
                            timer.status = TaskStatus.FAILED
                        elif opts['dry']:
                            fmt.h(f'dry-run: {len(files)} files, {len(apps)} app bundles')
                            for path in files:
                                fmt.hu(path.name)
                            for path in apps:
                                fmt.hu(path.name)
                        else:
                            dest.mkdir(parents=True, exist_ok=True)
                            for path in files:
                                shutil.copy2(path, dest / path.name)
                                fmt.hu((dest / path.name).as_posix())
                            for path in apps:
                                target = dest / path.name
                                if target.exists():
                                    shutil.rmtree(target)
                                shutil.copytree(path, target)
                                fmt.hu(target.as_posix())
                            fmt.h(f'Installed {len(files)} files to {dest.as_posix()}')

            stats['install'] = timer.get_dict()
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

    # After build and test. show_stats is appended later and exits when this failed.
    config.verbs.append('install')
    if GODOT_INSTALL_PATH:
        setattr(config, 'godot_install', GODOT_INSTALL_PATH)
    config.script_parts.append(install_scons)

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
# Automatic GDScript zones stay on: the coroutine fiber path is compiled
# only with them, and --tracy-features cannot add code the build left out.
# Frame images and the log bridge stay on for the same reason. They stay
# silent until --tracy-features lists them. log is not part of
# TRACY_TEST_FEATURES, so the other captures do not forward every engine print.
_TRACY_FEATURES = (
    ("tracy_zones", "yes"),
    ("tracy_plots", "yes"),
    ("tracy_messages", "yes"),
    ("tracy_memory", "yes"),
    ("tracy_locks", "yes"),
    ("tracy_gpu", "yes"),
    ("tracy_gdscript_auto", "yes"),
    ("tracy_frames", "yes"),
    ("tracy_frame_images", "yes"),
    ("tracy_log", "yes"),
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
    if not TRACY_REF or cfg.source_def.ref != TRACY_REF:
        return False
    scons = cfg.buildtool

    # Enable the tracy profiler.
    scons.build_vars.append("profiler=tracy")

    # profiler_path: Path to the Profiler framework. Only tracy and perfetto are supported at the moment.
    if not TRACY_PROFILER_PATH:
        print("Skipping tracy build: TRACY_PROFILER_PATH is not set (see godot/paths.local.*.example)")
        return False
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
            # Templates default to disable_path_overrides=yes, which rejects --path,
            # --main-pack and --script. The test stages need them as the editor has them.
            if str(getattr(cfg, 'target', '')).startswith('template'):
                cfg.buildtool.build_vars.append('disable_path_overrides=no')
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


