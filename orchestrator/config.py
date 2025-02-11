import copy
import inspect
from textwrap import indent
from types import SimpleNamespace

import rich

from share.actions import git_checkout
from share.expand_config import expand, expand_host_env
from share.toolchains import toolchains
from share.format import *

project_config = SimpleNamespace(**{
    'gitUrl'  : "https://github.com/enetheru/godot-orchestrator.git/",
    'gitHash':  'f266c8a3736a778be45b071e2f62ebecd56fd9ea',
    'godot':{
        'platforms':['android', 'ios', 'linux', 'macos', 'web', 'windows'],
    },
    'build_configs' : {}
})

# MARK: Notes
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  _     _                                                                │
# │ | \| |___| |_ ___ ___                                                      │
# │ | .` / _ \  _/ -_|_-<                                                      │
# │ |_|\_\___/\__\___/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
# =======================[ Emscripten ]========================-
# latest version gives this error
# scons: *** [bin\.web_zip\godot.editor.worker.js] The system cannot find the file specified
# https://forum.godotengine.org/t/error-while-building-godot-4-3-web-template/86368

# Official Requirements:
# godotengine - 4.0+     | Emscripten 1.39.9
# godotengine - 4.2+     | Emscripten 3.1.39
# godotengine - master   | Emscripten 3.1.62

# But in the github action runner, it's 3.1.64
# And all of the issues related show 3.1.64

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

# MARK: CMake Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ __  __      _         ___         _      _                           │
# │  / __|  \/  |__ _| |_____  / __| __ _ _(_)_ __| |_                         │
# │ | (__| |\/| / _` | / / -_) \__ \/ _| '_| | '_ \  _|                        │
# │  \___|_|  |_\__,_|_\_\___| |___/\__|_| |_| .__/\__|                        │
# │                                          |_|                               │
# ╰────────────────────────────────────────────────────────────────────────────╯
def cmake_script( config:SimpleNamespace, console:rich.console.Console ):
    import os
    from pathlib import Path

    from share.Timer import Timer
    from share.format import h4
    from share.actions import git_checkout, cmake_configure, cmake_build

    def want( action:str ) -> bool:
        return action in config['verbs'] and action in config['actions']

    stats:dict = dict()

    timer = Timer()

    # use the toolchain cmake and merge/overwrite with the build cmake
    if 'cmake' in toolchain:
        cmake = toolchain['cmake']
        for key,val in config['cmake'].items():
            if isinstance(val,list):
                cmake[key] = cmake.get(key,[]) + val
            if isinstance(val,str):
                cmake[key] = val
    else:
        cmake = config['cmake']

    config['cmake'] = cmake

    import json
    print( json.dumps( config['cmake'], indent=2 ) )


    #[=================================[ Fetch ]=================================]
    if want('source'):
        console.set_window_title('Source - {name}')
        stats['source'] = timer.time_function( config, func=git_checkout )

    #[===============================[ Configure ]===============================]
    if want('configure'):
        cmake['fresh'] = True if want('fresh') else False

        if 'godotcpp_profile' in config:
            profile_path = Path(config['godotcpp_profile'])
            if not profile_path.is_absolute():
                profile_path = config['source_dir'] / profile_path
            h4(f'using build profile: "{profile_path}"')
            cmake['config_vars'].append(f'-DGODOT_BUILD_PROFILE="{os.fspath(profile_path)}"')

        console.set_window_title('Prepare - {name}')
        stats['prepare'] = timer.time_function( config, func=cmake_configure )

    #[=================================[ Build ]=================================]
    if want('build') and timer.ok():
        console.set_window_title('Build - {name}')
        stats['build'] = timer.time_function( config, func=cmake_build )

    #[==================================[ Test ]==================================]
    # if want('test') and timer.ok():
    #     console.set_window_title('Test - {name}')
    #     stats['test'] = timer.time_function( config, func=godotcpp_test )


    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(highlight=True, min_width=80)

    table.add_column("Section",no_wrap=True)
    table.add_column("Status")
    table.add_column("Duration")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}', style='red')

    print( table )
    if not timer.ok():
        exit(1)

def process_script( script:str ) -> str:
    print( 'processing script' )
    return script.replace('%replaceme%', inspect.getsource(git_checkout))

