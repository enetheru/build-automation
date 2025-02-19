import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import rich

from share.expand_config import expand_host_env, expand
from share.run import stream_command
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

# Platform Mapping from python 3.13 to what godot-cpp scons expects
godot_platforms = {
    'android':'android',
    'ios':'ios',
    'linux':'linux',
    'emscripten':'web',
    'darwin':'macos',
    'win32':'windows'
    # aix, cygwin, wasi, are unsupported
}

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
def scons_script( config:dict, toolchain:dict, console:rich.console.Console ):
    from share.Timer import Timer, TaskStatus
    from actions import godotcpp_test
    from share.actions_git import git_checkout
    from share.actions_scons import scons_build

    stats:dict = {}
    ok = True

    def want( action:str ) -> bool:
        return (ok
                and action in config['verbs']
                and action in config['actions'])

    name = config['name']

    # Use a project wide build cache
    scons:dict = config['scons']
    scons_cache = Path(config['project_dir']) / 'scons_cache'
    scons['build_vars'].append(f'cache_path={scons_cache.as_posix()}')
    scons['build_vars'].append('cache_limit=16')

    #[=================================[ Fetch ]=================================]
    if want('source'):
        console.set_window_title(f'Source - {name}')
        with Timer(name='source') as timer:
            git_checkout( config )
        stats['source'] = timer.get_dict()
        ok = timer.ok()

    # Check whether build path is viable.
    if "build_dir" in scons.keys():
        build_dir = Path(scons["build_dir"])
        if not build_dir.is_absolute():
            build_dir = Path(config["source_dir"]) / build_dir
    else:
        build_dir = Path(config["source_dir"])

    try:
        os.chdir(build_dir)
    except FileNotFoundError as e:
        print( f'Missing Folder {build_dir}' )
        ok = False

    # requires SConstruct file existing in the current directory.
    if not (build_dir / "SConstruct").exists():
        print(f"[red]Missing SConstruct in {build_dir}")
        ok = False

    #[=================================[ Clean ]=================================]
    if want('clean'):
        console.set_window_title(f'Clean - {name}')
        print(figlet("SCons Clean", {"font": "small"}))

        with Timer(name='clean', push=False) as timer:
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
        ok = timer.ok()

    #[=================================[ Build ]=================================]
    if want('build'):
        console.set_window_title(f'Build - {name}')
        with Timer(name='build') as timer:
            scons_build( config )
        stats['build'] = timer.get_dict()
        ok = timer.ok()

    #[==================================[ Test ]==================================]
    if want('test'):
        console.set_window_title(f'Test - {name}')
        with Timer(name='test') as timer:
            godotcpp_test( config )

        stats['test'] = timer.get_dict()
        ok = timer.ok()

    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(title="Stats", highlight=True, min_width=80)

    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Duration", style="green")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}')

    print( table )
    if not ok: exit(1)

scons_script.verbs = ['source', 'clean', 'build', 'test']

