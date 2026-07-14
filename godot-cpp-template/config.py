import copy
from types import SimpleNamespace

from rich import json
from rich.pretty import pprint

from src.config import git_base
from src.expand_config import expand_attr_list, short_host, expand_cmake
import src.format as fmt

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    from godot.config import godot_platforms, godot_arch

    from src.config import project_base, build_base, scons_base, cmake_base
    from src.expand_config import expand_host_env, expand_cmake, expand_func
    from share.snippets import source_git, show_stats

    origin = SimpleNamespace({**vars(git_base), **{
        'remote':'origin',
        'url': "https://github.com/godotengine/godot-cpp-template.git/",
        'ref': "main",
    }})

    sources:dict = {
        'origin': origin,
        'tracylib': SimpleNamespace({**vars(origin), **{
            'remote':'enetheru',
            'url': "https://github.com/enetheru/godot-cpp-template.git/",
            'ref': "godot-shared-tracy",
        }}),
    }

    project = SimpleNamespace({**vars(project_base), **{
        'name': 'godot-cpp-test',
        'path': opts.path / 'godot-cpp-template',
        'verbs': ['fetch'],
        'sources':sources,
        'buildtools': {
            'scons': SimpleNamespace({ **vars(scons_base), **{
                'expand':expand_scons,
                'configure':configure_scons,
            }}),
            'cmake': SimpleNamespace({ **vars(cmake_base), **{
                'targets':['tracy-example'],
                'expand':expand_cmake2,
                'configure':configure_cmake,
            }})
        },
    }})

    # == Expansion ==

    # source definitions.
    builds:list[SimpleNamespace] = expand_func(
        [build_base],
        expand_attr_list,
        'source_def',
        sources.values() )
    fmt.hu(f"build configs after source expansion: {len(builds)}")

    # Toolchains
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'toolchain',
        opts.toolchains.values() )
    fmt.hu(f"build configs after toolchain expansion: {len(builds)}")

    # godot targets
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'target',
        ['editor', 'template_debug', 'template_release'] )
    fmt.hu(f"build configs after godot target expansion: {len(builds)}")

    # Build tools
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'buildtool',
        project.buildtools.values() )
    fmt.hu(f"build configs after build tool expansion: {len(builds)}")

    # == Variations ==
    builds = expand_func( builds, expand_variations )
    fmt.hu(f"build configs after variation expansion: {len(builds)}")

    # == Configure ==
    builds = [
        b for b in builds
        if all( f(b) for f in getattr(b, 'configure_funcs', []) )
    ]

    # == name the build ==
    for build in builds:
        tc = build.toolchain
        bt = build.buildtool

        bt_name = bt.name
        if bt_name == 'cmake':
            bt_name = f'{bt.name}-{bt.short_type}-{bt.short_gen}'

        name_parts = [
            short_host(),
            bt_name,
            tc.name,
            tc.target_arch if tc.target_platform not in ['emscripten'] else None,
            godot_platforms[tc.target_platform] if tc.target_platform not in ['android', 'emscripten'] else None,
            build.target,
            build.variant if build.variant != 'default' else None,
            # build.source_def.remote if build.source_def.remote != 'origin' else None,
            # build.source_def.ref
        ]

        build.name = '.'.join(filter(None, name_parts))
        build.source_dir =  build.name

        build.script_parts += [show_stats]

    project.build_configs = { v.name:v for v in builds }
    return project



    build_start = SimpleNamespace({**vars(build_base), **{
        'verbs': ['source'],
        'script_parts': [source_git],
        'arch': 'x86_64'
    }})

    builds = expand_host_env( build_start, project )

    # Only expand cmake on configs that actually use cmake
    cmake_builds = [b for b in builds if getattr(b.buildtool, 'name', None) == 'cmake']
    if cmake_builds: cmake_builds = expand_func(cmake_builds, expand_cmake)
    # Put them back (or replace the cmake ones)
    builds = [b for b in builds if getattr(b.buildtool, 'name', None) != 'cmake'] + cmake_builds


    # Rename
    for build in builds:

        toolchain = build.toolchain.name
        arch = godot_arch[build.arch]
        platform = godot_platforms[build.platform]

        if build.buildtool.name == 'cmake':

            cmake = build.buildtool
            short_gen = cmake.generators[cmake.generator]
            short_type = cmake.config_types[cmake.config_type]
        else:
            short_gen = None
            short_type = None

        name_parts = [
            build.host,
            toolchain if toolchain != 'emscripten' else None,
            platform if build.platform != 'android' else None,
            arch if arch != 'wasm32' else None,
            short_gen,
            short_type
        ]
        build.name = '.'.join(filter(None,name_parts))

        srcdir_parts = [
            build.host,
            toolchain,
            short_gen if short_gen != build.toolchain.name else None
        ]
        build.source_dir = '.'.join(filter(None, srcdir_parts))
        build.script_parts.append( show_stats )

    project.build_configs = {v.name: v for v in builds }
    return  project



# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

# MARK: SCons Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___  ___               ___         _      _                               │
# │ / __|/ __|___ _ _  ___ / __| __ _ _(_)_ __| |_                             │
# │ \__ \ (__/ _ \ ' \(_-< \__ \/ _| '_| | '_ \  _|                            │
# │ |___/\___\___/_||_/__/ |___/\__|_| |_| .__/\__|                            │
# │                                      |_|                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯


# MARK: Config Expansion
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _        ___                        _                   │
# │  / __|___ _ _  / _(_)__ _  | __|_ ___ __  __ _ _ _  __(_)___ _ _           │
# │ | (__/ _ \ ' \|  _| / _` | | _|\ \ / '_ \/ _` | ' \(_-< / _ \ ' \          │
# │  \___\___/_||_|_| |_\__, | |___/_\_\ .__/\__,_|_||_/__/_\___/_||_|         │
# │                     |___/          |_|                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Scons
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                                                                       │
# │ / __| __ ___ _ _  ___                                                      │
# │ \__ \/ _/ _ \ ' \(_-<                                                      │
# │ |___/\__\___/_||_/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_scons( build:SimpleNamespace ) -> list[SimpleNamespace]:
    new_build = copy.deepcopy(build)
    return [new_build]

def configure_scons( build:SimpleNamespace ) -> bool:
    return True

# FIXME, expand cmake is aready defined in the expand config section.
#   What I'd like instead is to have the configura and expand functions in
#   a list so that they can be stacked.
def expand_cmake2( build:SimpleNamespace ) -> list[SimpleNamespace]:
    return expand_cmake( build )

def configure_cmake( build:SimpleNamespace ) -> bool:
    return True

# MARK: Variant Config
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _          _      ___           __ _                        │
# │ \ \ / /_ _ _ _(_)__ _ _ _| |_   / __|___ _ _  / _(_)__ _                   │
# │  \ V / _` | '_| / _` | ' \  _| | (__/ _ \ ' \|  _| / _` |                  │
# │   \_/\__,_|_| |_\__,_|_||_\__|  \___\___/_||_|_| |_\__, |                  │
# │                                                    |___/                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

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

def configure_variant( config:SimpleNamespace ) -> bool:
    match config.build_tool:
        case 'scons':
            pass
        case 'cmake':
            pass

            # -DGODOT_USE_STATIC_CPP=OFF '-DGODOT_DEBUG_CRT=ON'
            # config.cmake["config_vars"].append('-DGODOT_ENABLE_TESTING=ON')


    match config.variant:
        case 'default':
            pass
        case 'double':
            if config.arch not in ['x86_64', 'arm64']: return False
            match config.build_tool:
                case 'scons':
                    config.scons["build_vars"].append("precision=double")
                case 'cmake':
                    config.cmake["config_vars"].append("-DGODOT_PRECISION=double")
                    pass
        case _:
            return False
    return True

def libtracy_config( cfg:SimpleNamespace ) -> bool:
    if cfg.buildtool.name != 'scons':
        return False
    if cfg.source_def.ref != ('godot-shared-tracy'):
        return False
    cfg.buildtool.build_vars += [
        'extra_suffix=tracy',
        "profiler=tracy",
        # "profiler_sample_callstack=yes",
        # "profiler_track_memory=yes",
        'tracy_as_shared=yes',
    ]
    tc = cfg.toolchain
    match tc.host:
        case 'Windows':
            cfg.buildtool.build_vars.append("profiler_path=C:/git/wolfpld/tracy")
        case 'Darwin':
            cfg.buildtool.build_vars.append("profiler_path=/Users/enetheru/src/tracy")
    return True

variations = {
    'default': lambda cfg: True,
    'libtracy': libtracy_config
}

# variations = ['default',
#               'double',
#               'nothreads',
#               'hotreload'
#               'exceptions']