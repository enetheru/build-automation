import os
from types import SimpleNamespace

from src.config import git_base

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    import copy
    from src.expand_config import expand_host_env, expand_cmake, expand_func
    from share.snippets import source_git, show_stats

    from godot.config import godot_platforms, godot_arch

    from src.compiler_cache import apply_cmake_compiler_cache
    from src.config import (git_base, project_base, build_base, cmake_base, gopts)

    # main builds one library. GODOTCPP_TARGET is a cache string, so each
    # flavor is its own configure. flatc is a second --target of that cache.
    git_source = SimpleNamespace({**vars(git_base), **{
        'name': 'git',
        'url': "https://github.com/enetheru/godot-flatbuffers.git/",
        'ref': "main"
    }})
    project = SimpleNamespace({**vars(project_base), **{
        'name':'gdflatbuffers',
        'sources':{
            'git': git_source,
            # Only the libtracy configs use it. See LIBTRACY_SOURCE.
            'tracy': LIBTRACY_SOURCE,
        },
        'buildtools':{
            'cmake':SimpleNamespace(**{
                **vars(cmake_base),
                'targets': ['flatc', 'godot-flatbuffers'],
                # One configure, then cmake --build --config. Single-config
                # Ninja and MinGW Makefiles would repeat that as three folders.
                'generators': {
                    'msvc': 'Visual Studio 17 2022',
                    'ninja-multi': 'Ninja Multi-Config',
                },
            }),
        },
    }})
    # project_base keeps a view of the toolchain dict from before -t filters it.
    project.toolchains = gopts.toolchains.values()


    build_start = SimpleNamespace({**vars(build_base), **{
        'verbs':['source'],
        'script_parts':[source_git],
        'platform':'win32',
        'arch':'x86_64',
        # build_base leaves source_def empty. Fetch reads remote from it.
        'source_def': git_source,
    }})

    builds = expand_host_env( build_start, project )

    # generic_toolchain_expand records the pair on the toolchain.
    # Android's expand already set the ABI and platform.
    for build in builds:
        toolchain = build.toolchain
        if hasattr(toolchain, 'target_arch'):
            build.arch = toolchain.target_arch
            build.platform = toolchain.target_platform

    builds = expand_func( builds, expand_cmake )

    split = []
    for build in builds:
        for target in ('template_release', 'template_debug', 'editor'):
            cfg = copy.deepcopy(build)
            cfg.godotcpp_target = target
            cfg.buildtool.config_vars.append(f'-DGODOTCPP_TARGET={target}')
            split.append(cfg)
            # Three more folders per platform: the same configure against the
            # matching libtracy Godot bin. The default folders stay as they are.
            tracy = libtracy_variant(cfg)
            if tracy is not None:
                split.append(tracy)
    builds = split

    # llvm, llvm-mingw, and mingw64 attach the CMake toolchain file here.
    for build in builds:
        configure = getattr(build.toolchain, 'configure', None)
        if configure is not None:
            configure(build)

    for build in builds:
        apply_cmake_compiler_cache(build)
        toolchain = build.toolchain.name
        raw_platform = build.platform
        arch = godot_arch[build.arch]
        platform = godot_platforms[raw_platform]

        cmake = build.buildtool
        # configuration_types means Debug/Release/RelWithDebInfo stay off the folder.
        if getattr(cmake, 'configuration_types', None):
            tool_name = f'{cmake.name}-{cmake.short_gen}'
        else:
            tool_name = f'{cmake.name}-{cmake.short_type}-{cmake.short_gen}'
        name_parts = [
            build.host,
            tool_name,
            toolchain if toolchain != 'emscripten' else None,
            platform if raw_platform not in ('android', 'emscripten') else None,
            arch if arch != 'wasm32' else None,
            build.godotcpp_target,
            getattr(build, 'variant', None),
        ]
        build.name = '.'.join(filter(None, name_parts))
        # libtracy configs check out the tracy source into their own worktree.
        build.source_dir = f'{build.host}.{getattr(build, "source_dir_suffix", "main")}'
        cmake.build_dir = build.name
        build.script_parts.append( show_stats )

    project.build_configs = {v.name: v for v in builds }
    return  project

# MARK: Paths
# Machine-specific paths live in gdflatbuffers/paths.local.py, which is
# gitignored (like godot/paths.local.py). To set up a machine, copy
#   gdflatbuffers/paths.local.box.example      (the Linux box)
# to gdflatbuffers/paths.local.py and edit it. Without that file the defaults
# below apply.
#
# GDFB_INSTALL_PREFIX: the `cmake --install --prefix` of the libtracy builds.
#   Relative paths resolve against the source worktree; the default 'install'
#   is <source>/install. A Tracy install takes the default build's slot in
#   flatbuffers.gdextension, so it must never target a shared Godot project:
#   libtracy Install refuses a prefix that holds project.godot, and the source
#   worktree itself or a folder above it.
GDFB_INSTALL_PREFIX: str = 'install'

# Names paths.local.py may set.
_LOCAL_OVERRIDES = (
    'GDFB_INSTALL_PREFIX',
)


def _load_local_paths() -> None:
    """Apply gdflatbuffers/paths.local.py, when present, over the defaults above."""
    import importlib.util
    import pathlib
    try:
        local = pathlib.Path(__file__).with_name('paths.local.py')
    except NameError:   # no __file__, nothing to look for
        return
    if not local.is_file():
        return
    spec = importlib.util.spec_from_file_location('gdflatbuffers_paths_local', local)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in _LOCAL_OVERRIDES:
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)


_load_local_paths()

# MARK: libtracy
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _ _ _    _                                                                │
# │ | (_) |__| |_ _ _ __ _ __ _  _                                             │
# │ | | | '_ \  _| '_/ _` / _| || |                                            │
# │ |_|_|_.__/\__|_| \__,_\__|\_, |                                            │
# │                           |__/                                             │
# ╰────────────────────────────────────────────────────────────────────────────╯
# The extension linked against the engine's shared Tracy client. Spec:
# godot-flatbuffers Notes/TracyExtension.md (branch tracy). One extra Ninja
# Multi-Config configure per GODOTCPP_TARGET, named with `libtracy`. The Godot
# bin, its header and its client library are found when the build script runs,
# because a Godot rebuild changes the defines hash and may change the version.