# MARK: CMake Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ __  __      _         ___         _      _                           │
# │  / __|  \/  |__ _| |_____  / __| __ _ _(_)_ __| |_                         │
# │ | (__| |\/| / _` | / / -_) \__ \/ _| '_| | '_ \  _|                        │
# │  \___|_|  |_\__,_|_\_\___| |___/\__|_| |_| .__/\__|                        │
# │                                          |_|                               │
# ╰────────────────────────────────────────────────────────────────────────────╯
def cmake_script( config:dict, toolchain:dict, console:rich.console.Console ):
    import os
    import copy
    from pathlib import Path

    from share.Timer import Timer
    from share.format import h4
    from share.actions_git import git_checkout

    from actions import godotcpp_test

    ok = True

    def want( action:str ) -> bool:
        return (ok
                and action in config['verbs']
                and action in config['actions'])

    stats:dict = dict()
    cmake = config['cmake']

    #[=================================[ Fetch ]=================================]
    if want('source'):
        console.set_window_title('Source - {name}')
        with Timer(name='source') as timer:
            git_checkout( config )
        stats['source'] = timer.get_dict()
        ok = timer.ok()

    #[===============================[ Configure ]===============================]
    if want('configure'):
        print(figlet("CMake Configure", {"font": "small"}))
        console.set_window_title('Configure - {name}')

        source_dir = Path(config["source_dir"])

        # requires CMakeLists.txt file existing in the current directory.
        if not (source_dir / "CMakeLists.txt").exists():
            print( f"Missing CMakeLists.txt in {source_dir}" )
            ok = timer.ok()

        try:
            os.chdir(source_dir)
        except FileNotFoundError as e:
            print( f'Missing Folder {source_dir}' )
            ok = timer.ok()

        # Create Build Directory
        build_dir = Path(cmake['build_dir'])
        if not build_dir.is_dir():
            h4(f"Creating {build_dir}")
            os.mkdir(build_dir)

        config_opts = [
            "--fresh" if want('fresh') else None,
            "--log-level=VERBOSE" if not config["quiet"] else None,
            f'-B "{build_dir}"',
        ]

        if 'cmake' in toolchain:
            tc = toolchain['cmake']
            if 'toolchain' in tc:
                toolchain_file = config["root_dir"] / toolchain['cmake']['toolchain']
                config_opts.append( f'--toolchain "{os.fspath(toolchain_file)}"' )
            for var in tc.get('config_vars', []):
                config_opts.append(var)

        if 'generator' in cmake:
            config_opts.append( f'-G "{cmake['generator']}"' )

        if "config_vars" in cmake:
            config_opts += cmake["config_vars"]

        if 'godot_build_profile' in cmake:
            config_opts.append( f'-DGODOT_BUILD_PROFILE="{os.fspath(cmake['godot_build_profile'])}"' )

        with Timer(name='configure') as timer:
            stream_command(f'cmake {' '.join(filter(None, config_opts))}', dry=config['dry'])
            print('')

        print(align(" CMake Configure Completed ", line=fill("-")))
        stats['configure'] = timer.get_dict()
        ok = timer.ok()


    #[=================================[ Build ]=================================]
    if want('build'):
        print(figlet("CMake Build", {"font": "small"}))
        console.set_window_title('Build - {name}')

        build_dir = Path(cmake["build_dir"])
        if not build_dir.is_absolute():
            build_dir = Path(config['source_dir']) / build_dir

        # requires CMakeLists.txt file existing in the current directory.
        if not (build_dir / "CMakeCache.txt").exists():
            print(f"Missing CMakeCache.txt in {build_dir}")
            ok = timer.ok()

        try:
            os.chdir( build_dir )
        except FileNotFoundError as e:
            print( f'Missing Folder {build_dir}' )
            ok = timer.ok()

        build_opts = [
            f'--build .',
            "--verbose" if not config["quiet"] else None,
            f"-j {config['jobs']}",
        ]
        build_opts += cmake.get("build_vars", [])

        with Timer(name='build') as timer:
            for target in cmake["targets"]:
                print(align(f" Building target: {target} ", line=fill("~ ")))
                target_opts = copy.copy(build_opts)
                target_opts.append(f" --target {target}")

                if "tool_vars" in cmake:
                    target_opts.append('--')
                    target_opts += cmake["tool_vars"]

                stream_command(f'cmake {' '.join(filter(None, target_opts))}', dry=config["dry"])
                print('')

        print(align(" CMake Build Completed ", line=fill("-")))
        print('')
        stats['build'] = timer.get_dict()
        ok = timer.ok()

    #[==================================[ Test ]==================================]
    if want('test'):
        console.set_window_title('Test - {name}')
        with Timer(name='test') as timer:
            godotcpp_test( config )
        stats['test'] = timer.get_dict()
        ok = timer.ok()


    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(highlight=True, min_width=80)

    table.add_column("Section",no_wrap=True)
    table.add_column("Status")
    table.add_column("Duration")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}', style='red')

    print( table )
    if not ok: exit(1)

cmake_script.verbs = ['configure','fresh', 'build', 'test']

# MARK: Configure
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ██████  ███    ██ ███████ ██  ██████  ██    ██ ██████  ███████    │
# │ ██      ██    ██ ████   ██ ██      ██ ██       ██    ██ ██   ██ ██         │
# │ ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ██    ██ ██████  █████      │
# │ ██      ██    ██ ██  ██ ██ ██      ██ ██    ██ ██    ██ ██   ██ ██         │
# │  ██████  ██████  ██   ████ ██      ██  ██████   ██████  ██   ██ ███████    │
# ╰────────────────────────────────────────────────────────────────────────────╯

