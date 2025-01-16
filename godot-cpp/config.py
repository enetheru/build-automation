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
from pprint import pp
from actions import *

stats = {{'name':'{name}'}}

if {fetch}:
    stats['fetch'] = {{'name':'fetch'}}
    terminal_title(f'Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )
        
if {build}:
    stats['build'] = {{'name':'build'}}
    terminal_title(f"Build - {name}")
    with Timer(container=stats['build']):
        build_scons( config, build_vars=[f'target={build_target}'] )

h3( 'build_config stats' )
pp( stats, indent=4 )
"""

cmake_script = """
# <above this line is the config and environment code>

from pprint import pp
from actions import *

name = config['name']

build_root = Path(config['build_root'])

if 'godot_build_profile' in config.keys():
    build_profile = build_root / config['godot_build_profile']
    config['cmake_config_vars'] += [f'-DGODOT_BUILD_PROFILE="{build_profile}"']

stats = {'name':name}

if config['fetch']:
    stats['fetch'] = {'name':'fetch'}
    terminal_title(f'Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )

if config['prepare']:
    stats['prepare'] = {'name':'prepare'}
    terminal_title(f"Prepare - {name}")
    with Timer(container=stats['prepare']):
        prepare_cmake( config, prep_vars=config['cmake_config_vars'])
        
if config['build']:
    stats['build'] = {'name':'build'}
    terminal_title(f"Build - {name}")
    with Timer(container=stats['build']):
        build_cmake( config, build_vars=config['cmake_build_vars'] )

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

#[=================================[ SCons ]=================================]
for build_target in ['template_release','template_debug','editor']:
    new_config = SimpleNamespace(**{
        'name' : f'Windows.SCons.{build_target}',
        'build_target':build_target,
        'script': scons_script,
        'shell':'msys2.clang64'
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