# CMake interface of the extension (godot-flatbuffers cmake/tracy.cmake, tracy branch
# 54a6325). Every option name the variant passes is here and nowhere else. The
# Tracy client comes only from the engine's bin; the extension never copies it.
# On MinGW the import library (.a) is all the configure needs.
LIBTRACY_CMAKE = {
    'enable':         'GDFB_ENABLE_TRACY',       # BOOL, ON for libtracy only. Default folders leave it unset.
    'header_dir':     'GODOT_TRACY_HEADER_DIR',  # dir of godot_profiling.gen.h (that target's Godot bin)
    'include_dir':    'TRACY_INCLUDE_DIR',       # Tracy public headers (<tracy/Tracy.hpp>)
    'client_library': 'TRACY_CLIENT_LIBRARY',    # what the extension links: MinGW import lib, or the .so
}

# Submodules the tracy source needs after checkout (godot-cpp stays FetchContent).
# The .gitmodules URL may be SSH; the rewrite makes the clone https, and is a
# no-op once the URL is https. It is passed per command, never written to config.
LIBTRACY_SUBMODULES = ['lib/flatbuffers']
LIBTRACY_SUBMODULE_GIT_CONFIG = ['url.https://github.com/.insteadOf=git@github.com:']

# Per-target override of the Godot bin, read by the build script. Set it to
# point a configure at a bin the runner did not build, for example on Linux.
#   GDFB_GODOT_TRACY_BIN_EDITOR, ..._TEMPLATE_DEBUG, ..._TEMPLATE_RELEASE
# GDFB_GODOT_TRACY_BIN applies to every target. A bin without that target's
# client library still fails, so a shared value cannot link the wrong target.
LIBTRACY_BIN_ENV = 'GDFB_GODOT_TRACY_BIN'

# The engine binary the libtracy launch uses. It must be a shared-client build:
# its dynamic section names the TracyClient library (readelf -d on Linux,
# objdump -p on Windows). A static-Tracy exe in the same bin is rejected.
# Pick one explicitly with $GDFB_GODOT_TRACY_EXE_<TARGET> or $GDFB_GODOT_TRACY_EXE:
# a file name in the Godot bin, or an absolute path. Without it, the platform's
# 'engine' globs are tried in order and the newest shared-client match wins.
LIBTRACY_EXE_ENV = 'GDFB_GODOT_TRACY_EXE'
LIBTRACY_EXE_CLIENT_RE = r'TracyClient\.'

# Header the engine installs in its bin. The variant reads the defines hash and
# GODOT_TRACY_SHARED_CLIENT from it.
LIBTRACY_HEADER = 'godot_profiling.gen.h'

# Per platform. Globs are relative to the Godot bin; {target} is the
# GODOTCPP_TARGET, {host} is short_host(). 'godot_glob' is a folder under the
# runner's godot project (<runner root>/godot): that target's plain libtracy
# build, any version. The newest version wins.
# 'link' is what TRACY_CLIENT_LIBRARY gets. 'runtime' is the client the engine
# loads and the extension shares; it stays in the Godot bin and is never copied
# next to the extension (a second copy risks two clients in one process).
# 'extension' is every built extension of that target, in <build dir>/bin and in
# the installed addon bin; LIBTRACY_OUTPUT_TAG picks the tracy ones. 'engine' is
# the Tracy engine binary in the Godot bin (the test step runs it).
LIBTRACY_PLATFORMS = {
    'win32': {
        'toolchains': ['mingw64'],     # the import library is MinGW
        'godot_glob': '{host}.mingw64.x86_64.windows.{target}.libtracy.*',
        'link':       ['obj/core/profiling/libTracyClient.windows.{target}.x86_64.*tracy.a'],
        'runtime':    ['TracyClient.windows.{target}.x86_64.*tracy.dll'],
        'extension':  'flatbuffers.windows.{target}.*.dll',
        # The real exe. The .console.exe wrapper is a second process.
        'engine':     ['godot.windows.{target}*.x86_64.*tracy.exe'],   # .tracy or .libtracy
    },
    'linux': {
        'toolchains': ['gcc'],
        # The runner does not build Godot on Linux yet. The env override above is the usual path.
        'godot_glob': '{host}.*.x86_64.linux.{target}.libtracy.*',
        # The engine loads this library by SONAME; the extension needs no RUNPATH.
        'link':       ['libTracyClient.linuxbsd.{target}*.x86_64*.so',
                       'obj/core/profiling/libTracyClient.linuxbsd.{target}*.x86_64*.so'],
        'runtime':    ['libTracyClient.linuxbsd.{target}*.x86_64*.so'],
        'extension':  'flatbuffers.linux.{target}.*.so',
        'engine':     ['godot.linuxbsd.{target}*.x86_64.*tracy'],      # .tracy or .libtracy
    },
}

# The build stays in the build tree (godot-flatbuffers CMakeLists.txt):
#   <build dir>/bin/flatbuffers.<platform>.<target>.<arch>.tracy[.<config>].<so|dll>
# and flatc beside it. Nothing is written into the source tree's addon.
LIBTRACY_BUILD_BIN = 'bin'

# `cmake --install` (cmake/gdextension_install.cmake, gdextension_merge.cmake)
# copies the library and flatc into <dest>/bin and merges one line into
# <dest>/flatbuffers.gdextension. <dest> is <prefix>/addons/<addon> when the
# prefix holds project.godot, else the prefix itself.
# The merge key drops `.tracy` and the config suffix, so a Tracy install takes
# the default build's slot for that platform and target; the last install wins.
# So a Tracy build is installed only into the runner's own prefix, never into a
# shared project: libtracy Install always passes --prefix GDFB_INSTALL_PREFIX.
LIBTRACY_ADDON_NAME = 'enetheru.flatbuffers-extension'
LIBTRACY_INSTALL_GDEXTENSION = 'flatbuffers.gdextension'
LIBTRACY_FLATC_GLOB = 'flatc*'                         # in <dest>/bin; installed 644, made executable

# The old in-source addon layout. Only the on-hold libtracy_test_headless reads
# these; the build no longer writes there.
LIBTRACY_EXTENSION_ADDON = f'project/addons/{LIBTRACY_ADDON_NAME}'
LIBTRACY_EXTENSION_BIN = f'{LIBTRACY_EXTENSION_ADDON}/bin'

# With GDFB_ENABLE_TRACY=ON the extension's outputs carry a `tracy` name part,
# e.g. flatbuffers.linux.editor.x86_64.tracy.so and a matching .gdextension, so
# they sit beside the default outputs. A file is a tracy output when one of its
# dot-separated name parts is this tag. This is the only place that knows it.
LIBTRACY_OUTPUT_TAG = 'tracy'

