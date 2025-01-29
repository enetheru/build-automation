import copy
import inspect
import itertools
from pathlib import Path
from types import SimpleNamespace

import rich

from share.Timer import TaskStatus
from share.actions import git_checkout
from share.run import stream_command
from share.toolchains import toolchains
from share.format import *

project_config = SimpleNamespace(**{
    'gitUrl'  : "https://github.com/enetheru/godot-cpp.git/",
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

def scons_script( config:SimpleNamespace, console:rich.console.Console ):
    from share.Timer import Timer
    from share.actions import git_checkout, scons_build
    from actions import godotcpp_test
    from share.Timer import TaskStatus


    name = config['name']
    actions = config['actions']
    scons: dict = config["scons"]
    jobs = config["jobs"]

    stats:dict = dict()
    timer = Timer()

    #[=================================[ Fetch ]=================================]
    if 'source' in config['verbs'] and actions['source']:
        console.set_window_title(f'Source - {name}')
        stats['source'] = timer.time_function( config, func=git_checkout )


    # Check whether build path is viable.
    if "build_dir" in scons.keys():
        build_dir = Path(scons["build_dir"])
        if not build_dir.is_absolute():
            build_dir = Path(config["source_dir"]) / build_dir
    else:
        build_dir = Path(config["source_dir"])

    os.chdir(build_dir)

    # requires SConstruct file existing in the current directory.
    if not (build_dir / "SConstruct").exists():
        print(f"[red]Missing SConstruct in {build_dir}")
        raise "Missing SConstruct"

    #[=================================[ Clean ]=================================]
    if 'clean' in config['verbs'] and actions['clean']:
        console.set_window_title(f'Clean - {name}')
        print(figlet("SCons Clean", {"font": "small"}))

        with timer:
            try:
                proc = stream_command( "scons --clean" , dry=config['dry'])
                # Change status depending on the truthiness of returnvalue
                # where False is Success and True is Failure.
                timer.status = TaskStatus.FAILED if proc.returncode else TaskStatus.COMPLETED
            except subprocess.CalledProcessError as e:
                # FIXME should this be more generic and handled elsewhere?
                print( '[red]subprocess error')
                print( f'[red]{e}' )
                timer.status = TaskStatus.FAILED
            stats['clean'] = timer.get_dict()

    #[=================================[ Build ]=================================]
    if 'build' in config['verbs'] and actions['build'] and timer.ok():
        console.set_window_title(f'Build - {name}')
        stats['build'] = timer.time_function( config, func=scons_build )

    #[==================================[ Test ]==================================]
    if 'test' in config['verbs'] and actions['test'] and timer.ok():
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
    import os
    from pathlib import Path

    from share.Timer import Timer
    from share.format import h4
    from share.actions import git_checkout, cmake_configure, cmake_build

    from actions import godotcpp_test

    stats:dict = dict()
    cmake = config['cmake']
    actions = config['actions']
    timer = Timer()

    #[=================================[ Fetch ]=================================]
    if 'source' in config['verbs'] and actions['source']:
        console.set_window_title('Source - {name}')
        stats['source'] = timer.time_function( config, func=git_checkout )

    #[===============================[ Configure ]===============================]
    if 'configure' in config['verbs'] and actions['prepare']:
        if 'godot_build_profile' in cmake:
            profile_path = Path(cmake['godot_build_profile'])
            if not profile_path.is_absolute():
                profile_path = config['source_dir'] / profile_path
            h4(f'using build profile: "{profile_path}"')
            cmake['config_vars'].append(f'-DGODOT_BUILD_PROFILE="{os.fspath(profile_path)}"')

        if 'toolchain_file' in cmake:
            toolchain_path = Path(cmake['toolchain_file'])
            if not toolchain_path.is_absolute():
                toolchain_path = config['root_dir'] / toolchain_path
            h4(f'using toolchain file: "{toolchain_path}"')
            cmake['config_vars'].append(f'--toolchain "{os.fspath(toolchain_path)}"')

        console.set_window_title('Prepare - {name}')
        stats['prepare'] = timer.time_function( config, func=cmake_configure )

    #[=================================[ Build ]=================================]
    if 'build' in config['verbs'] and actions['build'] and timer.ok():
        console.set_window_title('Build - {name}')
        stats['build'] = timer.time_function( config, func=cmake_build )

    #[==================================[ Test ]==================================]
    if 'test' in config['verbs'] and actions['test'] and timer.ok():
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
    return script.replace('%replaceme%', inspect.getsource(git_checkout))

# MARK: Windows
# ╒════════════════════════════════════════════════════════════════════════════╕
# │            ██     ██ ██ ███    ██ ██████   ██████  ██     ██ ███████       │
# │            ██     ██ ██ ████   ██ ██   ██ ██    ██ ██     ██ ██            │
# │            ██  █  ██ ██ ██ ██  ██ ██   ██ ██    ██ ██  █  ██ ███████       │
# │            ██ ███ ██ ██ ██  ██ ██ ██   ██ ██    ██ ██ ███ ██      ██       │
# │             ███ ███  ██ ██   ████ ██████   ██████   ███ ███  ███████       │
# ╘════════════════════════════════════════════════════════════════════════════╛

"""
## Platforms
### Windows
#### Toolchains:
- msvc
    - archs [x86_32, x86_64, arm64]
    - using clang-cl
- llvm
- mingw-llvm
    - archs [x86_32, x86_64, arm64]
- mingw64
    - archs [x86_32, x86_64]
- clion( mingw64 )
- msys64.ucrt64
- msys64.mingw32
- msys64.mingw64
- msys64.clang32
- msys64.clang64
- msys64.clangarm64

### Android
#### Toolchains:
- android
    - arch [arm32, arm64, x86_32, x86_64]
    
### Web
#### Toolchains
- emsdk

## Variations
- Thread/noThread
- Profile/NoProfile
- Precision single/double
- Hot Re-Load ON/OFF
- Exceptions ON/OFF
"""

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      ___         _                                                      │
# │ \ \    / (_)_ _  __| |_____ __ _____                                       │
# │  \ \/\/ /| | ' \/ _` / _ \ V  V (_-<                                       │
# │   \_/\_/ |_|_||_\__,_\___/\_/\_//__/                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯

build_tool:list = ['scons','cmake']
generators = ['Visual Studio 17 2022', 'Ninja', 'Ninja Multi-Config']
msbuild_extras = ['--', '/nologo', '/v:m', "/clp:'ShowCommandLine;ForceNoAlign'"]

for bt, tc in itertools.product( build_tool, toolchains.values() ):
    build_tool:str = bt
    toolchain:SimpleNamespace = tc

    cfg = SimpleNamespace(**{
        'name' : f'w64.{build_tool}.{toolchain.name}',
        'toolchain':copy.deepcopy(toolchain),
        'verbs':['source', 'build', 'test'],
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
        # Variables for testing
        'godot_tr':'C:/build/godot/w64.msvc/bin/godot.windows.template_release.x86_64.console.exe',
        'godot_td':'C:/build/godot/w64.msvc/bin/godot.windows.template_debug.x86_64.console.exe',
        'godot_e':'C:/build/godot/w64.msvc/bin/godot.windows.editor.x86_64.console.exe',
        # Variables to clean the logs
        # 'clean_log':clean_log
    })

    match build_tool:
        case 'cmake':
            cfg.script = cmake_script
            cfg.verbs += ['configure']
            delattr( cfg, 'scons')
        case 'scons':
            cfg.script = scons_script
            cfg.verbs += ['clean']
            delattr( cfg, 'cmake')

    match build_tool, toolchain.name:
        case 'scons', 'msvc':
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
            cfg.verbs.remove('test')
            setattr(cfg, 'test', False)
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'scons', 'emsdk':
            cfg.scons['build_vars'] += ['platform=web']
            cfg.verbs.remove('test')
            setattr(cfg, 'test', False)
            project_config.build_configs[cfg.name] = cfg
            continue

        case 'cmake', 'msvc':
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
            cfg.verbs.remove('test')
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
            setattr(cfg, 'test', False)
            continue

        case 'cmake', 'emsdk':
            cfg.verbs.remove('test')
            # FIXME, investigate the rest of the emcmake pyhton script for any other options.
            cfg.cmake['config_vars'] =[
                '-G"Ninja"',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DGODOT_ENABLE_TESTING=ON']
            cfg.cmake['toolchain_file'] = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
            setattr(cfg, 'test', False)
            project_config.build_configs[cfg.name] = cfg
            continue


        case _:
            print( f'ignoring combination: {build_tool} - {toolchain.name}')
            continue

# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯



# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      __   _                                                             │
# │ \ \    / /__| |__                                                          │
# │  \ \/\/ / -_) '_ \                                                         │
# │   \_/\_/\___|_.__/                                                         │
# ╰────────────────────────────────────────────────────────────────────────────╯



# MARK: Linux
# ╒════════════════════════════════════════════════════════════════════════════╕
# │                      ██      ██ ███    ██ ██    ██ ██   ██                 │
# │                      ██      ██ ████   ██ ██    ██  ██ ██                  │
# │                      ██      ██ ██ ██  ██ ██    ██   ███                   │
# │                      ██      ██ ██  ██ ██ ██    ██  ██ ██                  │
# │                      ███████ ██ ██   ████  ██████  ██   ██                 │
# ╘════════════════════════════════════════════════════════════════════════════╛
"""
== Platforms ==
- Linux
- MacOS
- iOS
- Windows
- Android
- Web
== Toolchains ==
- OSXCross
- cctools(for iOS)
- gcc
- clang
- riscv
- mingw32
- android(clang)
- emsdk(clang)
"""
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _    _                                                                    │
# │ | |  (_)_ _ _  ___ __                                                      │
# │ | |__| | ' \ || \ \ /                                                      │
# │ |____|_|_||_\_,_/_\_\                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      __   _                                                             │
# │ \ \    / /__| |__                                                          │
# │  \ \/\/ / -_) '_ \                                                         │
# │   \_/\_/\___|_.__/                                                         │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: MacOS
# ╒════════════════════════════════════════════════════════════════════════════╕
# │                   ███    ███  █████   ██████  ██████  ███████              │
# │                   ████  ████ ██   ██ ██      ██    ██ ██                   │
# │                   ██ ████ ██ ███████ ██      ██    ██ ███████              │
# │                   ██  ██  ██ ██   ██ ██      ██    ██      ██              │
# │                   ██      ██ ██   ██  ██████  ██████  ███████              │
# ╘════════════════════════════════════════════════════════════════════════════╛
"""
== Platforms ==
- MacOS

- android
- web
== Toolchains ==
- appleclang
- android(clang)
- emsdk(clang)
"""
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __          ___  ___                                                  │
# │ |  \/  |__ _ __ / _ \/ __|                                                 │
# │ | |\/| / _` / _| (_) \__ \                                                 │
# │ |_|  |_\__,_\__|\___/|___/                                                 │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  ___  ___                                                               │
# │ (_)/ _ \/ __|                                                              │
# │ | | (_) \__ \                                                              │
# │ |_|\___/|___/                                                              │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │    _           _         _    _                                            │
# │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# ╰────────────────────────────────────────────────────────────────────────────╯

# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      __   _                                                             │
# │ \ \    / /__| |__                                                          │
# │  \ \/\/ / -_) '_ \                                                         │
# │   \_/\_/\___|_.__/                                                         │
# ╰────────────────────────────────────────────────────────────────────────────╯