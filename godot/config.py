#!/usr/bin/env python
import copy
import sys
from types import SimpleNamespace

import rich

from share.toolchains import toolchains

# ╒════════════════════════════════════════════════════════════════════════════╕
# │                    ██████   ██████  ██████   ██████  ████████              │
# │                   ██       ██    ██ ██   ██ ██    ██    ██                 │
# │                   ██   ███ ██    ██ ██   ██ ██    ██    ██                 │
# │                   ██    ██ ██    ██ ██   ██ ██    ██    ██                 │
# │                    ██████   ██████  ██████   ██████     ██                 │
# ╘════════════════════════════════════════════════════════════════════════════╛

project_config = SimpleNamespace(
    **{"gitUrl": "https://github.com/godotengine/godot.git/", "build_configs": {}}
    # TODO Update Verbs
)

# MARK: Scripts
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _                                                      │
# │ / __| __ _ _(_)_ __| |_ ___                                                │
# │ \__ \/ _| '_| | '_ \  _(_-<                                                │
# │ |___/\__|_| |_| .__/\__/__/                                                │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯

def scons_script( config:dict, console:rich.console.Console ):
    from share.Timer import Timer
    from share.actions import git_checkout, scons_build

    def want( action:str ) -> bool:
        return action in config['verbs'] and action in config['actions']

    stats:dict = dict()
    timer = Timer()

    #[=================================[ Fetch ]=================================]
    if want('source'):
        console.set_window_title('Source - {name}')

        stats['source'] = timer.time_function( config, func=git_checkout )

    #[=================================[ Build ]=================================]
    if want('build') and timer.ok():
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

# MARK: Windows
# ╒════════════════════════════════════════════════════════════════════════════╕
# │            ██     ██ ██ ███    ██ ██████   ██████  ██     ██ ███████       │
# │            ██     ██ ██ ████   ██ ██   ██ ██    ██ ██     ██ ██            │
# │            ██  █  ██ ██ ██ ██  ██ ██   ██ ██    ██ ██  █  ██ ███████       │
# │            ██ ███ ██ ██ ██  ██ ██ ██   ██ ██    ██ ██ ███ ██      ██       │
# │             ███ ███  ██ ██   ████ ██████   ██████   ███ ███  ███████       │
# ╘════════════════════════════════════════════════════════════════════════════╛

variations = ['default', 'double']

