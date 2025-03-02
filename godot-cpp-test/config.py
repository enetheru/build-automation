import copy
from types import SimpleNamespace

from share.expand_config import cmake_config_types
from share.script_preamble import *

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ):
    from godot.config import godot_platforms, godot_arch

    from share.expand_config import expand_host_env, cmake_generators, expand_cmake, expand_func
    from share.snippets import source_git, show_stats

    project = SimpleNamespace(**{
        'name':'godot-cpp-test',
        'gitdef':{
            'url':"https://github.com/enetheru/godot-cpp-test.git/",
            'ref':"main",
        },
        'build_configs' : {}
    })


    build_base = SimpleNamespace(**{
        'verbs':['source'],
        'script_parts':[source_git]
    })

    builds = expand_host_env( build_base, opts )
    builds = expand_func( builds,  expand_cmake )

    # Rename
    for build in builds:

        toolchain = build.toolchain.name
        arch = godot_arch[build.arch]
        platform = godot_platforms[build.platform]

        cmake = build.cmake
        short_gen = cmake_generators[cmake['generator']]
        short_type = cmake_config_types[cmake['config_type']]

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
    return { project.name: project }

variations = ['default',
    'double',
    'nothreads',
    'hotreload'
    'exceptions']

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜



# MARK: Config Expansion
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _        ___                        _                   │
# │  / __|___ _ _  / _(_)__ _  | __|_ ___ __  __ _ _ _  __(_)___ _ _           │
# │ | (__/ _ \ ' \|  _| / _` | | _|\ \ / '_ \/ _` | ' \(_-< / _ \ ' \          │
# │  \___\___/_||_|_| |_\__, | |___/_\_\ .__/\__,_|_||_/__/_\___/_||_|         │
# │                     |___/          |_|                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯
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