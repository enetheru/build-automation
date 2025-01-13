#!/usr/bin/env python
from types import SimpleNamespace

# My imports
from share.format import *

target_config = SimpleNamespace(**{
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'gitHash' : None,
    'build_configs' : {}
})

# MARK: SConsBuild
# ╓───────────────────────────────────────────────────────────────────────────╖
# ║   ██████  █████  █████  ███   ██ ██████ █████  ██   ██ ██ ██     █████    ║
# ║   ██     ██     ██   ██ ████  ██ ██     ██  ██ ██   ██ ██ ██     ██  ██   ║
# ║   ██████ ██     ██   ██ ██ ██ ██ ██████ █████  ██   ██ ██ ██     ██  ██   ║
# ║       ██ ██     ██   ██ ██  ████     ██ ██  ██ ██   ██ ██ ██     ██  ██   ║
# ║   ██████  █████  █████  ██   ███ ██████ █████   █████  ██ ██████ █████    ║
# ╙───────────────────────────────────────────────────────────────────────────╜
scons_command = SimpleNamespace(**{
    'name'        : "SCons Build",
    'status'      : "dnf",
    'duration'    : None
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

#[=============================[ test config 1 ]=============================]
new_config = SimpleNamespace(**{
    'name' : 'Windows.scons.template_debug',
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'gitHash' : None,
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

#[=============================[ test config 2 ]=============================]
new_config = SimpleNamespace(**{
    'name' : 'Windows.scons.template_release',
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'gitHash' : None,
})

target_config.build_configs[new_config.name] = new_config

#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}