def expand_variations( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant in variations:
        cfg = copy.deepcopy(config)

        match variant:
            case "default":
                pass

            case "double":
                # what's the point in using double precision on 32 bit architectures.
                if config.arch not in ['x86_64', 'arm64']: continue

                cfg.name += f".{variant}"
                cfg.scons["build_vars"].append("precision=double")

            case _:
                print( f"skipping variant: {variant}" )
                continue

        configs_out.append( cfg )
    return configs_out

def expand_platforms( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for platform in ['windows','web','android']:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'platform', platform )
        cfg.scons["build_vars"].append(f"platform={platform}")

        cfg.name = f"{cfg.host}.{cfg.toolchain.name}.{platform}.{cfg.arch}"

        if platform == 'web' and config.toolchain.name != 'emsdk': continue
        if config.toolchain.name == 'emsdk' and platform != 'web': continue

        if platform == 'android' and config.toolchain.name != 'android': continue
        if config.toolchain.name == 'android' and platform != 'android': continue

        match platform:
            case "windows":
                pass

            case "android" | 'web':
                cfg.name = f"{config.host}.{platform}"

            case _:
                print( f"skipping platform: {platform}" )
                continue
        configs_out += expand_variations( cfg )
    return configs_out

def expand_arch( config:SimpleNamespace ) -> list:
    # List of CPU architectures from the arch setting in godot
    # (auto|x86_32|x86_64|arm32|arm64|rv64|ppc32|ppc64|wasm32|loongarch64)
    configs_out:list = []
    for arch in config.toolchain.arch:
        cfg = copy.deepcopy(config)

        cfg.name += f'.{arch}'
        setattr( cfg, 'arch', arch )
        cfg.scons['build_vars'].append(f'arch={arch}')

        configs_out += expand_platforms( cfg )
    return configs_out


def expand_toolchains( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for toolchain in toolchains.values():
        cfg = copy.deepcopy(config)

        cfg.name += f".{toolchain.name}"
        setattr(cfg, 'toolchain', toolchain )

        match toolchain.name:
            case "msvc" | 'emsdk' | 'android':
                pass

            case "llvm":
                cfg.scons["build_vars"].append("use_llvm=yes")

            case "llvm-mingw" | "msys2-clang64":
                cfg.scons["build_vars"].append("use_mingw=yes")
                cfg.scons["build_vars"].append("use_llvm=yes")

            case "mingw64" | "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
                cfg.scons["build_vars"].append("use_mingw=yes")

            case _:
                print( f"skipping toolchain: {toolchain.name}" )
                continue

        configs_out += expand_arch( cfg )
    return configs_out

def base_config() -> SimpleNamespace:
    import platform
    host = 'unknown'
    match platform.system():
        case 'Windows':
            host  = 'w'

    match platform.architecture()[0]:
        case '64bit':
            host += '64'

    if host == 'unknown':
        print( "Failed to match host platform")
        exit(1)

    return SimpleNamespace( **{
        "name": host,
        "host": host,
        'script':scons_script,
        'verbs':['source', 'build'],
        "scons": {
            "targets": ["template_release", "template_debug", "editor"],
            "build_vars":["compiledb=yes"]
        }
    })

def generate_configs():
    for cfg in  expand_toolchains( base_config() ):
        project_config.build_configs[cfg.name] = cfg

generate_configs()

# MARK: Linux
# ╒════════════════════════════════════════════════════════════════════════════╕
# │                      ██      ██ ███    ██ ██    ██ ██   ██                 │
# │                      ██      ██ ████   ██ ██    ██  ██ ██                  │
# │                      ██      ██ ██ ██  ██ ██    ██   ███                   │
# │                      ██      ██ ██  ██ ██ ██    ██  ██ ██                  │
# │                      ███████ ██ ██   ████  ██████  ██   ██                 │
# ╘════════════════════════════════════════════════════════════════════════════╛
"""
== Platforms ==
- Linux
- MacOS
- iOS
- Windows
- Android
- Web
== Toolchains ==
- OSXCross
- cctools(for iOS)
- gcc
- clang
- riscv
- mingw32
- android(clang)
- emsdk(clang)
"""
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _    _                                                                    │
# │ | |  (_)_ _ _  ___ __                                                      │
# │ | |__| | ' \ || \ \ /                                                      │
# │ |____|_|_||_\_,_/_\_\                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      __   _                                                             │
# │ \ \    / /__| |__                                                          │
# │  \ \/\/ / -_) '_ \                                                         │
# │   \_/\_/\___|_.__/                                                         │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: MacOS
# ╒════════════════════════════════════════════════════════════════════════════╕
# │                   ███    ███  █████   ██████  ██████  ███████              │
# │                   ████  ████ ██   ██ ██      ██    ██ ██                   │
# │                   ██ ████ ██ ███████ ██      ██    ██ ███████              │
# │                   ██  ██  ██ ██   ██ ██      ██    ██      ██              │
# │                   ██      ██ ██   ██  ██████  ██████  ███████              │
# ╘════════════════════════════════════════════════════════════════════════════╛
"""
== Platforms ==
- MacOS

- android
- web
== Toolchains ==
- appleclang
- android(clang)
- emsdk(clang)
"""
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __          ___  ___                                                  │
# │ |  \/  |__ _ __ / _ \/ __|                                                 │
# │ | |\/| / _` / _| (_) \__ \                                                 │
# │ |_|  |_\__,_\__|\___/|___/                                                 │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  ___  ___                                                               │
# │ (_)/ _ \/ __|                                                              │
# │ | | (_) \__ \                                                              │
# │ |_|\___/|___/                                                              │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      __   _                                                             │
# │ \ \    / /__| |__                                                          │
# │  \ \/\/ / -_) '_ \                                                         │
# │   \_/\_/\___|_.__/                                                         │
# ╰────────────────────────────────────────────────────────────────────────────╯