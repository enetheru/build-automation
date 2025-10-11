from types import SimpleNamespace

from share.config import git_base


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

    from share.config import project_base, build_base, scons_base, cmake_base
    from share.expand_config import expand_host_env, expand_cmake, expand_func
    from share.snippets import source_git, show_stats

    project = SimpleNamespace({**vars(project_base), **{
        'name': 'godot-cpp-test',
        'gitdef': {

        },
        'sources':{
            'git': SimpleNamespace({**vars(git_base), **{
                'url': "https://github.com/enetheru/godot-cpp-test.git/",
                'ref': "main",
            }}),
        },
        'buildtools': {
            'scons': SimpleNamespace({ **vars(cmake_base), **{}}),
            'cmake': SimpleNamespace({ **vars(scons_base), **{}})
        },
    }})


    build_start = SimpleNamespace({**vars(build_base), **{
        'verbs': ['source'],
        'script_parts': [source_git],
        'arch': 'x86_64'
    }})

    builds = expand_host_env( build_start, project )
    builds = expand_func( builds,  expand_cmake )

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