# What the extension prints at SCENE init (src/profiling.cpp), verbatim shape:
#   godot-flatbuffers tracy: godot_tracy_client_matches()=true client_version=0x000e01
#   client_defines_hash=0x... header_version=0x000e01 header_defines_hash=0x...
# (one line). A mismatch prints =false and pushes LIBTRACY_MISMATCH_WARNING.
LIBTRACY_MATCH_LINE_RE = (r'godot-flatbuffers tracy: godot_tracy_client_matches\(\)=(true|false)'
                          r' client_version=(0x[0-9a-f]+) client_defines_hash=(0x[0-9a-f]+)'
                          r' header_version=(0x[0-9a-f]+) header_defines_hash=(0x[0-9a-f]+)')
LIBTRACY_MISMATCH_WARNING = "godot-flatbuffers: the engine's TracyClient does not match"

# Extension zones as tracy-csvexport names them, and the sources they live in.
LIBTRACY_ZONES = (
    'FlatBuffer.get_root',
    'FlatBufferBuilder.finish',
    'FlatBufferBuilder.get_buffer',
    'FlatBufferBuilder allocate',
    'FlatBufferBuilder grow',
    'FlatBufferVerifier.set_buffer',
    'FlatBuffer.verify_vector_of_variant',
    'FlatBuffer.decode_variant packed',
)
LIBTRACY_ZONE_SOURCES = (
    'src/flatbuffer.cpp',
    'src/flatbufferbuilder.hpp', 'src/flatbufferbuilder.cpp',
    'src/flatbufferverifier.hpp',
    'src/profiling.hpp', 'src/profiling.cpp',
)
# Not wired into libtracy_test_headless yet (test work is on hold); its
# LIBTRACY_TEST patterns are still the earlier placeholders.

# The source the libtracy configs build. The default configs keep `git` above.
# GDFB_TRACY_SOURCE_URL / GDFB_TRACY_SOURCE_REF override it when the runner
# generates (for example a local bare). The runner fetches it into its own bare
# (gdflatbuffers/git) as remote `gitlab`; the repo is private, so the fetch needs a
# GitLab credential in the environment.
LIBTRACY_SOURCE = SimpleNamespace({**vars(git_base), **{
    'name': 'tracy',
    'remote': 'gitlab',
    'url': os.environ.get('GDFB_TRACY_SOURCE_URL') or 'https://gitlab.com/enetheru/godot-flatbuffers.git',
    'ref': os.environ.get('GDFB_TRACY_SOURCE_REF') or 'tracy',
}})

# Headless test on the editor Tracy engine (libtracy_test_headless).
# Env overrides, read by the build script:
#   GDFB_TRACY_PROJECT       Godot project to test. Default: <source>/project.
#                            It is copied per run, never written to.
#   GDFB_TRACY_TEST_SCRIPT   script to run, relative to the project or absolute.
#   GDFB_TRACY_RUNS          parent of the per-run folders.
LIBTRACY_TEST = {
    'targets': ['editor'],
    'script': 'addons/enetheru.test-runner/run_headless.gd',
    'project_env': 'GDFB_TRACY_PROJECT',
    'script_env': 'GDFB_TRACY_TEST_SCRIPT',
    'runs_env': 'GDFB_TRACY_RUNS',
    # The engine's on-demand client drops zones until a server is connected.
    # tracy-capture starts first; the engine starts this many seconds later.
    'settle_secs': 3,
    # Engine flags besides the script. One capture server per process.
    'engine_args': ['--headless', '--tracy'],
    # godot_tracy_client_matches() true: searched in the engine output and the
    # capture's messages (tracy-csvexport -m).
    # TODO(extension): replace with the exact line the extension prints or sends.
    'client_matches_pattern': r'godot_tracy_client_matches\(\)\W*(?:is\W*)?true',
    # An extension zone: a zone whose source file is under the extension's
    # src/ dir, or whose name matches this pattern.
    # TODO(extension): exact zone names (builder, verify, read) still to come.
    'zone_name_pattern': r'(?i)flatbuffer',
}


def _tracy_include_dir() -> str | None:
    """Tracy public headers, from the same TRACY_PROFILER_PATH the godot libtracy builds use."""
    from godot.config import TRACY_PROFILER_PATH, TRACY_VERSION, _tracy_version_at
    if not TRACY_PROFILER_PATH:
        print('Skipping gdflatbuffers libtracy: TRACY_PROFILER_PATH is not set (see godot/paths.local.*.example)')
        return None
    found = _tracy_version_at(TRACY_PROFILER_PATH)
    if found != TRACY_VERSION:
        print(f'Skipping gdflatbuffers libtracy: expected Tracy {TRACY_VERSION} at {TRACY_PROFILER_PATH}, found {found}')
        return None
    return f'{TRACY_PROFILER_PATH.rstrip("/")}/public'


