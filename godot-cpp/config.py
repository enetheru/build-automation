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

name = config['name']
build_target = config['build_target']

stats = {'name':name}

if config['fetch']:
    stats['fetch'] = {'name':'fetch'}
    terminal_title(f'Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )
        
if config['build']:
    stats['build'] = {'name':'build'}
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

# MARK: Configs
# ╓───────────────────────────────────────────────────────────────────────────╖
# ║          ██████  ██████  ███    ██ ███████ ██  ██████  ███████            ║
# ║         ██      ██    ██ ████   ██ ██      ██ ██       ██                 ║
# ║         ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ███████            ║
# ║         ██      ██    ██ ██  ██ ██ ██      ██ ██    ██      ██            ║
# ║          ██████  ██████  ██   ████ ██      ██  ██████  ███████            ║
# ╙───────────────────────────────────────────────────────────────────────────╜
# Construct build configurations

#[============================[ Windows.SCons.* ]============================]
for build_target in ['template_release','template_debug','editor']:
    new_config = SimpleNamespace(**{
        'name' : f'Windows.SCons.{build_target}',
        'build_target':build_target,
        'env_type':'python',
        'env_script': scons_script
    })

    project_config.build_configs[new_config.name] = new_config

#[==========================[ Windows.SCons.test.* ]==========================]
for build_target in ['template_release','template_debug','editor']:
    new_config = SimpleNamespace(**{
        'name' : f'Windows.SCons.test.{build_target}',
        'build_target':build_target,
        'env_type':'python',
        'env_script': scons_script
    })

    project_config.build_configs[new_config.name] = new_config

#[============================[ Windows.CMake.* ]============================]
for build_target in ['template_release','template_debug','editor']:
    new_config = SimpleNamespace(**{
        'name' : f'Windows.CMake.test.{build_target}',
        'env_type':'python',
        'env_script': cmake_script,
        'godot_build_profile':'test/build_profile.json',
        'cmake_config_vars':['-DGODOT_ENABLE_TESTING=ON'],
        'cmake_build_vars':['--target',f'godot-cpp.test.{build_target}'],
    })

    project_config.build_configs[new_config.name] = new_config

#[================================[ grab_bag ]================================]
new_config = SimpleNamespace(**{
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'gitHash'  : "947f0071bce8a6dc575986f77250dd42826065e1",
    'name' : f'pr.grab_bag',
    'env_type':'python',
    'env_script': cmake_script,
    'godot_build_profile':'test/build_profile.json',
    'cmake_config_vars':['-DGODOT_ENABLE_TESTING=ON'],
    'cmake_build_vars':['--target',f'godot-cpp.test.template_release'],
})

project_config.build_configs[new_config.name] = new_config


#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}