# MARK: Windows
# ╒════════════════════════════════════════════════════════════════════════════╕
# │            ██     ██ ██ ███    ██ ██████   ██████  ██     ██ ███████       │
# │            ██     ██ ██ ████   ██ ██   ██ ██    ██ ██     ██ ██            │
# │            ██  █  ██ ██ ██ ██  ██ ██   ██ ██    ██ ██  █  ██ ███████       │
# │            ██ ███ ██ ██ ██  ██ ██ ██   ██ ██    ██ ██ ███ ██      ██       │
# │             ███ ███  ██ ██   ████ ██████   ██████   ███ ███  ███████       │
# ╘════════════════════════════════════════════════════════════════════════════╛

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      ___         _                                                      │
# │ \ \    / (_)_ _  __| |_____ __ _____                                       │
# │  \ \/\/ /| | ' \/ _` / _ \ V  V (_-<                                       │
# │   \_/\_/ |_|_||_\__,_\___/\_/\_//__/                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯

variations = ['default']
generators = ['msvc', 'ninja', 'ninja-multi']
msbuild_extras = ['--', '/nologo', '/v:m', "/clp:'ShowCommandLine;ForceNoAlign'"]

for toolchain in toolchains.values():
    cfg = SimpleNamespace(**{
        'name' : f'w64.{toolchain.name}',
        'toolchain':copy.deepcopy(toolchain),
        'script': cmake_script,
        'verbs':['source','configure', 'fresh', 'build', 'test'],
        'cmake':{
            'build_dir':'build-cmake',
            'godot_build_profile':'test/build_profile.json',
            'config_vars':[],
            'build_vars':[],
            'targets':['orchestrator'],
        },
        # Variables for testing
        'godot_tr':'C:/build/godot/w64.msvc/bin/godot.windows.template_release.x86_64.console.exe',
        'godot_td':'C:/build/godot/w64.msvc/bin/godot.windows.template_debug.x86_64.console.exe',
        'godot_e':'C:/build/godot/w64.msvc/bin/godot.windows.editor.x86_64.console.exe',
        # Variables to clean the logs
        # 'clean_log':clean_log
    })

    # Toolchain
    match toolchain.name:
        case 'msvc':
            # MSVC
            alt = copy.deepcopy( cfg )
            alt.cmake['config_vars'] = ['-G"Visual Studio 17 2022"']
            alt.cmake['build_vars'].append('--config Release')
            alt.cmake['tool_vars'] = msbuild_extras
            project_config.build_configs[alt.name] = alt

            # Ninja
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja'
            alt.cmake['config_vars'] = [
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            project_config.build_configs[alt.name] = alt

            # Ninja Multi-Config
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja-multi'
            alt.cmake['config_vars'] = [
                '-G"Ninja Multi-Config"',
                '-DGODOT_ENABLE_TESTING=ON']
            alt.cmake['build_vars'].append('--config Release')
            project_config.build_configs[alt.name] = alt
            continue

        case 'llvm':
            cfg.cmake['toolchain_file'] = "toolchains/w64-llvm.cmake"
            # Ninja
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja'
            alt.cmake['config_vars'] = [
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            project_config.build_configs[alt.name] = alt

            # Ninja Multi-Config
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja-multi'
            alt.cmake['config_vars'] = [
                '-G"Ninja Multi-Config"',
                '-DGODOT_ENABLE_TESTING=ON']
            alt.cmake['build_vars'].append('--config Release')
            project_config.build_configs[alt.name] = alt
            continue

        case 'llvm-mingw':
            cfg.cmake['config_vars'] = [
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'msys2-ucrt64':
            # Ninja
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja'
            alt.cmake['config_vars'] = [
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            project_config.build_configs[alt.name] = alt

            # Ninja Multi-Config
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja-multi'
            alt.cmake['config_vars'] += ['-G"Ninja Multi-Config"']
            alt.cmake['build_vars'].append('--config Release')
            project_config.build_configs[alt.name] = alt
            continue

        case 'msys2-clang64':
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja'
            alt.cmake['config_vars'] += ['-G"Ninja"', '-DCMAKE_BUILD_TYPE=Release']
            project_config.build_configs[alt.name] = alt

            # Ninja Multi-Config
            alt = copy.deepcopy( cfg )
            alt.name += '.ninja-multi'
            alt.cmake['config_vars'] += ['-G"Ninja Multi-Config"' ]
            alt.cmake['build_vars'].append('--config Release')
            project_config.build_configs[alt.name] = alt
            continue

        case 'mingw64':
            # cfg.gitHash = '537b787f2dc73d097a0cba7963f2e24b82ce6076'
            cfg.cmake['config_vars'] = [
                '-G"MinGW Makefiles"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']

        case _:
            continue
    project_config.build_configs[cfg.name] = cfg


# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯
def add_android():
    cfg = SimpleNamespace(**{
        'name' : f'w64.{toolchain.name}',
        'toolchain':copy.deepcopy(toolchain),
        'script': cmake_script,
        'verbs':['source','configure', 'prepare', 'build'],
        'cmake':{
            'build_dir':'build-cmake',
            'godot_build_profile':'test/build_profile.json',
            'config_vars':[],
            'build_vars':[],
            'targets':['orchestrator'],
        },
    })

    cfg.cmake['config_vars'] =[
        "-DANDROID_PLATFORM=latest",
        "-DANDROID_ABI=x86_64"]
    cfg.cmake['toolchain_file'] = 'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake'

    alt = copy.deepcopy( cfg )
    alt.name += '.ninja'
    alt.cmake['config_vars'] += ['-G"Ninja"', '-DCMAKE_BUILD_TYPE=Release']
    alt.cmake['build_vars'].append('--config Release')
    project_config.build_configs[alt.name] = alt

    alt = copy.deepcopy( cfg )
    alt.name += '.ninja-multi'
    alt.cmake['config_vars'] += ['-G"Ninja Multi-Config"']
    alt.cmake['build_vars'].append('--config Release')
    project_config.build_configs[alt.name] = alt

add_android()

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      __   _                                                             │
# │ \ \    / /__| |__                                                          │
# │  \ \/\/ / -_) '_ \                                                         │
# │   \_/\_/\___|_.__/                                                         │
# ╰────────────────────────────────────────────────────────────────────────────╯

def add_web():
    cfg = SimpleNamespace(**{
        'name' : f'w64.{toolchain.name}',
        'toolchain':copy.deepcopy(toolchain),
        'script': cmake_script,
        'verbs':['source', 'configure', 'fresh', 'build'],
        'cmake':{
            'build_dir':'build-cmake',
            'godot_build_profile':'test/build_profile.json',
            'config_vars':[],
            'build_vars':[],
            'targets':['orchestrator'],
        },
        # Variables to clean the logs
        # 'clean_log':clean_log
    })

    cfg.cmake['toolchain_file'] = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'

    project_config.build_configs[cfg.name] = cfg

add_web()

def filter_config( config:SimpleNamespace )-> list:
    match config.toolchain.name:
        case 'emsdk':
            config.cmake['generator'] = 'Ninja'
            config.cmake['config_varas'] = '-DCMAKE_BUILD_TYPE=Release'

    return[config]

def generate_configs():
    build_base = SimpleNamespace(**{
        'name' : '',
        'script': cmake_script,
        'verbs':['source','configure', 'fresh', 'build', 'test'],
        'godotcpp_profile':'extern/godot-cpp-profile.json',
        'cmake':{
            'build_dir':'build-cmake',
            'config_vars':[],
            'build_vars':[],
            'targets':['orchestrator'],
        },
        # Variables for testing
        'godot_tr':'C:/build/godot/w64.msvc/bin/godot.windows.template_release.x86_64.console.exe',
        'godot_td':'C:/build/godot/w64.msvc/bin/godot.windows.template_debug.x86_64.console.exe',
        'godot_e':'C:/build/godot/w64.msvc/bin/godot.windows.editor.x86_64.console.exe',
        # Variables to clean the logs
        # 'clean_log':clean_log
    })

    configs = expand_host_env( build_base )
    for cfg in configs:
        cfg.name = f'{cfg.host}.{cfg.toolchain.name}.{cfg.arch}'

    configs = expand( configs, filter_config )

    for config in configs:
        project_config.build_configs[config.name] = config

project_config.build_configs = {}
generate_configs()
