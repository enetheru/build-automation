#!/usr/bin/env python
import copy
from io import StringIO
from types import SimpleNamespace

import rich

from share.env_commands import toolchains
from share.generate import func_as_script

# Build Targets
#   - lib - 'template_release','template_debug','editor'
#   - test - 'template_release','template_debug','editor'
#
# - msvc
#   - msvc
#   - using clang-cl
# - mingw32
#   - clion builtin
#   - mingw64
#   - msys64/ucrt64
#   - msys64/mingw32
#   - msys64/mingw64
# - clang
#   - llvm
#   - llvm-mingw
#   - msys64/clang32
#   - msys64/clang64
#   - msys64/clangarm64
# - android(clang)
# - emscripten(clang)
#
# Option Variations
# TODO List off the variations

project_config = SimpleNamespace(
    **{"gitUrl": "https://github.com/godotengine/godot.git/", "build_configs": {}}
)

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def scons_script( config:dict, toolchain:dict, console:rich.console.Console ):
    from share.Timer import Timer
    from share.actions import git_checkout, scons_build

    actions = config['actions']
    stats:dict = dict()
    timer = Timer()

    #[=================================[ Fetch ]=================================]
    if actions['source']:
        console.set_window_title('Source - {name}')

        stats['source'] = timer.time_function( config, func=git_checkout )

    #[=================================[ Build ]=================================]
    if actions['build'] and timer.ok():
        console.set_window_title('Build - {name}')

        stats['build'] = timer.time_function( config, func=scons_build )

    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(title="Stats", highlight=True, min_width=80)

    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Duration", style="green")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}')

    print( table )
    if not timer.ok():
        exit(1)

def write_script( build:SimpleNamespace, script:StringIO ):
    script.write( func_as_script( scons_script ) )

# ╒════════════════════════════════════════════════════════════════════════════╕
# │            ██████  ███████ ███████ ██   ██ ████████  ██████  ██████        │
# │            ██   ██ ██      ██      ██  ██     ██    ██    ██ ██   ██       │
# │            ██   ██ █████   ███████ █████      ██    ██    ██ ██████        │
# │            ██   ██ ██           ██ ██  ██     ██    ██    ██ ██            │
# │            ██████  ███████ ███████ ██   ██    ██     ██████  ██            │
# ╘════════════════════════════════════════════════════════════════════════════╛
# Construct build configurations
# MARK: Linux
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _    _                                                                    │
# │ | |  (_)_ _ _  ___ __                                                      │
# │ | |__| | ' \ || \ \ /                                                      │
# │ |____|_|_||_\_,_/_\_\                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: MacOS
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __          ___  ___                                                  │
# │ |  \/  |__ _ __ / _ \/ __|                                                 │
# │ | |\/| / _` / _| (_) \__ \                                                 │
# │ |_|  |_\__,_\__|\___/|___/                                                 │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Windows
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      ___         _                                                      │
# │ \ \    / (_)_ _  __| |_____ __ _____                                       │
# │  \ \/\/ /| | ' \/ _` / _ \ V  V (_-<                                       │
# │   \_/\_/ |_|_||_\__,_\___/\_/\_//__/                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯

for toolchain in toolchains.values():
    cfg = SimpleNamespace(
        **{
            "name": f"w64.{toolchain.name}",
            "shell": "pwsh",
            "build_tool": "scons",
            'build_verbs':['source', 'build'],
            "toolchain": copy.deepcopy(toolchain),
            'write':write_script,
            "scons": {
                "build_vars": [],
                "targets": ["template_release", "template_debug", "editor"],
            },
            "godot_tr": "bin/godot.windows.template_release.x86_64.exe",
            "godot_td": "bin/godot.windows.template_debug.x86_64.exe",
            "godot_e": "bin/godot.windows.editor.x86_64.exe",
        }
    )

    if toolchain.name.startswith("msys2"):
        cfg.shell = toolchain

    match toolchain.name:
        case "msvc":
            cfg.shell = "pwsh-dev"
            project_config.build_configs[cfg.name] = cfg
            continue

        case "llvm":
            cfg.scons["build_vars"].append("use_llvm=yes")
            project_config.build_configs[cfg.name] = cfg
            continue

        case "llvm-mingw":
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")
            project_config.build_configs[cfg.name] = cfg
            continue

        case "msys2-ucrt64":
            # cfg.gitHash = 'df2f263531d0e26fb6d60aa66de3e84165e27788'
            cfg.scons["build_vars"].append("use_mingw=yes")
            project_config.build_configs[cfg.name] = cfg
            continue

        case "msys2-clang64":
            # cfg.gitHash = 'df2f263531d0e26fb6d60aa66de3e84165e27788'
            cfg.scons["build_vars"] += ["use_mingw=yes", "use_llvm=yes"]
            project_config.build_configs[cfg.name] = cfg
            continue

        case "mingw64":
            cfg.scons["build_vars"] += ["use_mingw=yes"]
            project_config.build_configs[cfg.name] = cfg
            continue

        case "android":
            cfg.scons["build_vars"] += ["platform=android"]
            project_config.build_configs[cfg.name] = cfg
            continue

        case "emsdk":
            cfg.scons["build_vars"] += ["platform=web"]
            cfg.shell = "emsdk"
            project_config.build_configs[cfg.name] = cfg
            continue

        case _:
            print(f"ignoring toolchain: {toolchain.name}")
            continue

# ╒════════════════════════════════════════════════════════════════════════════╕
# │                 ███    ███  ██████  ██████  ██ ██      ███████             │
# │                 ████  ████ ██    ██ ██   ██ ██ ██      ██                  │
# │                 ██ ████ ██ ██    ██ ██████  ██ ██      █████               │
# │                 ██  ██  ██ ██    ██ ██   ██ ██ ██      ██                  │
# │                 ██      ██  ██████  ██████  ██ ███████ ███████             │
# ╘════════════════════════════════════════════════════════════════════════════╛

# MARK: Android
# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: iOS
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  ___  ___                                                               │
# │ (_)/ _ \/ __|                                                              │
# │ | | (_) \__ \                                                              │
# │ |_|\___/|___/                                                              │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Web
# ╒════════════════════════════════════════════════════════════════════════════╕
# │                            ██     ██ ███████ ██████                        │
# │                            ██     ██ ██      ██   ██                       │
# │                            ██  █  ██ █████   ██████                        │
# │                            ██ ███ ██ ██      ██   ██                       │
# │                             ███ ███  ███████ ██████                        │
# ╘════════════════════════════════════════════════════════════════════════════╛


# {cmake,meson}
# {make,ninja,scons,msvc,autotools,gradle,etc}
# {gcc,clang,msvc,appleclang,ibm,etc}
# {ld,lld,gold,mold,appleld,msvc}
