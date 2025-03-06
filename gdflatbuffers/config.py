from types import SimpleNamespace
from share.expand_config import cmake_config_types

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
        'name':'gdflatbuffers',
        'gitdef':{
            'url':"https://github.com/enetheru/godot-flatbuffers.git/",
            'ref':"main",
        },
        'build_configs' : {}
    })


    build_base = SimpleNamespace(**{
        'verbs':['source'],
        'script_parts':[source_git],
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

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