def configure_scons( cfg:SimpleNamespace ) -> bool:
    setattr(cfg, 'script', scons_script)
    cfg.verbs += scons_script.verbs
    setattr(cfg, 'scons', {
        'build_dir':'test',
        "build_vars":["compiledb=yes", 'build_profile=build_profile.json'],
        "targets": ["template_release", "template_debug", "editor"],
    } )

    cfg.scons["build_vars"].append(f'platform={godot_platforms[cfg.platform]}')

    match cfg.toolchain.name:
        case 'android':
            android_abi = {
                'armeabi-v7a': 'arm32',
                'arm64-v8a':'arm64',
                'x86':'x86_32',
                'x86_64':'x86_64'
            }
            cfg.scons["build_vars"].append(f'arch={android_abi[cfg.arch]}')

        case 'emsdk':
            pass

        case "msvc" | 'appleclang':
            cfg.scons['build_vars'].append(f'arch={cfg.arch}')

        case "llvm":
            if cfg.arch != 'x86_64': return False
            cfg.scons["build_vars"].append("use_llvm=yes")
            cfg.scons['build_vars'].append(f'arch={cfg.arch}')

        case "llvm-mingw":
            archmap = {
                'armv7': 'arm32',
                'aarch64':'arm64',
                'i686':'x86_32',
                'x86_64':'x86_64'
            }
            cfg.scons["build_vars"].append(f'arch={archmap[cfg.arch]}')
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")
            cfg.scons["build_vars"].append(f"mingw_prefix={cfg.toolchain.sysroot}")

        case "msys2-clang64":
            cfg.scons['build_vars'].append(f'arch={cfg.arch}')
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            cfg.scons['build_vars'].append(f'arch={cfg.arch}')
            cfg.scons["build_vars"].append("use_mingw=yes")

        case _:
            return False

    return True

def configure_cmake( cfg:SimpleNamespace ) -> bool:
    setattr(cfg, 'script', cmake_script)
    cfg.verbs += cmake_script.verbs
    setattr(cfg, 'cmake', {
        'build_dir':'build-cmake',
        'godot_build_profile':'test/build_profile.json',
        'config_vars':['-DGODOT_ENABLE_TESTING=ON', '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache'],
        'build_vars':[],
        'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
    } )
    # TODO make ccache soemthing that is detected before use.

    if cfg.toolchain.name == 'android':
        cfg.cmake['config_vars'] += ['-DANDROID_PLATFORM=latest', f'-DANDROID_ABI={cfg.arch}' ]

    if cfg.toolchain.name == 'llvm-mingw':
        cfg.cmake['config_vars'] += [f'-DLLVM_MINGW_PROCESSOR={cfg.arch}']

    return True

build_tools = {
    'scons': configure_scons,
    'cmake': configure_cmake
}

# MARK: Variant Config
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _          _      ___           __ _                        │
# │ \ \ / /_ _ _ _(_)__ _ _ _| |_   / __|___ _ _  / _(_)__ _                   │
# │  \ V / _` | '_| / _` | ' \  _| | (__/ _ \ ' \|  _| / _` |                  │
# │   \_/\__,_|_| |_\__,_|_||_\__|  \___\___/_||_|_| |_\__, |                  │
# │                                                    |___/                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

def variant_default( cfg:SimpleNamespace ) -> bool:
    """

    :type cfg: object
    """
    return True

def variant_skip( cfg:SimpleNamespace ) -> bool:
    """

    :type cfg: object
    """
    return False

# MARK: double
def variant_double( cfg:SimpleNamespace ) -> bool:
    setattr( cfg, 'variant', 'double' )
    if cfg.arch not in ['x86_64', 'arm64']: return False
    match cfg.buildtool:
        case 'scons':
            cfg.scons["build_vars"].append("precision=double")
        case 'cmake':
            cfg.cmake["config_vars"].append("-DGODOT_PRECISION=double")
    return True

variations = {
    'default':variant_default,
    'double':variant_double,
    'nothreads':variant_skip,
    'hotreload':variant_skip,
    'exceptions':variant_skip,
    'staticcpp':variant_skip,
    'debugcrt':variant_skip,
}

# MARK: ConfigureFilter
def configure_and_filter( cfg:SimpleNamespace ) -> list:
    cfg.name = f'{cfg.host}'

    match cfg.toolchain.name:
        case 'android' | 'emsdk':
            pass
        case _:
            cfg.name += f'.{cfg.toolchain.name}'

    cfg.name += f'.{godot_platforms[cfg.platform]}'

    match cfg.arch:
        case 'wasm32':
            pass # skip for emscripten
        # Android arches
        case 'armeabi-v7a' | 'armv7':
            cfg.name += f'.arm32'
        case 'arm64-v8a' | 'aarch64':
            cfg.name += f'.arm64'
        case 'x86' | 'i686':
            cfg.name += f'.x86_32'
        case _:
            cfg.name += f'.{cfg.arch}'

    cfg.name += f'.{cfg.variant}'
    cfg.name += f'.{cfg.buildtool}'

    return [cfg]

