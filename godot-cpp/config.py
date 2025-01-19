#!/usr/bin/env python
from types import SimpleNamespace

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
    stats['fetch'] = {{'name':'fetch'}}
    console.set_window_title('Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )
        
if config['build']:
    for target in {build_targets}:
        build_vars = {build_vars} + [f'target={{target}}']
        stats['build'] = {{'name':'target'}}
        console.set_window_title('Build - {name}')
        with Timer(container=stats['build']):
            build_scons( config, build_vars=build_vars )

h3( 'build_config stats' )
pp( stats, indent=4 )
"""

cmake_script = """
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pprint import pp
from actions import *

stats = {{'name':'{name}'}}

#[=================================[ Fetch ]=================================]
if config['fetch']:
    stats['fetch'] = {{'name':'fetch'}}
    console.set_window_title('Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )

#[===============================[ Configure ]===============================]
cmake_config_vars = config['prep_vars']

if config['build_profile']:
    profile_path = Path(config['build_profile'])
    if not profile_path.is_absolute():
        profile_path = config['source_dir'] / profile_path
    h4(f'using build profile:{{profile_path}}')
    cmake_config_vars.append(f'-DGODOT_BUILD_PROFILE="{{os.fspath(profile_path)}}"')

if config['prepare']:
    stats['prepare'] = {{'name':'prepare'}}
    console.set_window_title('Prepare - {name}')
    with Timer(container=stats['prepare']):
        prepare_cmake( config, prep_vars=cmake_config_vars)

#[=================================[ Build ]=================================]
if config['build']:
    stats['build'] = {{'name':'build'}}
    console.set_window_title('Build - {name}')
    with Timer(container=stats['build']):
        build_cmake( config )

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

#[=======================[ SCons Default with Profile ]=======================]
new_config = SimpleNamespace(**{
    'name' : f'w64.scons.msvc',
    'shell':'pwsh',
    'script': scons_script,
    'build_dir':'test',
    'build_vars':['build_profile="build_profile.json"'],
    'build_targets':['template_release','template_debug','editor'],
})
project_config.build_configs[new_config.name] = new_config

#[================[ MSYS2/CLANG64 SCons Default with Profile ]================]
new_config = SimpleNamespace(**{
    'name' : 'w64.clang64.scons',
    'shell':'msys2.clang64',
    'script': scons_script,
    'build_dir':'test',
    'build_vars':['build_profile="build_profile.json"', 'use_llvm=yes', 'use_mingw=yes'],
    'build_targets':['template_release','template_debug','editor']
})
project_config.build_configs[new_config.name] = new_config

#[================[ MSYS2/UCRT64 SCons Default with Profile ]================]
new_config = SimpleNamespace(**{
    'name' : 'w64.ucrt64.scons',
    'shell':'msys2.ucrt64',
    'script': scons_script,
    'build_dir':'test',
    'build_vars':['build_profile="build_profile.json"', 'use_mingw=yes'],
    'build_targets':['template_release','template_debug','editor']
})
project_config.build_configs[new_config.name] = new_config

#[=======================[ CMake Default with Profile ]=======================]
new_config = SimpleNamespace(**{
    'name' : 'w64.cmake.msvc',
    'shell':'pwsh',
    'script': cmake_script,
    'build_dir':'cmake-build',
    'build_profile':'test/build_profile.json',
    'prep_vars':['--fresh', '-DGODOT_ENABLE_TESTING=ON'],
    'build_vars':['--config Release'],
    'build_targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
})
project_config.build_configs[new_config.name] = new_config
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