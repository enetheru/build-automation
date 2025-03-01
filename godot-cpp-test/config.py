import copy
from types import SimpleNamespace

from share.expand_config import cmake_config_types
from share.script_preamble import *

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ):
    from godot.config import godot_platforms
    from godot.config import godot_arch

    from share.expand_config import expand_host_env, cmake_generators, expand_cmake, expand
    from share.snippets import source_git

    project = SimpleNamespace(**{
        'name':'godot-cpp-test',
        'gitdef':{
            'url':"https://github.com/enetheru/godot-cpp-test.git/",
            'ref':"main",
        },
        'build_configs' : {}
    })


    build_base = SimpleNamespace(**{
        'verbs':['source'],
        'script_parts':[source_git]
    })

    builds = expand_host_env( build_base, opts )
    builds = expand( builds,  expand_cmake )

    # Rename
    for build in builds:

        toolchain = build.toolchain.name
        arch = godot_arch[build.arch]
        platform = godot_platforms[build.platform]

        cmake = build.cmake
        short_gen = cmake_generators[cmake['generator']]
        short_type = cmake_config_types[cmake['config_type']]

        name_parts = [
            build.host,
            toolchain if toolchain != 'emscripten' else None,
            platform if build.platform != 'android' else None,
            arch if arch != 'wasm32' else None,
            short_gen,
            short_type
        ]
        build.name = '.'.join(filter(None,name_parts))

        srcdir_parts = [
            build.host,
            toolchain,
            short_gen if short_gen != build.toolchain.name else None
        ]
        build.source_dir = '.'.join(filter(None, srcdir_parts))

    project.build_configs = {v.name: v for v in builds }
    return { project.name: project }

variations = ['default',
    'double',
    'nothreads',
    'hotreload'
    'exceptions']

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
def cmake_script():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    project:dict = {}
    build:dict = {}
    # start_script

    from share.actions_git import git_checkout
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
            h(f'using build profile: "{profile_path}"')
            cmake['config_vars'].append(f'-DGODOT_BUILD_PROFILE="{os.fspath(profile_path)}"')

        if 'toolchain_file' in cmake:
            toolchain_path = Path(cmake['toolchain_file'])
            if not toolchain_path.is_absolute():
                toolchain_path = config['root_dir'] / toolchain_path
            h(f'using toolchain file: "{toolchain_path}"')
            cmake['config_vars'].append(f'--toolchain "{os.fspath(toolchain_path)}"')

        console.set_window_title('Prepare - {name}')
        # FIXME stats['prepare'] = timer.time_function( config, func=cmake_configure )

    #[=================================[ Build ]=================================]
    if want('build') and timer.ok():
        console.set_window_title('Build - {name}')
        # FIXME stats['build'] = timer.time_function( config, func=cmake_build )

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
def expand_cmake2( config:SimpleNamespace ) -> list:
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
        

