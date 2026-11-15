import os
from types import SimpleNamespace

from src.config import git_base

def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    import copy
    from src.expand_config import expand_host_env, expand_cmake, expand_func
    from share.snippets import source_git, show_stats, cmake_build

    from godot.config import godot_platforms, godot_arch

    from src.compiler_cache import apply_cmake_compiler_cache
    from src.config import (git_base, project_base, build_base, cmake_base, gopts)

    # One library. GODOTCPP_TARGET is a cache string, so each flavor is its
    # own configure. GDTESTS_SOURCE_PATH, when set, replaces the GitHub url.
    # Ref stays main.
    git_source = SimpleNamespace({**vars(git_base), **{
        'name': 'git',
        'url': GDTESTS_SOURCE_PATH or "https://github.com/enetheru/godot-tests.git/",
        'ref': "main"
    }})
    project = SimpleNamespace({**vars(project_base), **{
        'name':'gdtests',
        'sources':{
            'git': git_source,
        },
        'buildtools':{
            'cmake':SimpleNamespace(**{
                **vars(cmake_base),
                'targets': ['godot-tests'],
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
        'source_def': git_source,
    }})

    builds = expand_host_env( build_start, project )

    for build in builds:
        toolchain = build.toolchain
        if hasattr(toolchain, 'target_arch'):
            build.arch = toolchain.target_arch
            build.platform = toolchain.target_platform

    builds = expand_func( builds, expand_cmake )

    split = []
    for build in builds:
        # godot-cpp 10 reads a versioned api file unless CUSTOM_API_FILE is set.
        # DEPRECATED=OFF matches an engine built with deprecated=no.
        if CUSTOM_GDEXTENSION_DIR:
            gde_dir = str(CUSTOM_GDEXTENSION_DIR).replace('\\', '/')
            build.buildtool.config_vars.append(f'-DGODOTCPP_GDEXTENSION_DIR={gde_dir}')
            build.buildtool.config_vars.append(
                f'-DGODOTCPP_CUSTOM_API_FILE={gde_dir}/extension_api.json')
        build.buildtool.config_vars.append('-DGODOTCPP_DEPRECATED=OFF')
        for target in ('template_release', 'template_debug', 'editor'):
            cfg = copy.deepcopy(build)
            cfg.godotcpp_target = target
            cfg.buildtool.config_vars.append(f'-DGODOTCPP_TARGET={target}')
            split.append(cfg)
            # The same configure against the matching libtracy Godot bin.
            # The default folders stay as they are.
            tracy = libtracy_variant(cfg)
            if tracy is not None:
                split.append(tracy)
    builds = split

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
        # libtracy configs check out ref tracy into their own worktree.
        build.source_dir = f'{build.host}.{getattr(build, "source_dir_suffix", "main")}'
        cmake.build_dir = build.name
        build.gdtests_install = {
            'prefix': GDTESTS_INSTALL_PREFIX,
            'addon_name': 'enetheru.tests-extension',
        }
        if install_cmake not in build.script_parts:
            build.script_parts.insert(build.script_parts.index(cmake_build) + 1, install_cmake)
        if 'install' not in build.verbs:
            at = build.verbs.index('build') + 1 if 'build' in build.verbs else len(build.verbs)
            build.verbs.insert(at, 'install')
        build.script_parts.append( show_stats )

    project.build_configs = {v.name: v for v in builds }
    return  project

# Machine-specific paths live in gdtests/paths.local.py, which is gitignored.
# Copy gdtests/paths.local.windows.example to gdtests/paths.local.py.
#
# GDTESTS_SOURCE_PATH: checkout fetch uses (remote origin, ref main). None
#   keeps the GitHub url. A local repo only advertises committed branches.
# GDTESTS_INSTALL_PREFIX: cmake --install --prefix. Relative paths resolve
#   against the source worktree. Files land in
#   <prefix>/addons/enetheru.tests-extension/.
# CUSTOM_GDEXTENSION_DIR: dumped interface directory. When set, configure
#   passes it and its unversioned extension_api.json.
GDTESTS_SOURCE_PATH: str | None = None
GDTESTS_INSTALL_PREFIX: str = 'install'
CUSTOM_GDEXTENSION_DIR:str = ''

_LOCAL_OVERRIDES = (
    'GDTESTS_SOURCE_PATH',
    'GDTESTS_INSTALL_PREFIX',
    'CUSTOM_GDEXTENSION_DIR'
)


def _load_local_paths() -> None:
    """Apply gdtests/paths.local.py, when present, over the defaults above."""
    import importlib.util
    import pathlib
    try:
        local = pathlib.Path(__file__).with_name('paths.local.py')
    except NameError:
        return
    if not local.is_file():
        return
    spec = importlib.util.spec_from_file_location('gdtests_paths_local', local)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in _LOCAL_OVERRIDES:
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)


_load_local_paths()

# The extension linked against the engine's shared Tracy client.
# One extra Ninja Multi-Config configure per GODOTCPP_TARGET, named libtracy.
# The Godot bin, its header and its client library are found when the build
# script runs. See cmake/tracy.cmake.
LIBTRACY_CMAKE = {
    'enable':         'GDTESTS_ENABLE_TRACY',
    'header_dir':     'GODOT_TRACY_HEADER_DIR',
    'profiling_header': 'GODOT_PROFILING_HEADER',
    'include_dir':    'TRACY_INCLUDE_DIR',
    'client_library': 'TRACY_CLIENT_LIBRARY',
}

LIBTRACY_BIN_ENV = 'GDTESTS_GODOT_TRACY_BIN'
LIBTRACY_EXE_ENV = 'GDTESTS_GODOT_TRACY_EXE'
LIBTRACY_EXE_CLIENT_RE = r'TracyClient\.'
LIBTRACY_HEADER = 'godot_profiling.*.gen.h'

LIBTRACY_PLATFORMS = {
    'win32': {
        'godot_glob': '{host}.{toolchain}.x86_64.windows.{target}.libtracy.*',
        'link':       ['TracyClient.windows.{target}.x86_64.*tracy.lib',
                       'obj/core/profiling/libTracyClient.windows.{target}.x86_64.*tracy.a'],
        'runtime':    ['TracyClient.windows.{target}.x86_64.*tracy.dll'],
        'extension':  'tests.windows.{target}.*.dll',
        'engine':     ['godot.windows.{target}*.x86_64.*tracy.exe'],
    },
    'linux': {
        'godot_glob': '{host}.*.x86_64.linux.{target}.libtracy.*',
        'link':       ['libTracyClient.linuxbsd.{target}*.x86_64*.so',
                       'obj/core/profiling/libTracyClient.linuxbsd.{target}*.x86_64*.so'],
        'runtime':    ['libTracyClient.linuxbsd.{target}*.x86_64*.so'],
        'extension':  'tests.linux.{target}.*.so',
        'engine':     ['godot.linuxbsd.{target}*.x86_64.*tracy'],
    },
}

LIBTRACY_BUILD_BIN = 'bin'
LIBTRACY_OUTPUT_TAG = 'tracy'

# Ref tracy of this same repo. $GDTESTS_TRACY_SOURCE_REF overrides it.
LIBTRACY_SOURCE = SimpleNamespace({**vars(git_base), **{
    'name': 'tracy',
    'url': GDTESTS_SOURCE_PATH or "https://github.com/enetheru/godot-tests.git/",
    'ref': os.environ.get('GDTESTS_TRACY_SOURCE_REF') or 'tracy',
}})


def _tracy_include_dir() -> str | None:
    """Tracy public headers, from the same TRACY_PROFILER_PATH the godot libtracy builds use."""
    from godot.config import TRACY_PROFILER_PATH, _tracy_version_at
    if not TRACY_PROFILER_PATH:
        print('Skipping gdtests libtracy: TRACY_PROFILER_PATH is not set (see godot/paths.local.*.example)')
        return None
    if not _tracy_version_at(TRACY_PROFILER_PATH):
        print(f'Skipping gdtests libtracy: cannot read Tracy version at {TRACY_PROFILER_PATH}')
        return None
    return f'{TRACY_PROFILER_PATH.rstrip("/")}/public'


def libtracy_variant( cfg:SimpleNamespace ) -> SimpleNamespace | None:
    """The libtracy copy of one per-target configure, or None where it does not apply."""
    import copy
    from pathlib import Path
    from src.config import gopts
    from src.expand_config import short_host

    spec = LIBTRACY_PLATFORMS.get(cfg.platform)
    if spec is None:
        return None
    if cfg.arch != 'x86_64' or getattr(cfg.buildtool, 'short_gen', None) != 'ninja-multi':
        return None
    include_dir = _tracy_include_dir()
    if include_dir is None:
        return None

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
        'godot_dir': GDTESTS_INSTALL_PREFIX if Path(GDTESTS_INSTALL_PREFIX).is_absolute() else '',
        'godot_root': (gopts.path / 'godot').as_posix(),
        'godot_glob': spec['godot_glob'].format(
            host=short_host(), target=target, toolchain=cfg.toolchain.name),
        'link': [g.format(target=target) for g in spec['link']],
        'runtime': [g.format(target=target) for g in spec['runtime']],
        'extension': spec['extension'].format(target=target),
        'build_bin': LIBTRACY_BUILD_BIN,
        'output_tag': LIBTRACY_OUTPUT_TAG,
        'engine': [g.format(target=target) for g in spec['engine']],
        'exe_env': [f'{LIBTRACY_EXE_ENV}_{target.upper()}', LIBTRACY_EXE_ENV],
        'exe_client_re': LIBTRACY_EXE_CLIENT_RE,
    }

    from share.snippets import source_git
    parts = tracy.script_parts
    parts.insert(parts.index(cmake_configure_part()), libtracy_resolve)
    return tracy


def cmake_configure_part():
    from share.snippets import cmake_configure
    return cmake_configure


def libtracy_resolve():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    buildtool:dict = {}
    # start_script

    def libtracy_dump_label():
        import sys
        if sys.platform == 'win32':
            return 'objdump/llvm-objdump'
        return 'readelf/llvm-readelf'

    def libtracy_needed_names(path):
        import re as _re
        import shutil
        import subprocess as _sp
        import sys
        if sys.platform == 'win32':
            candidates = (
                ('objdump', '-p', r'DLL Name:\s*(\S+)'),
                ('llvm-objdump', '-p', r'DLL Name:\s*(\S+)'),
            )
        else:
            candidates = (
                ('readelf', '-d', r'\(NEEDED\).*\[(.+)\]'),
                ('llvm-readelf', '-d', r'\(NEEDED\).*\[(.+)\]'),
            )
        for name, flag, line_re in candidates:
            exe = shutil.which(name)
            if not exe:
                continue
            try:
                out = _sp.run([exe, flag, str(path)], capture_output=True, text=True, timeout=60)
            except (OSError, _sp.SubprocessError):
                continue
            if out.returncode != 0:
                continue
            return _re.findall(line_re, out.stdout)
        return None

    # MARK: libtracy-Resolve
    # Find this target's Godot libtracy bin, header and client library, and pass
    # them to the configure.
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
                suffix = folder.name.split('.libtracy.', 1)[1]
                m = _re.fullmatch(r'(?:tests\.)?(\d+(?:\.\d+)*)(~?)', suffix)
                return (tuple(int(n) for n in m.group(1).split('.')), 1 if m.group(2) else 0, folder.stat().st_mtime)

            def _profiling_headers(folder):
                return sorted((folder / 'bin').glob(tt['header']))

            bin_dir = None
            shared_folder = False
            for name in tt['bin_env']:
                if os.environ.get(name):
                    bin_dir = Path(os.environ[name])
                    fmt.h(f'godot bin from ${name}: {bin_dir.as_posix()}')
                    break
            if bin_dir is None and tt.get('godot_dir'):
                bin_dir = Path(tt['godot_dir'])
                shared_folder = True
                fmt.h(f'godot bin folder: {bin_dir.as_posix()}')
            if bin_dir is None:
                root = Path(tt['godot_root'])
                pattern = tt['godot_glob']
                folders = [f for f in root.glob(pattern)
                           if f.is_dir()
                           and _re.fullmatch(r'(?:tests\.)?\d+(?:\.\d+)*~?', f.name.split('.libtracy.', 1)[1])
                           and len(_profiling_headers(f)) == 1]
                if not folders:
                    _missing('no Godot libtracy build folder with one godot_profiling.<suffix>.gen.h', [
                        f'looked for {(root / pattern).as_posix()}',
                        f'build that godot libtracy target first, or set ${tt["bin_env"][0]} to its bin'])
                folder = max(folders, key=_version_key)
                if len(folders) > 1:
                    fmt.hu('candidates: ' + ', '.join(sorted(f.name for f in folders)))
                bin_dir = folder / 'bin'
                fmt.h(f'godot bin: {bin_dir.as_posix()}')
            if not bin_dir.is_dir():
                _missing('Godot bin is not a directory', [bin_dir.as_posix()])

            header_glob = tt['header'].replace('*', f'*{tt["target"]}*', 1) if shared_folder else tt['header']
            headers = sorted(bin_dir.glob(header_glob))
            if len(headers) != 1:
                _missing(f'{header_glob} matched {len(headers)} files', [
                    f'looked in {bin_dir.as_posix()}',
                    'the engine publishes one godot_profiling<suffix>.gen.h for this target'])
            header = headers[0]
            text = header.read_text(errors='replace')
            m = _re.search(r'#define\s+GODOT_TRACY_DEFINES_HASH\s+(\S+)', text)
            fmt.hu(f'header: {header.as_posix()}  defines hash: {m.group(1) if m else "not found"}')
            if not _re.search(r'#define\s+GODOT_TRACY_SHARED_CLIENT\b', text):
                _missing('the header has no GODOT_TRACY_SHARED_CLIENT', [
                    header.as_posix(),
                    'the engine was not built with tracy_shared=yes, so there is no client library to link'])

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

            def _client_needed(exe):
                names = libtracy_needed_names(exe)
                if names is None:
                    return None
                return [n for n in names if _re.search(tt['exe_client_re'], n)]

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
                    fmt.hu(f'WARNING: no {libtracy_dump_label()} to check {exe.name}; accepted unchecked')
                    engine = exe
                    break
                if needed:
                    fmt.hu(f'engine NEEDED: {", ".join(needed)}')
                    if runtime.name not in needed:
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
                f'-D{cmake_names["profiling_header"]}={header.as_posix()}',
                f'-D{cmake_names["client_library"]}={link.as_posix()}',
            ]
            tt['bin_dir'] = bin_dir
            tt['runtime_path'] = runtime


def install_cmake():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: Install
    # cmake --install for this build. The prefix is GDTESTS_INSTALL_PREFIX,
    # under the source worktree when the path is relative. Files go in
    # <prefix>/addons/enetheru.tests-extension/.
    from src.select import chosen_config_types

    spec = build['gdtests_install']
    cmake = buildtool
    if config['ok'] and 'install' in opts['build_actions']:
        with fmt.Section('Install'), Timer(name='install') as timer:
            source = Path(build['source_path']).resolve()
            prefix = (source / Path(spec['prefix']).expanduser()).resolve()
            fmt.h(f'prefix: {prefix.as_posix()}')
            if prefix == source or prefix in source.parents:
                fmt.h(f'ERROR: install prefix {prefix.as_posix()} is the source worktree or above it')
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
                spec['root'] = prefix.as_posix()
        stats['install'] = timer.get_dict()
        config['ok'] = timer.ok()