def libtracy_variant( cfg:SimpleNamespace ) -> SimpleNamespace | None:
    """
    The libtracy copy of one per-target configure, or None where it does not apply.
    Paths that depend on the Godot build are left for libtracy_resolve.
    """
    import copy
    from src.config import gopts
    from src.expand_config import short_host

    spec = LIBTRACY_PLATFORMS.get(cfg.platform)
    if spec is None or cfg.toolchain.name not in spec['toolchains']:
        return None
    if cfg.arch != 'x86_64' or getattr(cfg.buildtool, 'short_gen', None) != 'ninja-multi':
        return None
    include_dir = _tracy_include_dir()
    if include_dir is None:
        return None

    from godot.config import TRACY_TEST as GODOT_TRACY_TEST

    tracy = copy.deepcopy(cfg)
    tracy.variant = 'libtracy'
    tracy.source_def = copy.deepcopy(LIBTRACY_SOURCE)
    tracy.source_dir_suffix = LIBTRACY_SOURCE.ref.replace('/', '-')
    target = tracy.godotcpp_target
    tracy.buildtool.config_vars.append(f'-D{LIBTRACY_CMAKE["enable"]}=ON')
    tracy.buildtool.config_vars.append(f'-D{LIBTRACY_CMAKE["include_dir"]}={include_dir}')
    tracy.libtracy = {
        'target': target,
        'cmake': dict(LIBTRACY_CMAKE),
        'header': LIBTRACY_HEADER,
        'include_dir': include_dir,
        'bin_env': [f'{LIBTRACY_BIN_ENV}_{target.upper()}', LIBTRACY_BIN_ENV],
        'godot_root': (gopts.path / 'godot').as_posix(),
        'godot_glob': spec['godot_glob'].format(host=short_host(), target=target),
        'link': [g.format(target=target) for g in spec['link']],
        'runtime': [g.format(target=target) for g in spec['runtime']],
        'extension': spec['extension'].format(target=target),
        'build_bin': LIBTRACY_BUILD_BIN,
        'install_prefix': GDFB_INSTALL_PREFIX,
        'addon_name': LIBTRACY_ADDON_NAME,
        'install_gdextension': LIBTRACY_INSTALL_GDEXTENSION,
        'flatc_glob': LIBTRACY_FLATC_GLOB,
        'submodules': list(LIBTRACY_SUBMODULES),
        'submodule_git_config': list(LIBTRACY_SUBMODULE_GIT_CONFIG),
        # Read only by the on-hold test step.
        'extension_addon': LIBTRACY_EXTENSION_ADDON,
        'extension_bin': LIBTRACY_EXTENSION_BIN,
        'output_tag': LIBTRACY_OUTPUT_TAG,
        'engine': [g.format(target=target) for g in spec['engine']],
        'exe_env': [f'{LIBTRACY_EXE_ENV}_{target.upper()}', LIBTRACY_EXE_ENV],
        'exe_client_re': LIBTRACY_EXE_CLIENT_RE,
        'test': {
            **LIBTRACY_TEST,
            'runs_default': (gopts.path / 'gdflatbuffers' / 'tracy-runs').as_posix(),
            # Capture tools and timeouts come from godot's Tracy settings (paths.local.py).
            'capture': GODOT_TRACY_TEST.get('capture'),
            'csvexport': GODOT_TRACY_TEST.get('csvexport'),
            'address': GODOT_TRACY_TEST.get('address'),
            'port': GODOT_TRACY_TEST.get('port'),
            'timeout': GODOT_TRACY_TEST.get('timeout'),
        },
    }

    # Submodules after the checkout, resolve before configure, install after
    # build, then the read-only check.
    from share.snippets import source_git, cmake_build
    parts = tracy.script_parts
    parts.insert(parts.index(source_git) + 1, libtracy_submodules)
    parts.insert(parts.index(cmake_configure_part()), libtracy_resolve)
    parts.insert(parts.index(cmake_build) + 1, libtracy_install)
    parts.append(libtracy_check)
    tracy.verbs.append('install')
    # Test action hooks: the headless test (editor); the bench is still a stub.
    tracy.verbs.append('test')
    parts += [libtracy_test_headless, libtracy_bench]
    return tracy


def cmake_configure_part():
    from share.snippets import cmake_configure
    return cmake_configure


# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
# The functions below run inside the generated build script. Only the body
# after `# start_script` is copied, so each one imports what it uses.

