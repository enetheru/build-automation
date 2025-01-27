import copy
import inspect
import itertools
from types import SimpleNamespace

import rich

from share.actions import git_fetch
from share.env_commands import toolchains

project_config = SimpleNamespace(**{
    'gitUrl'  : "https://github.com/enetheru/godot-cpp.git",
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

def func_as_script( func ) -> str:
    src=inspect.getsource( func ).splitlines()[1:]
    for n in range(len(src)):
        line = src[n]
        if line.startswith('    '):
            src[n] = line[4:]
    return '\n'.join(src)

def scons_script( config:SimpleNamespace, console:rich.console.Console ):
    from share.Timer import Timer
    from share.actions import git_fetch, scons_build
    from actions import godotcpp_test

    stats:dict = dict()
    timer = Timer()
    name = config['name']

    #[=================================[ Fetch ]=================================]
    if config['fetch']:
        console.set_window_title(f'Fetch - {name}')
        stats['fetch'] = timer.time_function( config, func=git_fetch )

    #[=================================[ Build ]=================================]
    if config['build'] and timer.ok():
        console.set_window_title(f'Build - {name}')
        stats['build'] = timer.time_function( config, func=scons_build )

    #[==================================[ Test ]==================================]
    if config['test'] and timer.ok():
        console.set_window_title(f'Test - {name}')
        stats['test'] = timer.time_function( config, func=godotcpp_test )

    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(title="Stats", highlight=True, min_width=80)

    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Duration", style="green")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}')

    print( table )
    if not timer.ok():
        exit(1)

def cmake_script( config:SimpleNamespace, console:rich.console.Console ):
    from share.Timer import Timer
    from pathlib import Path
    from share.actions import git_fetch, cmake_configure, cmake_build
    from actions import godotcpp_test
    from share.format import h4

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

    if 'toolchain_file' in cmake:
        toolchain_path = Path(cmake['toolchain_file'])
        if not toolchain_path.is_absolute():
            toolchain_path = config['root_dir'] / toolchain_path
        h4(f'using toolchain file: "{{toolchain_path}}"')
        cmake['config_vars'].append(f'--toolchain "{{os.fspath(toolchain_path)}}"')

    if config['prepare'] and timer.ok():
        console.set_window_title('Prepare - {name}')
        stats['prepare'] = timer.time_function( config, func=cmake_configure )

    #[=================================[ Build ]=================================]
    if config['build'] and timer.ok():
        console.set_window_title('Build - {name}')
        stats['build'] = timer.time_function( config, func=cmake_build )

    #[==================================[ Test ]==================================]
    if config['test'] and timer.ok():
        console.set_window_title('Test - {name}')
        stats['test'] = timer.time_function( config, func=godotcpp_test )


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
    return script.replace('%replaceme%', inspect.getsource(git_fetch))

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

build_tool = ['scons','cmake']

generators = ['Visual Studio 17 2022', 'Ninja', 'Ninja Multi-Config']

msbuild_extras = ['--', '/nologo', '/v:m', "/clp:'ShowCommandLine;ForceNoAlign'"]

for build_tool, toolchain in itertools.product( build_tool, toolchains):
    cfg = SimpleNamespace(**{
        'name' : f'w64.{build_tool}.{toolchain}',
        'shell':'pwsh',
        'build_tool':build_tool,
        'toolchain':toolchain,
        'script': None,
        'cmake':{
            'build_dir':'build-cmake',
            'godot_build_profile':'test/build_profile.json',
            'config_vars':[],
            'build_vars':[],
            'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
        },
        'scons':{
            'build_dir':'test',
            'build_vars':['build_profile=build_profile.json'],
            'targets':['template_release','template_debug','editor'],
        },
        'godot_tr':'C:/build/godot/w64.msvc/bin/godot.windows.template_release.x86_64.console.exe',
        'godot_td':'C:/build/godot/w64.msvc/bin/godot.windows.template_debug.x86_64.console.exe',
        'godot_e':'C:/build/godot/w64.msvc/bin/godot.windows.editor.x86_64.console.exe',
    })

    if toolchain.startswith('msys2'):
        cfg.shell = toolchain

    match build_tool:
        case 'cmake':
            cfg.script = cmake_script
        case 'scons':
            cfg.script = func_as_script( scons_script )

    match build_tool, toolchain:
        case 'scons', 'msvc':
            cfg.shell = 'pwsh-dev'
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons', 'llvm':
            cfg.scons['build_vars'].append('use_llvm=yes')
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons', 'llvm-mingw':
            cfg.scons['build_vars'].append('use_mingw=yes')
            cfg.scons['build_vars'].append('use_llvm=yes')
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons','msys2-ucrt64':
            cfg.gitHash = 'df2f263531d0e26fb6d60aa66de3e84165e27788'
            cfg.scons['build_vars'].append('use_mingw=yes')
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons','msys2-clang64':
            cfg.gitHash = 'df2f263531d0e26fb6d60aa66de3e84165e27788'
            cfg.scons['build_vars'] += ['use_mingw=yes', 'use_llvm=yes']
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons','mingw64':
            cfg.scons['build_vars'] += ['use_mingw=yes']
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons', 'android':
            cfg.scons['build_vars'] += ['platform=android']
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons', 'emsdk':
            cfg.scons['build_vars'] += ['platform=web']
            cfg.shell = 'emsdk'
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'cmake', 'msvc':
            cfg.shell = 'pwsh-dev'

            # MSVC
            alt = copy.deepcopy( cfg )
            alt.cmake['config_vars'] = [
                f'-G"Visual Studio 17 2022"',
                '-DGODOT_ENABLE_TESTING=ON']
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

        case 'cmake', 'llvm':
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

        case 'cmake', 'llvm-mingw':
            cfg.cmake['config_vars'] = [
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'cmake', 'msys2-ucrt64':
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

        case 'cmake', 'msys2-clang64':
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

        case 'cmake', 'mingw64':
            cfg.gitHash = '537b787f2dc73d097a0cba7963f2e24b82ce6076'
            cfg.cmake['config_vars'] = [
                '-G"MinGW Makefiles"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'cmake', 'android':
            cfg.cmake['config_vars'] =[
                '-DCMAKE_BUILD_TYPE=Release',
                "-DANDROID_PLATFORM=latest",
                "-DANDROID_ABI=x86_64",
                '-DGODOT_ENABLE_TESTING=ON']
            cfg.cmake['toolchain_file'] = 'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake'

            alt = copy.deepcopy( cfg )
            alt.name += '.ninja'
            alt.cmake['config_vars'] = ['-G"Ninja"'] + cfg.cmake['config_vars']
            alt.cmake['build_vars'].append('--config Release')
            project_config.build_configs[alt.name] = alt

            alt = copy.deepcopy( cfg )
            alt.name += '.ninja-multi'
            alt.cmake['config_vars'] = ['-G"Ninja Multi-Config"'] + cfg.cmake['config_vars']
            alt.cmake['build_vars'].append('--config Release')
            project_config.build_configs[alt.name] = alt
            continue

        case 'cmake', 'emsdk':
            # FIXME, investigate the rest of the emcmake pyhton script for any other options.
            cfg.cmake['config_vars'] =[
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            cfg.cmake['toolchain_file'] = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
            project_config.build_configs[cfg.name] = cfg
            continue


        case _:
            print( f'ignoring combination: {build_tool} - {toolchain}')
            continue

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