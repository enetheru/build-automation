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
    from share.snippets import source_git, show_stats, cmake_build

    from godot.config import godot_platforms, godot_arch

    from src.compiler_cache import apply_cmake_compiler_cache
    from src.config import (git_base, project_base, build_base, cmake_base, gopts)

    # One library. GODOTCPP_TARGET is a cache string, so each flavor is its
    # own configure. GDUUID_SOURCE_PATH, when set, replaces the GitHub url.
    # Ref stays main.
    git_source = SimpleNamespace({**vars(git_base), **{
        'name': 'git',
        'url': GDUUID_SOURCE_PATH or "https://github.com/enetheru/godot-uuid.git/",
        'ref': "main"
    }})
    project = SimpleNamespace({**vars(project_base), **{
        'name':'gduuid',
        'sources':{
            'git': git_source,
        },
        'buildtools':{
            'cmake':SimpleNamespace(**{
                **vars(cmake_base),
                'targets': ['godot-uuid'],
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
        ]
        build.name = '.'.join(filter(None, name_parts))
        build.source_dir = f'{build.host}.main'
        cmake.build_dir = build.name
        # Same install verb on every target. The prefix is this build's
        # source worktree plus GDUUID_INSTALL_PREFIX.
        build.gduuid_install = {
            'prefix': GDUUID_INSTALL_PREFIX,
            'addon_name': 'enetheru.uuid-extension',
        }
        if install_cmake not in build.script_parts:
            build.script_parts.insert(build.script_parts.index(cmake_build) + 1, install_cmake)
        if 'install' not in build.verbs:
            at = build.verbs.index('build') + 1 if 'build' in build.verbs else len(build.verbs)
            build.verbs.insert(at, 'install')
        build.script_parts.append( show_stats )

    project.build_configs = {v.name: v for v in builds }
    return  project

# MARK: Paths
# Machine-specific paths live in gduuid/paths.local.py, which is gitignored
# (like godot/paths.local.py). To set up a machine, copy
#   gduuid/paths.local.windows.example
# to gduuid/paths.local.py and edit it. Without that file the defaults
# below apply.
#
# GDUUID_SOURCE_PATH: checkout fetch uses for the main source (remote origin,
#   ref main). None keeps the GitHub url. A local repo only advertises its
#   branches, so uncommitted files there are not what gets built.
# GDUUID_INSTALL_PREFIX: the `cmake --install --prefix` of every build.
#   Relative paths resolve against that build's source worktree; the default
#   'install' is <source>/install. An absolute path is used as given. Files
#   land in <prefix>/addons/enetheru.uuid-extension/. The prefix may be any
#   folder, including a Godot project. The verb still refuses the source
#   worktree itself or a folder above it.
GDUUID_SOURCE_PATH: str | None = None
GDUUID_INSTALL_PREFIX: str = 'install'

# Names paths.local.py may set.
_LOCAL_OVERRIDES = (
    'GDUUID_SOURCE_PATH',
    'GDUUID_INSTALL_PREFIX',
)


def _load_local_paths() -> None:
    """Apply gduuid/paths.local.py, when present, over the defaults above."""
    import importlib.util
    import pathlib
    try:
        local = pathlib.Path(__file__).with_name('paths.local.py')
    except NameError:   # no __file__, nothing to look for
        return
    if not local.is_file():
        return
    spec = importlib.util.spec_from_file_location('gduuid_paths_local', local)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in _LOCAL_OVERRIDES:
        if hasattr(mod, name):
            globals()[name] = getattr(mod, name)


_load_local_paths()

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

def install_cmake():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: Install
    #[================================[ Install ]================================]
    # cmake --install for this build. The prefix is GDUUID_INSTALL_PREFIX,
    # under the source worktree when the path is relative. Files go in
    # <prefix>/addons/enetheru.uuid-extension/. Configurations install in
    # recorded order and the last one wins the slot for that platform and
    # target (narrow with --config-regex).
    from src.select import chosen_config_types

    spec = build['gduuid_install']
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