def libtracy_resolve():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: libtracy-Resolve
    #[===========================[ libtracy Resolve ]===========================]
    # Find this target's Godot libtracy bin, header and client library, and pass
    # them to the configure. Runs before cmake_configure, because a Godot
    # rebuild changes the defines hash and the version folder.
    import re as _re
    import glob as _glob

    tt = build['libtracy']
    wants = {'configure', 'build', 'install', 'test'} & set(opts['build_actions'])
    if config['ok'] and wants:
        with fmt.Section('libtracy Resolve'):
            def _missing(what, notes):
                fnf = FileNotFoundError(f'libtracy {tt["target"]}: {what}')
                for note in notes:
                    fnf.add_note(note)
                fmt.h(f'ERROR: libtracy {tt["target"]}: {what}')
                for note in notes:
                    fmt.hu(note)
                config['ok'] = False
                raise fnf

            def _version_key(folder):
                # '<prefix>.libtracy.4.7.2~' -> ((4, 7, 2), 1, mtime). The tilde is past that tag.
                suffix = folder.name.split('.libtracy.', 1)[1]
                m = _re.fullmatch(r'(\d+(?:\.\d+)*)(~?)', suffix)
                return (tuple(int(n) for n in m.group(1).split('.')), 1 if m.group(2) else 0, folder.stat().st_mtime)

            # 1. The Godot bin: env override, else the newest plain libtracy folder.
            bin_dir = None
            for name in tt['bin_env']:
                if os.environ.get(name):
                    bin_dir = Path(os.environ[name])
                    fmt.h(f'godot bin from ${name}: {bin_dir.as_posix()}')
                    break
            if bin_dir is None:
                root = Path(tt['godot_root'])
                pattern = tt['godot_glob']
                # Only <prefix>.libtracy.<version>; dev_build and tests copies are other builds.
                folders = [f for f in root.glob(pattern)
                           if f.is_dir() and _re.fullmatch(r'\d+(?:\.\d+)*~?', f.name.split('.libtracy.', 1)[1])]
                if not folders:
                    _missing('no Godot libtracy build folder', [
                        f'looked for {(root / pattern).as_posix()}',
                        f'build that godot libtracy target first, or set ${tt["bin_env"][0]} to its bin'])
                folder = max(folders, key=_version_key)
                if len(folders) > 1:
                    fmt.hu('candidates: ' + ', '.join(sorted(f.name for f in folders)))
                bin_dir = folder / 'bin'
                fmt.h(f'godot bin: {bin_dir.as_posix()}')
            if not bin_dir.is_dir():
                _missing('Godot bin is not a directory', [bin_dir.as_posix()])

            # 2. The header. The defines hash is the contract with the client library.
            header = bin_dir / tt['header']
            if not header.is_file():
                _missing(f'{tt["header"]} not found', [
                    f'looked in {bin_dir.as_posix()}',
                    'that bin is not a profiler=tracy build, or its header was not generated'])
            text = header.read_text(errors='replace')
            m = _re.search(r'#define\s+GODOT_TRACY_DEFINES_HASH\s+(\S+)', text)
            fmt.hu(f'header: {header.as_posix()}  defines hash: {m.group(1) if m else "not found"}')
            if not _re.search(r'#define\s+GODOT_TRACY_SHARED_CLIENT\b', text):
                _missing('the header has no GODOT_TRACY_SHARED_CLIENT', [
                    header.as_posix(),
                    'the engine was not built with tracy_as_shared=yes, so there is no client library to link'])

            # 3. The client library the extension links, and the one it loads.
            def _find(globs):
                for g in globs:
                    hits = sorted(_glob.glob(_glob.escape(bin_dir.as_posix()) + '/' + g))
                    if hits:
                        return Path(max(hits, key=os.path.getmtime))
                return None

            link = _find(tt['link'])
            if link is None:
                _missing('client library to link not found', [f'looked for {bin_dir.as_posix()}/{g}' for g in tt['link']])
            runtime = _find(tt['runtime'])
            if runtime is None:
                _missing('client runtime library not found', [f'looked for {bin_dir.as_posix()}/{g}' for g in tt['runtime']])
            fmt.hu(f'link:    {link.as_posix()}')
            fmt.hu(f'runtime: {runtime.as_posix()}')

            # 4. The engine exe: a shared-client build (it NEEDs the TracyClient).
            import subprocess as _sp

            def _client_needed(exe):
                # Names in the exe's dynamic section that match the TracyClient,
                # or None when no tool could read it.
                for cmd, line_re in ((['readelf', '-d', str(exe)], r'\(NEEDED\).*\[(.+)\]'),
                                     (['objdump', '-p', str(exe)], r'DLL Name:\s*(\S+)')):
                    try:
                        out = _sp.run(cmd, capture_output=True, text=True, timeout=60)
                    except (OSError, _sp.SubprocessError):
                        continue
                    if out.returncode != 0:
                        continue
                    names = _re.findall(line_re, out.stdout)
                    return [n for n in names if _re.search(tt['exe_client_re'], n)]
                return None

            chosen = None
            for name in tt['exe_env']:
                if os.environ.get(name):
                    p = Path(os.environ[name])
                    chosen = p if p.is_absolute() else bin_dir / p
                    fmt.h(f'engine from ${name}: {chosen.as_posix()}')
                    break
            if chosen is not None:
                candidates = [chosen]
                if not chosen.is_file():
                    _missing('engine exe not found', [chosen.as_posix()])
            else:
                candidates = []
                for g in tt['engine']:
                    candidates += sorted((p for p in bin_dir.glob(g) if p.is_file()),
                                         key=lambda p: p.stat().st_mtime, reverse=True)
                if not candidates:
                    _missing('no engine exe', [f'looked for {bin_dir.as_posix()}/{g}' for g in tt['engine']]
                             + [f'or set ${tt["exe_env"][0]}'])
            rejected = []
            engine = None
            for exe in candidates:
                needed = _client_needed(exe)
                if needed is None:
                    fmt.hu(f'WARNING: no readelf/objdump to check {exe.name}; accepted unchecked')
                    engine = exe
                    break
                if needed:
                    fmt.hu(f'engine NEEDED: {", ".join(needed)}')
                    if runtime.name not in needed:
                        # A bin can hold clients of several builds. Take the one this
                        # engine loads, when the linked file is that same library (Linux).
                        paired = [bin_dir / n for n in needed if (bin_dir / n).is_file()]
                        if paired and link == runtime:
                            fmt.hu(f'client {runtime.name} is not the one {exe.name} needs; using {paired[0].name}')
                            link = runtime = paired[0]
                        else:
                            _missing('engine and client do not match', [
                                f'{exe.as_posix()} needs {", ".join(needed)}',
                                f'resolved client: {runtime.as_posix()}'])
                    engine = exe
                    break
                rejected.append(f'{exe.as_posix()}: no NEEDED TracyClient (static Tracy, or no Tracy)')
            if engine is None:
                _missing('no shared-client engine exe', rejected + [f'pick one with ${tt["exe_env"][0]}'])
            fmt.hu(f'engine:  {engine.as_posix()}')
            tt['engine_path'] = engine

            cmake_names = tt['cmake']
            buildtool['config_vars'] += [
                f'-D{cmake_names["header_dir"]}={bin_dir.as_posix()}',
                f'-D{cmake_names["client_library"]}={link.as_posix()}',
            ]
            tt['bin_dir'] = bin_dir
            tt['runtime_path'] = runtime


def libtracy_submodules():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    # MARK: libtracy-Submodules
    #[==========================[ libtracy Submodules ]==========================]
    # The tracy source carries flatbuffers as a submodule. Init it after the
    # checkout. The URL rewrite is passed per command (git -c), never stored.
    tt = build['libtracy']
    if config['ok'] and 'source' in opts['build_actions'] and tt['submodules']:
        with fmt.Section('libtracy Submodules'), Timer(name='submodules') as timer:
            source = Path(build['source_path'])
            git_c = [a for kv in tt['submodule_git_config'] for a in ('-c', kv)]
            if source.is_dir():
                os.chdir(source)
            elif not opts['dry']:
                fmt.h(f'ERROR: no source worktree at {source.as_posix()}')
                timer.status = TaskStatus.FAILED
            if timer.ok():
                stream_command(['git', *git_c, 'submodule', 'update', '--init', '--', *tt['submodules']],
                               dry=opts['dry'])
                if not opts['dry']:
                    stream_command(['git', 'submodule', 'status', '--', *tt['submodules']])
        stats['submodules'] = timer.get_dict()
        config['ok'] = timer.ok()


def libtracy_install():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: libtracy-Install
    #[===========================[ libtracy Install ]===========================]
    # cmake --install into the runner's own prefix, <source>/install. The merge
    # key drops .tracy, so this replaces the default build's slot there; a shared
    # Godot project is never the prefix. Configurations install in recorded
    # order and the last one wins the slot (narrow with --config-regex).
    from src.select import chosen_config_types

    tt = build['libtracy']
    cmake = buildtool
    if config['ok'] and 'install' in opts['build_actions']:
        with fmt.Section('libtracy Install'), Timer(name='install') as timer:
            # GDFB_INSTALL_PREFIX (gdflatbuffers/paths.local.py); relative to the source.
            source = Path(build['source_path']).resolve()
            prefix = (source / Path(tt['install_prefix']).expanduser()).resolve()
            fmt.h(f'prefix: {prefix.as_posix()}')
            if prefix == source or prefix in source.parents:
                fmt.h(f'ERROR: install prefix {prefix.as_posix()} is the source worktree or above it')
                timer.status = TaskStatus.FAILED
            elif (prefix / 'project.godot').exists():
                fmt.h(f'ERROR: install prefix {prefix.as_posix()} is a Godot project; a Tracy install '
                      'replaces its default slot, so it never targets a shared project')
                timer.status = TaskStatus.FAILED
            if cmake.get('configuration_types'):
                configurations = chosen_config_types(cmake, opts.get('config_regex') or '.*')
                if not configurations:
                    fmt.h(f'No configuration matches /{opts.get("config_regex")}/')
                    timer.status = TaskStatus.FAILED
            else:
                configurations = [None]
            if timer.ok():
                for config_name in configurations:
                    fmt.s2(f' Installing {config_name or "default"} ')
                    args = ['cmake', '--install', Path(cmake['build_path']).as_posix(),
                            *(['--config', config_name] if config_name else []),
                            '--prefix', prefix.as_posix()]
                    stream_command(args, dry=opts['dry'])
                # cmake --install leaves flatc at mode 644; make it executable.
                dest = prefix / 'addons' / tt['addon_name'] if (prefix / 'project.godot').is_file() else prefix
                for flatc in sorted((dest / 'bin').glob(tt['flatc_glob'])):
                    if flatc.is_file() and not flatc.name.endswith(('.pdb', '.ilk')):
                        if opts['dry']:
                            fmt.hu(f'dry-run: chmod +x {flatc.as_posix()}')
                        else:
                            flatc.chmod(flatc.stat().st_mode | 0o111)
                            fmt.hu(f'chmod +x {flatc.as_posix()}')
                tt['install_root'] = prefix
                tt['installed_config'] = configurations[-1]
        stats['install'] = timer.get_dict()
        config['ok'] = timer.ok()


