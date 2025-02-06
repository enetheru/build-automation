import copy
import inspect
import itertools
from pathlib import Path
from types import SimpleNamespace

import rich

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

# MARK: SCons Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___  ___               ___         _      _                               │
# │ / __|/ __|___ _ _  ___ / __| __ _ _(_)_ __| |_                             │
# │ \__ \ (__/ _ \ ' \(_-< \__ \/ _| '_| | '_ \  _|                            │
# │ |___/\___\___/_||_/__/ |___/\__|_| |_| .__/\__|                            │
# │                                      |_|                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯
def scons_script( config:SimpleNamespace, console:rich.console.Console ):
    from share.Timer import Timer
    from share.actions import git_checkout, scons_build
    from actions import godotcpp_test
    from share.Timer import TaskStatus

    def want( action:str ) -> bool:
        return action in config['verbs'] and action in config['actions']

    name = config['name']
    scons: dict = config["scons"]

    stats:dict = dict()
    timer = Timer()

    #[=================================[ Fetch ]=================================]
    if want('source'):
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
    if want('clean'):
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
    if want('build') and timer.ok():
        console.set_window_title(f'Build - {name}')
        stats['build'] = timer.time_function( config, func=scons_build )

    #[==================================[ Test ]==================================]
    if want('test') and timer.ok():
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

    from actions import godotcpp_test

    def want( action:str ) -> bool:
        return action in config['verbs'] and action in config['actions']

    stats:dict = dict()
    cmake = config['cmake']
    timer = Timer()

    #[=================================[ Fetch ]=================================]
    if want('source'):
        console.set_window_title('Source - {name}')
        stats['source'] = timer.time_function( config, func=git_checkout )

    #[===============================[ Configure ]===============================]
    if want('configure'):
        if want('fresh'):
            cmake['config_vars'].append('--fresh')

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
    if want('build') and timer.ok():
        console.set_window_title('Build - {name}')
        stats['build'] = timer.time_function( config, func=cmake_build )

    #[==================================[ Test ]==================================]
    if want('test') and timer.ok():
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

build_tools:list = ['scons','cmake']
platforms = ['windows','web','android']
variations = ['default',
    'double',
    'nothreads',
    'hotreload'
    'exceptions']

generators = ['msvc', 'ninja', 'ninja-multi', 'mingw']
msbuild_extras = ['--', '/nologo', '/v:m', "/clp:'ShowCommandLine;ForceNoAlign'"]

def configure_variant( config:SimpleNamespace ) -> bool:
    match config.variant:
        case 'default':
            pass
        case 'double':
            if config.arch not in ['x86_64', 'arm64']: return False
            match config.build_tool:
                case 'scons':
                    config.scons["build_vars"].append("precision=double")
                case 'cmake':
                    config.cmake["build_vars"].append("-DGODOT_PRECISION=double")
                    pass
        case _:
            return False
    return True

def expand_cmake( config:SimpleNamespace ) -> list:
    config.name += ".cmake"

    setattr(config, 'script', cmake_script )
    setattr(config, 'verbs', ['source', 'configure', 'fresh', 'build', 'test'] )
    setattr(config, 'cmake', {
        'build_dir':'build-cmake',
        'godot_build_profile':'test/build_profile.json',
        'config_vars':['-DGODOT_ENABLE_TESTING=ON'], # -DGODOT_USE_STATIC_CPP=OFF '-DGODOT_DEBUG_CRT=ON'
        'build_vars':[],
        'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
    })

    configs_out:list = []
    for generator in generators:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'gen', generator )
        cfg.name += f".{generator}"

        match generator:
            case 'msvc':
                if cfg.toolchain.name != generator: continue
                pass
            case 'ninja':
                pass
            case 'ninja-multi':
                pass
            case 'mingw':
                if cfg.toolchain.name != 'mingw64': continue
                pass
            case _:
                print( f"unknown generator: {generator}" )
                continue

        if not configure_variant( cfg ): continue
        configs_out.append( cfg )
    return configs_out

def expand_scons( config:SimpleNamespace ) -> list:
    configs_out:list = []
    # Add base options
    cfg = copy.deepcopy(config)
    cfg.name += ".scons"
    setattr(cfg, 'script', scons_script )
    setattr(cfg, 'verbs', ['source', 'build', 'test'] )
    setattr(cfg, 'scons', {
        'build_dir':'test',
        'build_vars':['build_profile=build_profile.json'],
        'targets':['template_release','template_debug','editor'],
    })

    match cfg.toolchain.name:
        case "msvc" | 'emsdk' | 'android':
            pass

        case "llvm":
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "llvm-mingw" | "msys2-clang64":
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            cfg.scons["build_vars"].append("use_mingw=yes")

        case _:
            print( f"skipping toolchain: {cfg.name}" )
            return []

    if not configure_variant(cfg):
        return []

    return [cfg]

