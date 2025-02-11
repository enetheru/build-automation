import copy
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import rich

from share.actions import git_checkout
from share.format import *
from share.expand_config import expand_host_env

project_config = SimpleNamespace(**{
    'name'      : 'godot-cpp-test',
    'gitUrl'    : "https://github.com/enetheru/godot-cpp-test.git/",
    'gitHash'   : "main",
    'build_configs' : {}
})


def base_config() -> SimpleNamespace:
    return SimpleNamespace( **{
        "name": '',
    })

variations = ['default',
    'double',
    'nothreads',
    'hotreload'
    'exceptions']

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

# MARK: Config Expansion
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _        ___                        _                   │
# │  / __|___ _ _  / _(_)__ _  | __|_ ___ __  __ _ _ _  __(_)___ _ _           │
# │ | (__/ _ \ ' \|  _| / _` | | _|\ \ / '_ \/ _` | ' \(_-< / _ \ ' \          │
# │  \___\___/_||_|_| |_\__, | |___/_\_\ .__/\__,_|_||_/__/_\___/_||_|         │
# │                     |___/          |_|                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯
def configure_variant( config:SimpleNamespace ) -> bool:
    match config.build_tool:
        case 'scons':
            pass
        case 'cmake':
            pass

            # -DGODOT_USE_STATIC_CPP=OFF '-DGODOT_DEBUG_CRT=ON'
            # config.cmake["config_vars"].append('-DGODOT_ENABLE_TESTING=ON')


    match config.variant:
        case 'default':
            pass
        case 'double':
            if config.arch not in ['x86_64', 'arm64']: return False
            match config.build_tool:
                case 'scons':
                    config.scons["build_vars"].append("precision=double")
                case 'cmake':
                    config.cmake["config_vars"].append("-DGODOT_PRECISION=double")
                    pass
        case _:
            return False
    return True

# MARK: CMake
def expand_cmake( config:SimpleNamespace ) -> list:
    config.name += ".cmake"

    setattr(config, 'script', cmake_script )
    setattr(config, 'verbs', ['source', 'configure', 'fresh', 'build', 'test'] )
    setattr(config, 'cmake', {
        'build_dir':'build-cmake',
        'godot_build_profile':'test/build_profile.json',
        'config_vars':[],
        'build_vars':[],
        'targets':['gdexample'],
    })

    configs_out:list = []
    for generator in ['msvc', 'ninja', 'ninja-multi', 'mingw']:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'gen', generator )
        if generator != cfg.toolchain.name:
            cfg.name += f".{generator}"

        match generator:
            case 'msvc':
                if cfg.toolchain.name != generator: continue
                _A = {'x86_32':'Win32', 'x86_64':'x64', 'arm64':'ARM64'}
                cfg.cmake['generator'] = 'Visual Studio 17 2022'
                cfg.cmake['config_vars'].append( f'-A {_A[cfg.arch]}')
                cfg.cmake['tool_vars'] = ['-nologo', '-verbosity:normal', "-consoleLoggerParameters:'ShowCommandLine;ForceNoAlign'"]
            case 'ninja':
                cfg.cmake['generator'] = 'Ninja'
            case 'ninja-multi':
                cfg.cmake['generator'] = 'Ninja Multi-Config'
            case 'mingw':
                if cfg.toolchain.name != 'mingw64': continue
                cfg.cmake['generator'] = 'MinGW Makefiles'
            case _:
                continue

        if not configure_variant( cfg ): continue

        configs_out.append( cfg )
    return configs_out

# MARK: Tool
def build_tools( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for tool in ['scons','cmake']:
        cfg = copy.deepcopy(config)
        setattr( cfg, 'build_tool', tool )

        match tool:
            # case 'scons':
                # configs_out += expand_scons( cfg )
            case 'cmake':
                configs_out += expand_cmake( cfg )
            case _:
                continue

    return configs_out

# MARK: Variant
def variants( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant in variations:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'variant', variant )
        if variant != 'default':
            cfg.name += f'.{variant}'

        # TODO If I want to test against multiple binaries then I need to specify multiple.
        '{root}/godot/{host}.{toolchain}.{platform}.{arch}.{variant}/bin/godot.{platform}.{target}[.double].{arch}[.llvm].console.exe'
        # For now I will just focus on the current OS
        setattr(cfg, 'godot_e', Path('C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.editor.x86_64.console'))
        setattr(cfg, 'godot_tr', Path('C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.template_release.x86_64.console'))
        setattr(cfg, 'godot_td', Path('C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.template_debug.x86_64.console'))

        configs_out.append( cfg )
    return configs_out

# MARK: Platform
def platforms( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for platform in ['android', 'ios', 'linux', 'macos', 'web', 'windows']:
        cfg = copy.deepcopy(config)

        setattr( cfg, 'platform', platform )
        cfg.name = f"{cfg.host}.{cfg.toolchain.name}.{platform}.{cfg.arch}"

        # Filter out host system capabilities
        match sys.platform:
            case 'windows':
                if platform not in ['android', 'web','windows']: continue
            case 'darwin':
                if platform not in ['android', 'ios', 'macos', 'web']: continue
            case 'linux':
                if platform not in ['android', 'linux', 'web', 'windows']: continue

        # Filter out toolchain capabilities
        match cfg.toolchain.name:
            case 'android':
                if platform != 'android': continue
            case 'emsdk':
                if platform != 'web': continue

        # rename for android and web since they only build for one system
        match platform:
            case "android":
                if cfg.toolchain.name != 'android': continue
                cfg.name = f"{config.host}.{platform}.{cfg.arch}"

            case "web":
                if cfg.toolchain.name != 'emsdk': continue
                cfg.name = f"{config.host}.{platform}"

        configs_out.append(cfg)
    return configs_out

def expand( configs:list, func ) -> list:
    configs_out:list = []
    for config in configs:
        configs_out += func( config )
    return configs_out
        
def generate_configs():
    configs:list = expand_host_env( base_config() )

    configs = expand( configs, platforms )
    configs = expand( configs, variants )
    configs = expand( configs, build_tools )


    for config in configs:
        project_config.build_configs[config.name] = config

generate_configs()
