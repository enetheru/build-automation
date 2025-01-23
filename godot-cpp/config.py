#!/usr/bin/env python
import copy
from types import SimpleNamespace
import itertools

project_config = SimpleNamespace(**{
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'build_configs' : {}
})

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

scons_script = """
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pprint import pp
from actions import *

stats:dict = dict()
timer = Timer()

#[=================================[ Fetch ]=================================]
if config['fetch']:
    console.set_window_title('Fetch - {name}')
    stats['fetch'] = timer.time_function( config, func=git_fetch )

#[=================================[ Build ]=================================]
if config['build'] and timer.ok():
    console.set_window_title('Build - {name}')
    stats['build'] = timer.time_function( config, func=scons_build )

#[=================================[ Stats ]=================================]
from rich.table import Table
table = Table(title="Stats", highlight=True, min_width=80)

table.add_column("Section", style="cyan", no_wrap=True)
table.add_column("Status", style="magenta")
table.add_column("Duration", style="green")

for cmd_name, cmd_stats in stats.items():
    table.add_row( cmd_name, f'{{cmd_stats['status']}}', f'{{cmd_stats['duration']}}')

print( table )
if not timer.ok():
    exit(1)
"""

cmake_script = """
from actions import *

stats:dict = dict()
cmake = config['cmake']
timer = Timer()

#[=================================[ Fetch ]=================================]
if config['fetch']:
    console.set_window_title('Fetch - {name}')
    stats['fetch'] = timer.time_function( config, func=git_fetch )

#[===============================[ Configure ]===============================]
if 'godot_build_profile' in cmake:
    profile_path = Path(cmake['godot_build_profile'])
    if not profile_path.is_absolute():
        profile_path = config['source_dir'] / profile_path
    h4(f'using build profile: "{{profile_path}}"')
    cmake['config_vars'].append(f'-DGODOT_BUILD_PROFILE="{{os.fspath(profile_path)}}"')

if config['prepare'] and timer.ok():
    console.set_window_title('Prepare - {name}')
    stats['prepare'] = timer.time_function( config, func=cmake_configure )

#[=================================[ Build ]=================================]
if config['build'] and and timer.ok():
    console.set_window_title('Build - {name}')
    stats['build'] = timer.time_function( config, func=cmake_build )

#[==================================[ Test ]==================================]
if config['test'] and and timer.ok():
    pass

#[=================================[ Stats ]=================================]
from rich.table import Table
table = Table(highlight=True, min_width=80)

table.add_column("Section",no_wrap=True)
table.add_column("Status")
table.add_column("Duration")

for cmd_name, cmd_stats in stats.items():
    table.add_row( cmd_name, f'{{cmd_stats['status']}}', f'{{cmd_stats['duration']}}', style='red')

print( table )
if not timer.ok():
    exit(1)
"""
msbuild_extras = ['--', '/nologo', '/v:m', "/clp:'ShowCommandLine;ForceNoAlign'"]

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
# Build Targets
#   - lib - 'template_release','template_debug','editor'
#   - test - 'template_release','template_debug','editor'
#
# Build Tool
#   - CMake
#   - SCons
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
#   - Thread/noThread
#   - Profile/NoProfile
#   - Precision single/double
#   - Hot Re-Load ON/OFF
#   - Exceptions ON/OFF

# Naming of builds.
#   host.env.build_tool.compiler.options
# Where any of the above are omitted it obvious

# The variations of toolchains for mingw are listed here: https://www.mingw-w64.org/downloads/
toolchains = ['msvc',               # Microsoft Visual Studio
              'llvm-clang',         # clang from llvm.org
              'llvm-clang-cl',      # clang-cl from llvm.org
              'llvm-mingw-i686',    # llvm based mingw-w64 toolchain.
              'llvm-mingw-x86_64',  #   https://github.com/mstorsjo/llvm-mingw
              'llvm-mingw-aarch64', #
              'llvm-mingw-armv7',   #
              'mingw64',            # mingw from https://github.com/niXman/mingw-builds-binaries/releases,
                                    #   This is also the default toolchain for clion.
              'android',            # https://developer.android.com/tools/sdkmanager
              'emscripten',         # https://emscripten.org/
              'msys2-mingw32',      # i686      gcc linking against msvcrt
              'msys2-mingw64',      # x86_64    gcc linking against msvcrt
              'msys2-ucrt64',       # x86_64    gcc linking against ucrt
              'msys2-clang32',      # i686      clang linking against ucrt
              'msys2-clang64',      # x86_64    clang linking against ucrt
              'msys2-clangarm64']   # aarch64   clang linking against ucrt

build_tool = ['scons','cmake']

generators = ['Visual Studio 17 2022', 'Ninja', 'Ninja Multi-Config']

for build_tool, toolchain in itertools.product( build_tool, toolchains):
    cfg = SimpleNamespace(**{
        'name' : f'w64.{build_tool}.{toolchain}',
        'shell':'pwsh',
        'build_tool':build_tool,
        'script': None,
        'cmake':{
            'build_dir':'build-cmake',
            'godot_build_profile':'test/build_profile.json',
            'config_vars':['-DGODOT_ENABLE_TESTING=ON'],
            'build_vars':[],
            'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
        },
        'scons':{
            'build_dir':'test',
            'build_vars':['build_profile=build_profile.json'],
            'targets':['template_release','template_debug','editor'],
        },
    })

    if toolchain.startswith('msys2'):
        cfg.shell = toolchain

    match build_tool:
        case 'cmake':
            cfg.script = cmake_script
        case 'scons':
            cfg.script = scons_script


    match build_tool, toolchain:
        case 'cmake' | 'scons', 'msvc' | 'msys2-ucrt64':
            pass
        case 'scons','msys2-ucrt64':
            cfg.scons['build_vars'] += ['use_mingw=yes']
        case 'scons','msys2-clang64':
            cfg.scons['build_vars'] += ['use_mingw=yes', 'use_llvm=yes']
        case _:
            print( f'ignoring combination: {build_tool} - {toolchain}')
            continue

    # Add the generator variations.
    original = cfg
    if build_tool == 'cmake':
        for gen in generators:
            cfg = copy.deepcopy( original )
            match gen:
                case 'Ninja':
                    cfg.name = original.name + '.ninja'
                case 'Ninja Multi-Config':
                    cfg.name = original.name + '.ninja-multi'
                    cfg.cmake['build_vars'].append('--config Release')
                case 'Visual Studio 17 2022':
                    if not toolchain == 'msvc':
                        cfg.name = original.name + '.msvc'
                    cfg.cmake['build_vars'].append('--config Release')
                    cfg.cmake['tool_vars'] = msbuild_extras
                case _:
                    continue

            cfg.cmake['config_vars'] = [f'-G"{gen}"'] + original.cmake['config_vars']
            project_config.build_configs[cfg.name] = cfg
    else:
        project_config.build_configs[cfg.name] = cfg

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


#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}