def libtracy_check():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: libtracy-Check
    #[============================[ libtracy Check ]============================]
    # Read-only, writes nothing. The Tracy client comes only from the engine: it
    # must be in the Godot bin the extension linked, each tracy library must
    # NEED that target's client, and nothing copies a client next to the
    # extension. A client found there is reported, not removed.
    # After a build: <build dir>/bin. After an install: the installed addon bin
    # under the prefix, and the merged flatbuffers.gdextension line for this
    # platform and target pointing at a .tracy library.
    import filecmp as _filecmp
    import re as _re
    import subprocess as _sp

    tt = build['libtracy']
    acts = set(opts['build_actions'])
    dry = opts['dry']
    if config['ok'] and acts & {'build', 'install'} and 'runtime_path' in tt:
        with fmt.Section('libtracy Check'):
            runtime = Path(tt['runtime_path'])
            errors = []   # the body runs at script level, so no nonlocal

            def err(msg):
                fmt.h(f'ERROR: {msg}')
                errors.append(msg)

            def is_tracy(p):
                return tt['output_tag'] in p.name.split('.')

            def needed(lib):
                # The dynamic section's library names, or None when no tool read it.
                for cmd, line_re in ((['readelf', '-d', str(lib)], r'\(NEEDED\).*\[(.+)\]'),
                                     (['objdump', '-p', str(lib)], r'DLL Name:\s*(\S+)')):
                    try:
                        out = _sp.run(cmd, capture_output=True, text=True, timeout=60)
                    except (OSError, _sp.SubprocessError):
                        continue
                    if out.returncode == 0:
                        return _re.findall(line_re, out.stdout)
                return None

            def check_lib(lib):
                names = needed(lib)
                if names is None:
                    fmt.hu(f'WARNING: no readelf/objdump to check {lib.name}')
                    return
                clients = [n for n in names if _re.search(tt['exe_client_re'], n)]
                fmt.hu(f'{lib.name} NEEDED client: {", ".join(clients) or "none"}')
                if runtime.name not in clients:
                    err(f'{lib.as_posix()} does not NEED {runtime.name}')

            def check_strays(directory):
                strays = sorted({p for g in tt['runtime'] for p in Path(directory).glob(g) if p.is_file()})
                for stray in strays:
                    fmt.h(f'WARNING: Tracy client next to the extension: {stray.as_posix()}; '
                          'the client must come only from the engine, delete this copy')

            engine_client = Path(tt['bin_dir']) / runtime.name
            if engine_client.is_file() and _filecmp.cmp(engine_client, runtime, shallow=False):
                fmt.h(f'engine client: {engine_client.as_posix()}')
            else:
                err(f'{engine_client.as_posix()} is missing or differs from {runtime.as_posix()}')

            # The build tree.
            if 'build' in acts:
                build_bin = Path(buildtool['build_path']) / tt['build_bin']
                built = sorted(p for p in build_bin.glob(tt['extension']) if is_tracy(p))
                if not built and not dry:
                    err(f'no tracy extension built for {tt["target"]}: '
                        f'{(build_bin / tt["extension"]).as_posix()} with a ".{tt["output_tag"]}." name part')
                for ext in built:
                    fmt.hu(f'built: {ext.as_posix()}')
                    check_lib(ext)
                check_strays(build_bin)

            # The installed addon.
            if 'install' in acts:
                root = Path(tt.get('install_root') or
                            (Path(build['source_path']).resolve() / Path(tt['install_prefix']).expanduser()).resolve())
                dest = root / 'addons' / tt['addon_name'] if (root / 'project.godot').is_file() else root
                fmt.h(f'installed addon: {dest.as_posix()}')
                gdext = dest / tt['install_gdextension']
                if not gdext.is_file():
                    if not dry:
                        err(f'{gdext.as_posix()} not found')
                else:
                    # [libraries] lines whose library is this target's extension.
                    section, lines = None, []
                    for raw in gdext.read_text(encoding='utf-8', errors='replace').splitlines():
                        line = raw.strip()
                        if line.startswith('['):
                            section = line
                            continue
                        m = _re.fullmatch(r'([^=\s]+)\s*=\s*"([^"]*)"', line)
                        if section == '[libraries]' and m and Path(m.group(2)).match(tt['extension']):
                            lines.append((m.group(1), m.group(2), line))
                    if len(lines) != 1:
                        err(f'{gdext.as_posix()}: expected one {tt["extension"]} line, found {len(lines)}')
                    for key, rel, line in lines:
                        fmt.hu(f'gdextension: {line}')
                        lib = dest / rel
                        if not is_tracy(lib):
                            err(f'{key} points at {rel}, not a ".{tt["output_tag"]}." library')
                        if not lib.is_file():
                            err(f'{lib.as_posix()} not found')
                        else:
                            fmt.hu(f'installed: {lib.as_posix()}')
                            check_lib(lib)
                for flatc in sorted((dest / 'bin').glob(tt['flatc_glob'])):
                    if flatc.is_file() and not os.access(flatc, os.X_OK) and os.name != 'nt':
                        if dry:
                            fmt.hu(f'dry-run: {flatc.name} is not executable yet (Install makes it so)')
                        else:
                            err(f'{flatc.as_posix()} is not executable')
                check_strays(dest / 'bin')
            if errors:
                config['ok'] = False