# MARK: Expansion
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ ███████ ██   ██ ██████   █████  ███    ██ ███████ ██  ██████  ███    ██    │
# │ ██       ██ ██  ██   ██ ██   ██ ████   ██ ██      ██ ██    ██ ████   ██    │
# │ █████     ███   ██████  ███████ ██ ██  ██ ███████ ██ ██    ██ ██ ██  ██    │
# │ ██       ██ ██  ██      ██   ██ ██  ██ ██      ██ ██ ██    ██ ██  ██ ██    │
# │ ███████ ██   ██ ██      ██   ██ ██   ████ ███████ ██  ██████  ██   ████    │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Variant
def expand_variant( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant, configure_func in variations.items():
        cfg = copy.deepcopy(config)

        setattr( cfg, 'variant', variant )
        if not configure_func( cfg ): continue


        # TODO If I want to test against multiple binaries then I need to specify multiple.
        '{root}/godot/{host}.{toolchain}.{platform}.{arch}.{variant}/bin/godot.{platform}.{target}[.double].{arch}[.llvm].console.exe'
        # For now I will just focus on the current OS
        setattr(cfg, 'godot_e', Path('C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.editor.x86_64.console'))
        setattr(cfg, 'godot_tr', Path('C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.template_release.x86_64.console'))
        setattr(cfg, 'godot_td', Path('C:/build/godot/w64.msvc.windows.x86_64/bin/godot.windows.template_debug.x86_64.console'))

        configs_out.append( cfg )
    return configs_out

# MARK: Platform
def expand_platforms( config:SimpleNamespace ) -> list:
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

        match platform:
            case "windows":
                pass

            case "android":
                if cfg.toolchain.name != 'android': continue
                cfg.name = f"{config.host}.{platform}.{cfg.arch}"

            case "web":
                if cfg.toolchain.name != 'emsdk': continue
                cfg.name = f"{config.host}.{platform}"

            case _:
                continue
        configs_out += expand_variant( cfg )
    return configs_out

# MARK: Generators
def expand_generators( config:SimpleNamespace ) -> list:
    configs_out:list = []

    for generator in  ['msvc', 'ninja', 'ninja-multi', 'mingw']:
        cfg = copy.deepcopy(config)

        cfg.buildtool += f'.{generator}'

        match generator:
            case 'msvc':
                _A = {'x86_32':'Win32', 'x86_64':'x64', 'arm64':'ARM64'}
                if cfg.toolchain.name != generator: continue
                cfg.cmake['generator'] = 'Visual Studio 17 2022'
                cfg.cmake['config_vars'].append( f'-A {_A[cfg.arch]}')
                cfg.cmake['build_vars'].append('--config Release')
                cfg.cmake['tool_vars'] = ['-nologo', '-verbosity:normal', "-consoleLoggerParameters:'ShowCommandLine;ForceNoAlign'"]

            case 'ninja':
                cfg.cmake['generator'] = 'Ninja'
                cfg.cmake['config_vars'].append('-DCMAKE_BUILD_TYPE=Release')

            case 'ninja-multi':
                cfg.cmake['generator'] = 'Ninja Multi-Config'
                cfg.cmake['build_vars'].append('--config Release')

            case 'mingw':
                if cfg.toolchain.name != 'mingw64': continue
                cfg.cmake['generator'] = 'MinGW Makefiles'
                cfg.cmake['config_vars'].append('-DCMAKE_BUILD_TYPE=Release')
            case _:
                continue

        configs_out.append( cfg )
    return configs_out

# MARK: BuildTools
def expand_buildtools( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for buildtool, configure_func in build_tools.items():
        cfg = copy.deepcopy(config)

        setattr(cfg, 'buildtool', buildtool )
        if not configure_func( cfg ):
            continue

        match buildtool:
            case 'scons':
                configs_out.append( cfg )

            case 'cmake':
                configs_out += expand_generators( cfg )

    return configs_out

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯
def generate_configs():
    config_base = SimpleNamespace(**{
        'name':'',
        'verbs':['source'],
    })

    # Host environment toolchain and build tools
    configs = expand_host_env( config_base )
    configs = expand( configs, expand_buildtools )

    # target and variants
    configs = expand( configs, expand_variant )

    # setup all the things.
    configs = expand( configs, configure_and_filter )

    for cfg in sorted( configs, key=lambda value: value.name ):
        project_config.build_configs[cfg.name] = cfg

generate_configs()