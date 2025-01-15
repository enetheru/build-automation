#!/usr/bin/env python
from types import SimpleNamespace

target_config = SimpleNamespace(**{
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
#[=====================[ Windows.SCons.template_release ]=====================]
new_config = SimpleNamespace(**{
    'name' : 'Windows.SCons.template_release',
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'env_type':'python',
    'env_script': """
from actions import *

stats = {}

name = config['name']

if config['fetch']:
    stats['fetch'] = {'name':'fetch'}
    terminal_title(f'Fetch - {name}')
    with Timer(container=stats['fetch']):
        git_fetch( config )
        
if config['build']:
    stats['build'] = {'name':'build'}
    terminal_title(f"Build - {name}")
    with Timer(container=stats['build']):
        build_scons( config, build_vars=['target=template_release'] )
"""
})

target_config.build_configs[new_config.name] = new_config
#[======================[ Windows.SCons.template_debug ]======================]

new_config = SimpleNamespace(**{
    'name' : 'Windows.SCons.template_debug',
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'env_type':'python',
    'env_script': f"""
from actions import *

name = config['name']

if config['fetch']:
    terminal_title(f'Fetch - {{name}}')
    stats = {{'name':'fetch'}}
    with timer(container=stats):
        git_fetch(config)
        
if config['build']:
    terminal_title(f"Build - {{name}}")
    stats = {{'name':'build'}}
    with timer(container=stats):
        build_scons( config )
"""
})

target_config.build_configs[new_config.name] = new_config

#[==========================[ Windows.SCons.editor ]==========================]
new_config = SimpleNamespace(**{
    'name' : 'Windows.SCons.editor',
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
})

target_config.build_configs[new_config.name] = new_config

#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}