def libtracy_test_headless():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    # MARK: libtracy-Test
    #[============================[ libtracy Test ]=============================]
    # One headless run of the test-runner on the editor Tracy engine, captured.
    # Per run, under <runs>/<build name>/<timestamp>/:
    #   project/   a copy of the Godot project, the tracy extension in its addon,
    #              .godot/extension_list.cfg naming the tracy .gdextension
    #   xdg/       XDG_CONFIG/DATA/CACHE/STATE_HOME for the engine
    #   capture.tracy, *.log, *.cmd, zones.csv, messages.csv, result.json
    # tracy-capture listens first, the engine starts settle_secs later. Pass:
    # engine exit 0, capture saved, godot_tracy_client_matches() true, and at
    # least one extension zone in the capture.
    import csv as _csv
    import json as _json
    import re as _re
    import shutil as _shutil
    import socket as _socket
    import subprocess as _sp
    import time as _time

    tt = build['libtracy']
    tst = tt['test']
    if config['ok'] and 'test' in opts['build_actions'] and tt['target'] in tst['targets']:
        dry = opts['dry']
        with fmt.Section('libtracy Test'), Timer(name='test') as timer:
            res = {'status': None, 'failures': [], 'logs': [], 'facts': {}}

            def fail(why):
                res['failures'].append(why)
                fmt.h(f'FAIL: {why}')

            def need(path, what):
                if path is None or not Path(path).exists():
                    fail(f'{what} not found: {path}')
                    return False
                return True

            def cmdline(args, env=None):
                prefix = ''.join(f'{k}={v} ' for k, v in (env or {}).items())
                return prefix + _sp.list2cmdline([str(a) for a in args])

            def find_one(directory, globs):
                for g in globs:
                    hits = [p for p in Path(directory).glob(g) if p.is_file()]
                    if hits:
                        return max(hits, key=lambda p: p.stat().st_mtime)
                return None

            def tagged(paths):
                return sorted(p for p in paths if tt['output_tag'] in p.name.split('.'))

            source = Path(build['source_path'])
            bin_dir = Path(tt['bin_dir']) if 'bin_dir' in tt else None
            engine = find_one(bin_dir, tt['engine']) if bin_dir else None
            project_src = Path(os.environ.get(tst['project_env']) or (source / 'project'))
            script_rel = os.environ.get(tst['script_env']) or tst['script']
            capture_tool = tst.get('capture')
            csvexport_tool = tst.get('csvexport')
            addon_src = source / tt['extension_addon']

            ok = all([
                need(bin_dir, 'Godot bin (libtracy Resolve did not run?)'),
                need(engine, f'editor Tracy engine {tt["engine"]} in {bin_dir}'),
                need(project_src, f'Godot project (set ${tst["project_env"]})'),
                need(capture_tool, 'tracy-capture (godot TRACY_CAPTURE)'),
                need(csvexport_tool, 'tracy-csvexport (godot TRACY_CSVEXPORT)'),
            ])
            gdext = tagged(addon_src.glob('*.gdextension')) if addon_src.is_dir() else []
            ext_libs = tagged(Path(source / tt['extension_bin']).glob(tt['extension']))
            if not gdext:
                fail(f'no tracy .gdextension in {addon_src.as_posix()} (a name part ".{tt["output_tag"]}.")')
                ok = False
            if not ext_libs and not dry:
                fail(f'no tracy extension library in {(source / tt["extension_bin"]).as_posix()}')
                ok = False
            script_path = Path(script_rel) if Path(script_rel).is_absolute() else project_src / script_rel
            if not script_path.is_file():
                fail(f'test script not found: {script_path.as_posix()} (set ${tst["script_env"]})')
                ok = False

            runs = Path(os.environ.get(tst['runs_env']) or tst['runs_default'])
            run_dir = runs / build['name'] / _time.strftime('%Y%m%d-%H%M%S')
            project_dir = run_dir / 'project'
            xdg = run_dir / 'xdg'
            trace = run_dir / 'capture.tracy'
            fmt.h(f'run dir: {run_dir.as_posix()}')

            if ok:
                # The project copy: everything but .godot and .git, then the tracy
                # extension addon only (a default .gdextension would load a second
                # copy of the same classes), then extension_list.cfg.
                addon_rel = Path(tt['extension_addon']).relative_to('project')
                if dry:
                    fmt.hu(f'dry-run: copy {project_src.as_posix()} -> {project_dir.as_posix()}')
                    fmt.hu(f'dry-run: tracy addon {[p.name for p in gdext]} + {[p.name for p in ext_libs]}')
                else:
                    run_dir.mkdir(parents=True, exist_ok=True)
                    _shutil.copytree(project_src, project_dir, symlinks=False,
                                     ignore=_shutil.ignore_patterns('.godot', '.git'))
                    addon_dst = project_dir / addon_rel
                    if addon_dst.exists():
                        _shutil.rmtree(addon_dst)
                    (addon_dst / 'bin').mkdir(parents=True)
                    for f in gdext:
                        _shutil.copy2(f, addon_dst / f.name)
                    # TODO(libtracy test): stop copying the engine's client here before testing resumes; the client comes only from the engine.
                    # The tracy extension libraries, and the engine's Tracy client beside them.
                    for f in [*ext_libs, Path(tt['runtime_path'])]:
                        _shutil.copy2(f, addon_dst / 'bin' / f.name)
                ext_list = project_dir / '.godot' / 'extension_list.cfg'
                lines = [f'res://{(addon_rel / f.name).as_posix()}' for f in gdext]
                if dry:
                    fmt.hu(f'dry-run: write {ext_list.as_posix()}: {lines}')
                elif not ext_list.exists():
                    ext_list.parent.mkdir(parents=True, exist_ok=True)
                    ext_list.write_text('\n'.join(lines) + '\n', encoding='utf-8')
                    res['logs'].append(ext_list.as_posix())

                env = {f'XDG_{k}_HOME': (xdg / k.lower()).as_posix() for k in ('CONFIG', 'DATA', 'CACHE', 'STATE')}
                # Inside the project it is passed as res://, like the editor would.
                script_arg = f'res://{script_path.relative_to(project_src).as_posix()}' \
                    if script_path.is_relative_to(project_src) else script_path.as_posix()
                eng_cmd = [engine.as_posix(), *tst['engine_args'], '--path', project_dir.as_posix(), '-s', script_arg]
                cap_cmd = [str(capture_tool), '-o', trace.as_posix(), '-a', tst['address'], '-p', str(tst['port']), '-f']
                res['facts'].update({'engine': engine.as_posix(), 'engine_cmd': cmdline(eng_cmd, env),
                                     'capture_cmd': cmdline(cap_cmd), 'project': project_src.as_posix()})
                fmt.hu(f'$ {cmdline(cap_cmd)} &')
                fmt.hu(f'(wait {tst["settle_secs"]} s)')
                fmt.hu(f'$ {cmdline(eng_cmd, env)}')

                if not dry:
                    def port_busy():
                        try:
                            with _socket.create_connection((tst['address'], int(tst['port'])), timeout=1):
                                return True
                        except OSError:
                            return False

                    if port_busy():
                        fail(f'{tst["address"]}:{tst["port"]} already has a Tracy client; another engine is running')
                    else:
                        for d in env.values():
                            Path(d).mkdir(parents=True, exist_ok=True)
                        (run_dir / 'capture.cmd').write_text(cmdline(cap_cmd) + '\n', encoding='utf-8')
                        (run_dir / 'engine.cmd').write_text(cmdline(eng_cmd, env) + '\n', encoding='utf-8')
                        cap_log = run_dir / 'capture.log'
                        eng_log = run_dir / 'engine.log'
                        res['logs'] += [cap_log.as_posix(), eng_log.as_posix()]
                        with open(cap_log, 'w', encoding='utf-8') as cl:
                            cap = _sp.Popen(cap_cmd, stdout=cl, stderr=_sp.STDOUT, stdin=_sp.DEVNULL)
                            _time.sleep(tst['settle_secs'])
                            with open(eng_log, 'w', encoding='utf-8') as el:
                                try:
                                    eng_rc = _sp.run(eng_cmd, stdout=el, stderr=_sp.STDOUT, stdin=_sp.DEVNULL,
                                                     env={**os.environ, **env}, cwd=project_dir,
                                                     timeout=tst.get('timeout') or 300).returncode
                                except _sp.TimeoutExpired:
                                    eng_rc = 'timeout'
                            try:
                                cap_rc = cap.wait(timeout=60)
                            except _sp.TimeoutExpired:
                                cap.terminate()   # a hard stop skips the write; terminate first
                                try:
                                    cap_rc = cap.wait(timeout=10)
                                except _sp.TimeoutExpired:
                                    cap.kill()
                                    cap_rc = 'killed'
                        res['facts'].update({'engine_rc': eng_rc, 'capture_rc': cap_rc})
                        if eng_rc != 0:
                            fail(f'engine exited {eng_rc} (log: {eng_log.as_posix()})')
                        if cap_rc != 0:
                            fail(f'tracy-capture exited {cap_rc} (log: {cap_log.as_posix()})')
                        eng_text = eng_log.read_text(encoding='utf-8', errors='replace')

                        if not trace.is_file() or not trace.stat().st_size:
                            fail(f'capture missing or empty: {trace.as_posix()}')
                        else:
                            res['facts']['trace'] = trace.as_posix()
                            res['facts']['trace_bytes'] = trace.stat().st_size
                            zones_csv = run_dir / 'zones.csv'
                            msgs_csv = run_dir / 'messages.csv'
                            z = _sp.run([str(csvexport_tool), trace.as_posix()], capture_output=True, text=True,
                                        errors='replace', timeout=300)
                            m = _sp.run([str(csvexport_tool), '-m', trace.as_posix()], capture_output=True,
                                        text=True, errors='replace', timeout=300)
                            zones_csv.write_text(z.stdout, encoding='utf-8')
                            msgs_csv.write_text(m.stdout, encoding='utf-8')
                            res['logs'] += [zones_csv.as_posix(), msgs_csv.as_posix()]

                            # tracy-csvexport: name,src_file,src_line,total_ns,total_perc,counts,mean,min,max,std
                            ext_src = (source / 'src').resolve().as_posix()
                            name_re = _re.compile(tst['zone_name_pattern'])
                            ext_zones = []
                            for row in list(_csv.reader(z.stdout.splitlines()))[1:]:
                                if len(row) < 10:
                                    continue
                                zname, zfile = ','.join(row[:-9]), row[-9]
                                if Path(zfile).as_posix().startswith(ext_src) or name_re.search(zname):
                                    ext_zones.append(f'{zname} ({zfile}:{row[-8]}) x{row[-5]}')
                            res['facts']['extension_zones'] = ext_zones
                            fmt.h(f'extension zones: {len(ext_zones)}')
                            for line in ext_zones[:10]:
                                fmt.hu(line)
                            if not ext_zones:
                                fail(f'no extension zone in {zones_csv.as_posix()}')

                        match_re = _re.compile(tst['client_matches_pattern'])
                        msgs = msgs_csv.read_text(encoding='utf-8') if msgs_csv.is_file() else ''
                        matched = bool(match_re.search(eng_text) or match_re.search(msgs))
                        res['facts']['client_matches'] = matched
                        fmt.h(f'godot_tracy_client_matches() true: {"yes" if matched else "not seen"}')
                        if not matched:
                            fail(f'godot_tracy_client_matches() true not seen in {eng_log.as_posix()} '
                                 f'or the capture messages (pattern {tst["client_matches_pattern"]})')

                        res['status'] = 'fail' if res['failures'] else 'pass'
                        (run_dir / 'result.json').write_text(_json.dumps(res, indent=2, default=str), encoding='utf-8')
                        fmt.h(f'result: {res["status"]}  ({(run_dir / "result.json").as_posix()})')
            if dry:
                res['status'] = 'dry'
            if res['failures']:
                timer.status = TaskStatus.FAILED
        stats['test'] = timer.get_dict()
        config['ok'] = timer.ok() and not res['failures']


def libtracy_bench():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    # start_script

    # MARK: libtracy-Bench
    #[============================[ libtracy Bench ]============================]
    # TODO(libtracy bench): not implemented. Hook: the `test` build action.
    # template_release target only. One scenario suite of project/bench on
    # godot.windows.template_release.x86_64.tracy.exe (the real exe, not
    # .console.exe), keeping run.ps1's pack layout: the extension DLL and the
    # TracyClient DLL beside that exe. tracy-capture v0.14.1 listens first.
    if config['ok'] and 'test' in opts['build_actions']:
        if build['libtracy']['target'] == 'template_release':
            fmt.h('libtracy bench: not implemented yet (TODO stub)')