def expand_build_tools( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for tool in build_tools:
        cfg = copy.deepcopy(config)
        setattr( cfg, 'build_tool', tool )

        match tool:
            case 'scons':
                configs_out += expand_scons( cfg )
            case 'cmake':
                configs_out += expand_cmake( cfg )
            case _:
                print( f"unknown build_tool: {tool}" )
                continue

    return configs_out

def expand_variant( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant in variations:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'variant', variant )
        if variant != 'default':
            cfg.name += f'.{variant}'

        configs_out += expand_build_tools( cfg )
    return configs_out

def expand_platforms( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for platform in platforms:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'platform', platform )
        cfg.name = f"{cfg.host}.{cfg.toolchain.name}.{platform}.{cfg.arch}"

        if platform == 'web' and config.toolchain.name != 'emsdk': continue
        if config.toolchain.name == 'emsdk' and platform != 'web': continue

        if platform == 'android' and config.toolchain.name != 'android': continue
        if config.toolchain.name == 'android' and platform != 'android': continue

        match platform:
            case "windows":
                pass

            case "android":
                cfg.name = f"{config.host}.{platform}"

            case "web":
                cfg.name = f"{config.host}.{platform}"

            case _:
                print( f"skipping platform: {platform}" )
                continue
        configs_out += expand_variant( cfg )
    return configs_out

def expand_arch( config:SimpleNamespace ) -> list:
    configs_out:list = []

    for arch in config.toolchain.arch:
        cfg = copy.deepcopy(config)

        cfg.name += f".{arch}"
        setattr( cfg, 'arch', arch )

        configs_out += expand_platforms( cfg )
    return configs_out

def expand_toolchains( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for toolchain in toolchains.values():
        cfg = copy.deepcopy(config)

        cfg.name += f".{toolchain.name}"
        setattr(cfg, 'toolchain', toolchain )

        configs_out += expand_arch( cfg )

    return configs_out

def base_config() -> SimpleNamespace:
    import platform
    host = 'unknown'
    match platform.system():
        case 'Windows':
            host  = 'w'

    match platform.architecture()[0]:
        case '64bit':
            host += '64'

    if host == 'unknown':
        print( "Failed to match host platform")
        exit(1)

    return SimpleNamespace( **{
        "name": host,
        "host": host,
    })

def expand_configs() -> list:
    return expand_toolchains( base_config() )

def generate_configs():
    for cfg in expand_configs():
        project_config.build_configs[cfg.name] = cfg

generate_configs()
# MARK: End of generation
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __      ___         _                                                      │
# │ \ \    / (_)_ _  __| |_____ __ _____                                       │
# │  \ \/\/ /| | ' \/ _` / _ \ V  V (_-<                                       │
# │   \_/\_/ |_|_||_\__,_\___/\_/\_//__/                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯

#
#
# for build_tool, toolchain in itertools.product( build_tools, toolchains.values() ):
#     cfg = SimpleNamespace(**{
#         'name' : f'w64.{build_tool}.{toolchain.name}',
#         'toolchain':copy.deepcopy(toolchain),
#         'verbs':['source', 'build', 'test'],
#         'cmake':{
#             'build_dir':'build-cmake',
#             'godot_build_profile':'test/build_profile.json',
#             'config_vars':['-DGODOT_ENABLE_TESTING=ON'], # -DGODOT_USE_STATIC_CPP=OFF '-DGODOT_DEBUG_CRT=ON'
#             'build_vars':[],
#             'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
#         },
#         'scons':{
#             'build_dir':'test',
#             'build_vars':['build_profile=build_profile.json'],
#             'targets':['template_release','template_debug','editor'],
#         },
#         # Variables for testing
#         'godot_tr':'C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.template_release.x86_64.console.exe',
#         'godot_td':'C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.template_debug.x86_64.console.exe',
#         'godot_e':'C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.editor.x86_64.console.exe',
#         # Variables to clean the logs
#         # 'clean_log':clean_log
#     })
#
#     match build_tool:
#         case 'cmake':
#             cfg.script = cmake_script
#             cfg.verbs += ['configure', 'fresh']
#             delattr( cfg, 'scons')
#         case 'scons':
#             cfg.script = scons_script
#             cfg.verbs += ['clean']
#             delattr( cfg, 'cmake')
#
#     # Toolchain
#     match build_tool, toolchain.name:
#         case 'scons', 'msvc':
#             pass
#
#         case 'scons', 'llvm':
#             cfg.scons['build_vars'].append('use_llvm=yes')
#
#         case 'scons', 'llvm-mingw':
#             cfg.scons['build_vars'].append('use_mingw=yes')
#             cfg.scons['build_vars'].append('use_llvm=yes')
#
#         case 'scons','msys2-ucrt64' | 'msys2-clang64' | 'msys2-mingw64' | 'msys2-mingw32' | 'msys2-clang32':
#             cfg.gitHash = '5cf70a3e9ae0269e2eadb6cfe66c8313a15a6180'
#
#         case 'scons','mingw64':
#             cfg.scons['build_vars'] += ['use_mingw=yes']
#
#         case 'cmake', 'msvc':
#             # MSVC
#             alt = copy.deepcopy( cfg )
#             alt.cmake['config_vars'].append('-G"Visual Studio 17 2022"')
#             alt.cmake['build_vars'].append('--config Release')
#             alt.cmake['tool_vars'] = msbuild_extras
#             project_config.build_configs[alt.name] = alt
#
#             # Ninja
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja'
#             alt.cmake['config_vars'].append('-G"Ninja"')
#             alt.cmake['config_vars'].append('-DCMAKE_BUILD_TYPE=Release')
#             project_config.build_configs[alt.name] = alt
#
#             # Ninja Multi-Config
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja-multi'
#             alt.cmake['config_vars'].append('-G"Ninja Multi-Config"')
#             alt.cmake['build_vars'].append('--config Release')
#             project_config.build_configs[alt.name] = alt
#             continue
#
#         case 'cmake', 'llvm':
#             cfg.cmake['toolchain_file'] = "toolchains/w64-llvm.cmake"
#             # Ninja
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja'
#             alt.cmake['config_vars'] = [
#                 '-G"Ninja"',
#                 '-DCMAKE_BUILD_TYPE=Release',
#                 '-DGODOT_ENABLE_TESTING=ON']
#             project_config.build_configs[alt.name] = alt
#
#             # Ninja Multi-Config
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja-multi'
#             alt.cmake['config_vars'] = [
#                 '-G"Ninja Multi-Config"',
#                 '-DGODOT_ENABLE_TESTING=ON']
#             alt.cmake['build_vars'].append('--config Release')
#             project_config.build_configs[alt.name] = alt
#             continue
#
#         case 'cmake', 'llvm-mingw':
#             cfg.cmake['config_vars'] = [
#                 '-G"Ninja"',
#                 '-DCMAKE_BUILD_TYPE=Release',
#                 '-DGODOT_ENABLE_TESTING=ON']
#             project_config.build_configs[cfg.name] = cfg
#             continue
#
#         case 'cmake', 'msys2-ucrt64':
#             # Ninja
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja'
#             alt.cmake['config_vars'] = [
#                 '-G"Ninja"',
#                 '-DCMAKE_BUILD_TYPE=Release',
#                 '-DGODOT_ENABLE_TESTING=ON']
#             project_config.build_configs[alt.name] = alt
#
#             # Ninja Multi-Config
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja-multi'
#             alt.cmake['config_vars'] += ['-G"Ninja Multi-Config"']
#             alt.cmake['build_vars'].append('--config Release')
#             project_config.build_configs[alt.name] = alt
#             continue
#
#         case 'cmake', 'msys2-clang64':
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja'
#             alt.cmake['config_vars'] += ['-G"Ninja"', '-DCMAKE_BUILD_TYPE=Release']
#             project_config.build_configs[alt.name] = alt
#
#             # Ninja Multi-Config
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja-multi'
#             alt.cmake['config_vars'] += ['-G"Ninja Multi-Config"' ]
#             alt.cmake['build_vars'].append('--config Release')
#             project_config.build_configs[alt.name] = alt
#             continue
#
#         case 'cmake', 'mingw64':
#             cfg.gitHash = '537b787f2dc73d097a0cba7963f2e24b82ce6076'
#             cfg.cmake['config_vars'] = [
#                 '-G"MinGW Makefiles"',
#                 '-DCMAKE_BUILD_TYPE=Release',
#                 '-DGODOT_ENABLE_TESTING=ON']
#
#         case _:
#             continue
#     project_config.build_configs[cfg.name] = cfg
#
#
# # ╭────────────────────────────────────────────────────────────────────────────╮
# # │    _           _         _    _                                            │
# # │   /_\  _ _  __| |_ _ ___(_)__| |                                           │
# # │  / _ \| ' \/ _` | '_/ _ \ / _` |                                           │
# # │ /_/ \_\_||_\__,_|_| \___/_\__,_|                                           │
# # ╰────────────────────────────────────────────────────────────────────────────╯
# for bt, tc in itertools.product( build_tools, toolchains.values() ):
#     build_tool:str = bt
#     toolchain:SimpleNamespace = tc
#
#     cfg = SimpleNamespace(**{
#         'name' : f'w64.{build_tool}.{toolchain.name}',
#         'toolchain':copy.deepcopy(toolchain),
#         'verbs':['source', 'build'],
#         'cmake':{
#             'build_dir':'build-cmake',
#             'godot_build_profile':'test/build_profile.json',
#             'config_vars':['-DGODOT_ENABLE_TESTING=ON'],
#             'build_vars':[],
#             'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
#         },
#         'scons':{
#             'build_dir':'test',
#             'build_vars':['build_profile=build_profile.json'],
#             'targets':['template_release','template_debug','editor'],
#         },
#     })
#
#     match build_tool:
#         case 'cmake':
#             cfg.script = cmake_script
#             cfg.verbs += ['configure', 'prepare']
#             delattr( cfg, 'scons')
#         case 'scons':
#             cfg.script = scons_script
#             cfg.verbs += ['clean']
#             delattr( cfg, 'cmake')
#
#     match build_tool, toolchain.name:
#         case 'scons', 'android':
#             cfg.scons['build_vars'] += ['platform=android']
#
#         case 'cmake', 'android':
#             cfg.cmake['config_vars'] =[
#                 "-DANDROID_PLATFORM=latest",
#                 "-DANDROID_ABI=x86_64"]
#             cfg.cmake['toolchain_file'] = 'C:/androidsdk/ndk/23.2.8568313/build/cmake/android.toolchain.cmake'
#
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja'
#             alt.cmake['config_vars'] += ['-G"Ninja"', '-DCMAKE_BUILD_TYPE=Release']
#             alt.cmake['build_vars'].append('--config Release')
#             project_config.build_configs[alt.name] = alt
#
#             alt = copy.deepcopy( cfg )
#             alt.name += '.ninja-multi'
#             alt.cmake['config_vars'] += ['-G"Ninja Multi-Config"']
#             alt.cmake['build_vars'].append('--config Release')
#             project_config.build_configs[alt.name] = alt
#             continue
#
#         case _:
#             continue
#     project_config.build_configs[cfg.name] = cfg
#
# # ╭────────────────────────────────────────────────────────────────────────────╮
# # │ __      __   _                                                             │
# # │ \ \    / /__| |__                                                          │
# # │  \ \/\/ / -_) '_ \                                                         │
# # │   \_/\_/\___|_.__/                                                         │
# # ╰────────────────────────────────────────────────────────────────────────────╯
# for build_tool, toolchain in itertools.product( build_tools, toolchains.values() ):
#     cfg = SimpleNamespace(**{
#         'name' : f'w64.{build_tool}.{toolchain.name}',
#         'toolchain':copy.deepcopy(toolchain),
#         'verbs':['source', 'build'],
#         'cmake':{
#             'build_dir':'build-cmake',
#             'godot_build_profile':'test/build_profile.json',
#             'config_vars':['-DGODOT_ENABLE_TESTING=ON'],
#             'build_vars':[],
#             'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
#         },
#         'scons':{
#             'build_dir':'test',
#             'build_vars':['platform=web', 'build_profile=build_profile.json'],
#             'targets':['template_release','template_debug','editor'],
#         },
#         # Variables to clean the logs
#         # 'clean_log':clean_log
#     })
#
#     match build_tool:
#         case 'cmake':
#             cfg.script = cmake_script
#             cfg.verbs += ['configure']
#             delattr( cfg, 'scons')
#         case 'scons':
#             cfg.script = scons_script
#             cfg.verbs += ['clean']
#             delattr( cfg, 'cmake')
#
#     match build_tool, toolchain.name:
#         case 'scons', 'emsdk':
#             pass
#
#         case 'cmake', 'emsdk':
#             cfg.cmake['toolchain_file'] = 'C:/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake'
#
#         case _:
#             continue
#
#     project_config.build_configs[cfg.name] = cfg
#


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