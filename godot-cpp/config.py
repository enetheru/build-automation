#!/usr/bin/env python
import time
import types
from types import SimpleNamespace

# My imports
from share.format import *

target_config = SimpleNamespace(**{
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'gitHash' : None,
    'build_configs' : {}
})

#TEMPORARY FIX
jobs = 1
verbose = 1

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

def build_scons(_self, target: str, build_vars: list):
    
    # requires SConstruct file existing in the current directory.
    # SCons - Remove generated source files if exists.
#     if( -Not (Test-Path "SConstruct" -PathType Leaf) ) {
#         Write-Error "BuildSCons: Missing '$(Get-Location)\SConstruct'"
# #        Return 1
#     }
    
    do_jobs     = "-j $jobs" if jobs > 0 else None
    do_verbose  = "verbose=yes" if verbose is True else None
    
    build_vars = [ do_jobs, do_verbose] + build_vars
    
    figlet( _self.name, {'font':'small'} )
    h3( f'Config: {_self.name}' )
    h3( f'Target: {target}' )
    start_time = time.process_time()
        
    # FIXME Format-Eval "scons $($buildVars -Join ' ') target=$target"
    print( f"scons {' '.join(filter(None, build_vars))} target={target}" )

    time.sleep(1) # Temporary
        
    _self.duration = time.process_time() - start_time
    _self.status = 'completed'
        
    h3( 'BuildScons Completed' )
        
    fill( "-")
# Construct scons builder object
scons_command.command = types.MethodType( build_scons, scons_command )

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
    # 'build_command' : scons_command
})
# new_config.build = types.MethodType( lambda _self: _self.build_command.command("first",["build vars"]), new_config )

target_config.build_configs[new_config.name] = new_config

#[=============================[ test config 2 ]=============================]
new_config = SimpleNamespace(**{
    'name' : 'Windows.scons.template_release',
    'gitUrl'  : "http://github.com/enetheru/godot-cpp.git",
    'gitHash' : None,
    # 'build_command' : scons_command
})
# new_config.build = types.MethodType( lambda _self: _self.build_command.command("second",["build vars"]), new_config )

target_config.build_configs[new_config.name] = new_config

#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}
