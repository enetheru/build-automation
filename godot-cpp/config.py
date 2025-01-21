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

stats = {{'name':'{name}'}}

if config['fetch']:
    console.set_window_title('Fetch - {name}')
    stats['fetch'] = {{'name':'fetch'}}
    with Timer(container=stats['fetch']):
        git_fetch( config )
        
if config['build']:
    console.set_window_title('Build - {name}')
    stats['build'] = {{'name':'build'}}
    with Timer(container=stats['build']):
        scons_build( config )

h3( 'build_config stats' )
pp( stats, indent=4 )
"""

cmake_script = """
from pprint import pp
from actions import *

stats = {{'name':'{name}'}}
cmake = config['cmake']

#[=================================[ Fetch ]=================================]
if config['fetch']:
    stats['fetch'] = {{'name':'fetch'}}
    console.set_window_title('Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )

#[===============================[ Configure ]===============================]
if 'godot_build_profile' in cmake:
    profile_path = Path(cmake['godot_build_profile'])
    if not profile_path.is_absolute():
        profile_path = config['source_dir'] / profile_path
    h4(f'using build profile: "{{profile_path}}"')
    cmake['config_vars'].append(f'-DGODOT_BUILD_PROFILE="{{os.fspath(profile_path)}}"')

if config['prepare']:
    console.set_window_title('Prepare - {name}')
    stats['prepare'] = {{'name':'prepare'}}
    with Timer(container=stats['prepare']):
        cmake_configure( config )

#[=================================[ Build ]=================================]
if config['build']:
    stats['build'] = {{'name':'build'}}
    console.set_window_title('Build - {name}')
    with Timer(container=stats['build']):
        cmake_build( config )

#[==================================[ Test ]==================================]


#[=================================[ Stats ]=================================]
h3( 'build_config stats' )
pp( stats, indent=4 )
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
              'mingw32-gcc',        # i686      gcc linking against msvcrt
              'mingw64-gcc',        # x86_64    gcc linking against msvcrt
              'ucrt64-gcc',         # x86_64    gcc linking against ucrt
              'clang32-clang',      # i686      clang linking against ucrt
              'clang64-clang',      # x86_64    clang linking against ucrt
              'clangarm64-clang']   # aarch64   clang linking against ucrt

build_tool = ['scons','cmake']

generators = ['Visual Studio 17 2022', 'Ninja', 'Ninja Multi-Config']

for toolchain, build_tool in itertools.product( toolchains, build_tool):
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

    match build_tool, toolchain:
        case 'cmake', 'msvc':
            cfg.script = cmake_script
        case 'scons', 'msvc':
            cfg.script = scons_script
        case _:
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
                    cfg.cmake['build_vars'].append('--config Release')
                    cfg.cmake['tool_vars'] = msbuild_extras
                case _:
                    raise "Invalid Generator"

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