from types import SimpleNamespace

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
        build.source_dir = f'{build.host}.main'
        cmake.build_dir = build.name
        build.script_parts.append( show_stats )

    project.build_configs = {v.name: v for v in builds }
    return  project

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

# CMake interface of the extension. Every option name the variant passes is
# here and nowhere else.
# TODO(extension): names confirmed final on 2026-10-21. Update them here only,
#   if the extension's CMake changes them.
LIBTRACY_CMAKE = {
    'enable':         'GDFB_ENABLE_TRACY',       # BOOL, ON for libtracy only. Default folders leave it unset.
    'header_dir':     'GODOT_TRACY_HEADER_DIR',  # dir of godot_profiling.gen.h (that target's Godot bin)
    'include_dir':    'TRACY_INCLUDE_DIR',       # Tracy public headers (<tracy/Tracy.hpp>)
    'client_library': 'TRACY_CLIENT_LIBRARY',    # what the extension links: MinGW import lib, or the .so
}

# Per-target override of the Godot bin, read by the build script. Set it to
# point a configure at a bin the runner did not build, for example on Linux.
#   GDFB_GODOT_TRACY_BIN_EDITOR, ..._TEMPLATE_DEBUG, ..._TEMPLATE_RELEASE
# GDFB_GODOT_TRACY_BIN applies to every target. A bin without that target's
# client library still fails, so a shared value cannot link the wrong target.
LIBTRACY_BIN_ENV = 'GDFB_GODOT_TRACY_BIN'

# Header the engine installs in its bin. The variant reads the defines hash and
# GODOT_TRACY_SHARED_CLIENT from it.
LIBTRACY_HEADER = 'godot_profiling.gen.h'

# Per platform. Globs are relative to the Godot bin; {target} is the
# GODOTCPP_TARGET, {host} is short_host(). 'godot_glob' is a folder under the
# runner's godot project (<runner root>/godot): that target's plain libtracy
# build, any version. The newest version wins.
# 'link' is what TRACY_CLIENT_LIBRARY gets. 'runtime' is the client the
# extension loads, placed next to the extension and in the Godot bin.
# 'extension' is the built extension, in the project's addon bin.
LIBTRACY_PLATFORMS = {
    'win32': {
        'toolchains': ['mingw64'],     # the import library is MinGW
        'godot_glob': '{host}.mingw64.x86_64.windows.{target}.libtracy.*',
        'link':       ['obj/core/profiling/libTracyClient.windows.{target}.x86_64.tracy.a'],
        'runtime':    ['TracyClient.windows.{target}.x86_64.tracy.dll'],
        'extension':  'flatbuffers.windows.{target}.x86_64*.dll',
    },
    'linux': {
        'toolchains': ['gcc'],
        # The runner does not build Godot on Linux yet. The env override above is the usual path.
        'godot_glob': '{host}.*.x86_64.linux.{target}.libtracy.*',
        # The engine loads this library by SONAME; the extension needs no RUNPATH.
        'link':       ['libTracyClient.linuxbsd.{target}*.x86_64*.so',
                       'obj/core/profiling/libTracyClient.linuxbsd.{target}*.x86_64*.so'],
        'runtime':    ['libTracyClient.linuxbsd.{target}*.x86_64*.so'],
        'extension':  'flatbuffers.linux.{target}*.so',
    },
}

# CMake writes the extension into the Godot project inside the source tree
# (godot-flatbuffers CMakeLists.txt: GDE_INSTALL_PATH/bin).
LIBTRACY_EXTENSION_BIN = 'project/addons/enetheru.flatbuffers-extension/bin'


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

    tracy = copy.deepcopy(cfg)
    tracy.variant = 'libtracy'
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
        'extension_bin': LIBTRACY_EXTENSION_BIN,
    }

    # Insert the resolve step before configure, the placement after build.
    parts = tracy.script_parts
    parts.insert(parts.index(cmake_configure_part()), libtracy_resolve)
    parts.append(libtracy_place)
    # Test action hooks. Stubs until the capture and bench steps are written.
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
    wants = {'configure', 'build', 'test'} & set(opts['build_actions'])
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

            cmake_names = tt['cmake']
            buildtool['config_vars'] += [
                f'-D{cmake_names["header_dir"]}={bin_dir.as_posix()}',
                f'-D{cmake_names["client_library"]}={link.as_posix()}',
            ]
            tt['bin_dir'] = bin_dir
            tt['runtime_path'] = runtime


def libtracy_place():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    # start_script

    # MARK: libtracy-Place
    #[============================[ libtracy Place ]============================]
    # Put the engine's Tracy client next to the built extension, and make sure it
    # is in the Godot bin the extension linked. Windows loads a GDExtension's
    # dependency from the engine exe's directory. An existing file in the Godot
    # bin is left alone: that bin belongs to the Godot build.
    import shutil as _shutil
    import filecmp as _filecmp

    tt = build['libtracy']
    if config['ok'] and 'build' in opts['build_actions'] and 'runtime_path' in tt:
        with fmt.Section('libtracy Place'):
            runtime = Path(tt['runtime_path'])
            ext_bin = Path(build['source_path']) / tt['extension_bin']
            built = sorted(ext_bin.glob(tt['extension']))
            if not built and not opts['dry']:
                fmt.h(f'ERROR: no extension built for {tt["target"]}: {(ext_bin / tt["extension"]).as_posix()}')
                config['ok'] = False
            else:
                for ext in built:
                    fmt.hu(f'extension: {ext.as_posix()}')
                for dest_dir in [ext_bin, Path(tt['bin_dir'])]:
                    dest = dest_dir / runtime.name
                    if dest.exists() and _filecmp.cmp(dest, runtime, shallow=False):
                        fmt.h(f'present: {dest.as_posix()}')
                    elif dest_dir == Path(tt['bin_dir']) and dest.exists():
                        fmt.h(f'ERROR: {dest.as_posix()} differs from {runtime.as_posix()}; not overwriting the Godot bin')
                        config['ok'] = False
                    elif opts['dry']:
                        fmt.h(f'dry-run: copy {runtime.as_posix()} -> {dest.as_posix()}')
                    else:
                        _shutil.copy2(runtime, dest)
                        fmt.h(f'copied: {dest.as_posix()}')


def libtracy_test_headless():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    # start_script

    # MARK: libtracy-Test
    #[============================[ libtracy Test ]=============================]
    # TODO(libtracy test): not implemented. Hook: the `test` build action.
    # Editor target only. One headless suite on the editor Tracy exe of the
    # resolved bin (godot.windows.editor.x86_64.tracy.exe, not .console.exe;
    # godot.linuxbsd.editor*.x86_64.tracy on Linux), with
    #   --headless --tracy -s res://addons/enetheru.test-runner/run_headless.gd
    # in the project folder. tracy-capture v0.14.1 (godot TRACY_CAPTURE) listens
    # first: on-demand keeps only zones that begin and end while it is
    # connected, and the client takes one server per process. Check
    # godot_tracy_client_matches() and an extension zone in the capture.
    if config['ok'] and 'test' in opts['build_actions']:
        if build['libtracy']['target'] == 'editor':
            fmt.h('libtracy headless test: not implemented yet (TODO stub)')


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
