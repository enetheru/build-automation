#!/usr/bin/env python
from types import SimpleNamespace

project_config = SimpleNamespace(**{
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'build_configs' : {}
})

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
        'env_script': """
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
    })

    project_config.build_configs[new_config.name] = new_config

#[==========================[ Windows.SCons.test.* ]==========================]
for build_target in ['template_release','template_debug','editor']:
    new_config = SimpleNamespace(**{
        'name' : f'Windows.SCons.test.{build_target}',
        'build_target':build_target,
        'build_root':'test',
        'env_type':'python',
        'env_script': """
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
    })

    project_config.build_configs[new_config.name] = new_config
#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}