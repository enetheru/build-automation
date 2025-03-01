import copy
from subprocess import CompletedProcess
from types import SimpleNamespace
from typing import Any

from share.expand_config import expand_host_env, expand
from share.script_preamble import *

project_base:dict[str,Any] = {
    'name':'godot-cpp',
    'gitdef':{
        'url':"https://github.com/enetheru/godot-cpp.git/",
        'ref':'master'
    },
}

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

godot_arch = {
    'armv32': 'arm32',
    'armv7': 'arm32',
    'armeabi-v7a': 'arm32',
    'arm64':'arm64',
    'arm64-v8a':'arm64',
    'aarch64':'arm64',
    'x86_32':'x86_32',
    'i686':'x86_32',
    'x86':'x86_32',
    'x86_64':'x86_64',
    'wasm32':'wasm32'
}

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def test_script():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    #[==================================[ Test ]==================================]
    from rich.panel import Panel
    from subprocess import SubprocessError
    from share.format import p
    from json import dumps

    def collect_godots() -> dict:
        godot_arches = ['x86_64', 'x86_32', 'arm64', 'arm32', 'wasm32']

        # find all builds in the godot build folder to test against.
        godot_path = Path( opts['path'] / 'godot' )
        godot_sets = {}
        for child in godot_path.glob(f'{build['host']}*/'):
            # Get all the executables in the folder
            files = [f.name for f in (child / 'bin').glob('*.exe')]
            files = [*filter( lambda f: 'godot' in f , files )]
            files = [*filter( lambda f: 'console' not in f , files )]

            if not len(files):
                continue

            set_folder = child.name

            for f in files:
                # Chop up the godot.windows.target... into pieces and process them
                file_path = Path(child / 'bin' / f)
                parts = f.split('.')[1:-1]
                parts = [p for p in parts if p != 'llvm']

                set_platform = parts[0]
                set_target = parts[1]
                parts = parts[2:]

                set_arch = 'unknown'
                set_variant = 'default'
                while parts:
                    if parts[0] in godot_arches: set_arch = parts[0]
                    else: set_variant = parts[0]
                    parts = parts[1:]

                # create the key
                set_name = f'{set_folder}.{set_platform}.{set_arch}.{set_variant}'

                godot_sets.setdefault( set_name, {
                    'name': set_name,
                    'platform': set_platform,
                    'arch': set_arch,
                    'variant':set_variant
                })

                # update the dict
                godot_sets[set_name] |= {
                    set_target: file_path.as_posix()
                }

        godot_sets = {k:v for k,v in godot_sets.items() if v['variant'] == build['variant']}

        #FIXME this is broken because python arches dont match godot arches, so we need to translate them.
        # godot_sets = {k:v for k,v in godot_sets.items() if v['platform'] == build['platform'] and v['arch'] == build['arch']}

        #FIXME, detect current platform and arch and use them to filter
        return {k:v for k,v in godot_sets.items() if v['platform'] == 'windows' and v['arch'] in ['x86_64']}

    def gen_dot_folder( godot_set ):
        cmd_parts = [
            f'"{godot_set['editor']}"',
            '-e',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        stream_command(' '.join(cmd_parts), dry=opts['dry'])

    def run_test( godot_set:dict ) -> dict:
        result = {
            'fileset': godot_set['name'],
            'status': 'Failed'
        }
        cmd_parts = [
            f'{godot_set['template_release']}',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        output = ['']
        errors = ['']

        returncode = 'dnf'
        try:
            proc:CompletedProcess = stream_command( ' '.join(cmd_parts), dry=opts['dry'],
                stdout_handler=lambda msg: output.append(msg),
                stderr_handler=lambda msg: errors.append(msg) )
            returncode = proc.returncode
            proc.check_returncode()
        except Exception as e:
            if opts['debug']: raise e
            from rich.console import Group
            panel_content = Group(f'ReturnCode: {returncode}',
                Panel( str(e), title='Exception', title_align='left' ),
                Panel( '\n'.join( output ), title='stderr', title_align='left'),
                Panel( '\n'.join( errors ), title='stderr', title_align='left')
            )
            print( Panel( panel_content,  expand=False, title='Errors', title_align='left', width=120 ) )
            return result

        if opts['verbose']:
            print( Panel( '\n'.join( output ),  expand=False, title='Test Output', title_align='left', width=120 ))

        if 'PASSED' in ''.join(output):
            return result | {'status': 'Success'}
        else:
            print( Panel( '\n'.join( output ),  expand=False, title='stdout', title_align='left', width=120 ))

        return result


    testing_results = []

    while config['ok'] and 'test' in opts['build_actions']:
        with Section( "Testing" ):
            config['ok'] = False
            console.set_window_title(f'Test - {build['name']}')

            godot_sets = collect_godots()
            num_tests = len(godot_sets)
            h(f'Found {num_tests} godot exe file sets to test with')

            test_project_dir = build['source_path'] / 'test/project'
            dot_godot_dir = test_project_dir / '.godot'

            # FIXME use fresh to delete the .godot folder

            for set_name, set_value in godot_sets.items():
                if dot_godot_dir.exists():
                    break
                h(f'Generating the .godot folder using: {set_name}')
                try: gen_dot_folder( set_value )
                except SubprocessError as e:
                    print( '[red]Godot exited abnormally during .godot folder creation')
                    if opts['debug']: raise e


            if not dot_godot_dir.exists() and not opts['dry']:
                print('[red]Error: Creating .godot folder')
                testing_results += ['Creation of .godot folder failed.']
                config['ok'] = False
                break

            if opts['dry']:
                h( 'Dry-Run: Test Completed' )
                config['ok'] = True
                break

            talley = 0
            for set_name, set_value in godot_sets.items():
                if opts['verbose']:
                    t3("Running Test")
                    h('Using Fileset:')
                    p( set_value, pretty=True )
                result = run_test( set_value )
                if result['status'] == 'Success': talley += 1
                testing_results.append( result )

            success = talley == num_tests
            if success: config['ok'] = True

            results:dict = {
                'status': 'Success' if success else 'Failed',
                'duration': f'{talley} / {num_tests}',
            }
            print('json:', dumps({'test':results}, default=str))
            stats['test'] = results
            break


# MARK: SCons Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___  ___               ___         _      _                               │
# │ / __|/ __|___ _ _  ___ / __| __ _ _(_)_ __| |_                             │
# │ \__ \ (__/ _ \ ' \(_-< \__ \/ _| '_| | '_ \  _|                            │
# │ |___/\___\___/_||_/__/ |___/\__|_| |_| .__/\__|                            │
# │                                      |_|                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

def check_scons():
    project:dict = {}
    build:dict = {}
    # start_script

    #[=================================[ Check ]=================================]
    scons = build['scons']

    # Figure out the build path
    if "build_dir" in scons.keys():
        scons['build_path'] = project['path'] / build['source_dir'] / scons['build_dir']
    else:
        scons['build_path'] = project['path'] / build['source_dir']

    build_path = scons['build_path']

    try: os.chdir(build_path)
    except FileNotFoundError as fnf:
        fnf.add_note( f'Missing Folder {build_path}' )
        raise fnf

    # requires SConstruct file existing in the current directory.
    if not (build_path / "SConstruct").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"[red]Missing SConstruct in {build_path}")
        raise fnf


def build_scons():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    #[=================================[ Build ]=================================]
    from share.actions_scons import scons_build

    if config['ok'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')
        with Timer(name='build') as timer:
            scons_build( config )
        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()


def clean_scons():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    from subprocess import CalledProcessError

    #[=================================[ Clean ]=================================]
    if config['ok'] and 'clean' in opts['build_actions']:
        console.set_window_title(f'Clean - {build['name']}')
        h2("SCons Clean")

        with Timer(name='clean', push=False) as timer:
            try:
                proc = stream_command( "scons --clean" , dry=config['dry'])
                # Change status depending on the truthiness of returnvalue
                # where False is Success and True is Failure.
                timer.status = TaskStatus.FAILED if proc.returncode else TaskStatus.COMPLETED
            except CalledProcessError as e:
                # FIXME should this be more generic and handled elsewhere?
                print( '[red]subprocess error')
                print( f'[red]{e}' )
                timer.status = TaskStatus.FAILED
        stats['clean'] = timer.get_dict()
        config['ok'] = timer.ok()

# MARK: CMake
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ __  __      _         ___         _      _                           │
# │  / __|  \/  |__ _| |_____  / __| __ _ _(_)_ __| |_                         │
# │ | (__| |\/| / _` | / / -_) \__ \/ _| '_| | '_ \  _|                        │
# │  \___|_|  |_\__,_|_\_\___| |___/\__|_| |_| .__/\__|                        │
# │                                          |_|                               │
# ╰────────────────────────────────────────────────────────────────────────────╯

def pre_cmake():
    build:dict = {}
    # start_script

    #[==============================[ Pre-CMake ]==============================]
    cmake = build['cmake']
    if 'godot_build_profile' in cmake:
        profile_path:Path = build['source_path'] / cmake['godot_build_profile']
        cmake['config_vars'].append( f'-DGODOT_BUILD_PROFILE="{profile_path.as_posix()}"' )


# MARK: Configure
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ██████  ███    ██ ███████ ██  ██████  ██    ██ ██████  ███████    │
# │ ██      ██    ██ ████   ██ ██      ██ ██       ██    ██ ██   ██ ██         │
# │ ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ██    ██ ██████  █████      │
# │ ██      ██    ██ ██  ██ ██ ██      ██ ██    ██ ██    ██ ██   ██ ██         │
# │  ██████  ██████  ██   ████ ██      ██  ██████   ██████  ██   ██ ███████    │
# ╰────────────────────────────────────────────────────────────────────────────╯

def gen_scons( cfg:SimpleNamespace ) -> bool:
    cfg.verbs += ['build', 'clean']
    cfg.script_parts +=  [check_scons, build_scons, clean_scons,]

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

        case 'emscripten':
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

def gen_cmake( cfg:SimpleNamespace ) -> bool:
    from share.snippets import cmake_check, cmake_configure, cmake_build
    cfg.verbs += ['configure', 'build']
    cfg.script_parts += [pre_cmake, cmake_check, cmake_configure, cmake_build]

    setattr(cfg, 'cmake', {
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
    'scons': gen_scons,
    'cmake': gen_cmake
}

# MARK: Variant Config
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _          _      ___           __ _                        │
# │ \ \ / /_ _ _ _(_)__ _ _ _| |_   / __|___ _ _  / _(_)__ _                   │
# │  \ V / _` | '_| / _` | ' \  _| | (__/ _ \ ' \|  _| / _` |                  │
# │   \_/\__,_|_| |_\__,_|_||_\__|  \___\___/_||_|_| |_\__, |                  │
# │                                                    |___/                   │
# ╰────────────────────────────────────────────────────────────────────────────╯
variations = { 'default' :lambda cfg:True }

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
variations['double'] = variant_double

# TODO
# * nothreads
# * hotreload
# * exceptions
# * staticcpp
# * debugcrt

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
        cfg.name.append( variant )

        if not configure_func( cfg ): # Skip variants who's configuration step fails.
            continue

        # TODO If I want to test against multiple binaries then I need to specify multiple.
        '{root}/godot/{host}.{toolchain}.{platform}.{arch}.{variant}/bin/godot.{platform}.{target}[.double].{arch}[.llvm].console.exe'
        # For now I will just focus on the current OS
        setattr(cfg, 'godot_e', Path('C:/build/godot/w64.msvc/bin/godot.windows.editor.x86_64.console'))
        setattr(cfg, 'godot_tr', Path('C:/build/godot/w64.msvc/bin/godot.windows.template_release.x86_64.console'))
        setattr(cfg, 'godot_td', Path('C:/build/godot/w64.msvc/bin/godot.windows.template_debug.x86_64.console'))

        configs_out.append( cfg )
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
def generate( opts:SimpleNamespace ) -> dict:
    from share.snippets import source_git, show_stats


    project_base.update({
        'path': opts.path / project_base['name'],
        'build_configs': dict[str,SimpleNamespace]()
    })
    project = SimpleNamespace(**project_base )

    config_base = SimpleNamespace(**{
        'name':'',
        'source_dir':'',
        'gitdef':{},
        'verbs':['source'],
        'script_parts':[source_git]
    })

    # Host environment toolchain and build tools
    configs:list[SimpleNamespace] = expand_host_env( config_base, opts )
    configs = expand( configs, expand_buildtools )

    # Naming upto now.
    for cfg in configs:
        # Host
        cfg.name = [cfg.host]
        cfg.source_dir = [cfg.host]

        # Toolchain
        if cfg.toolchain.name not in  ['android', 'emscripten']:
            cfg.name.append(cfg.toolchain.name)
            cfg.source_dir.append(cfg.toolchain.name)

        # Platform
        cfg.name.append(godot_platforms[cfg.platform])

        if len(cfg.toolchain.platform) > 1:
            cfg.source_dir.append(cfg.platform)

        # arch
        if cfg.arch != 'wasm32':
            cfg.name.append( godot_arch[cfg.arch] )

        if len(cfg.toolchain.arch) > 1:
            cfg.source_dir.append( cfg.arch )

    # target and variants
    configs = expand( configs, expand_variant )

    for cfg in sorted( configs, key=lambda value: value.name ):
        cfg.verbs += ['test']
        cfg.script_parts += [test_script, show_stats]

        cfg.name.append( cfg.buildtool )
        cfg.source_dir.append( cfg.buildtool )

        if cfg.buildtool == 'cmake':
            cfg.cmake['build_dir'] = f'build-{cfg.platform}-{cfg.arch}-{cfg.variant}'

        if isinstance(cfg.name, list): cfg.name = '.'.join(cfg.name)
        if isinstance(cfg.source_dir, list): cfg.source_dir = '.'.join(cfg.source_dir)

        project.build_configs[cfg.name] = cfg

    return {project.name:project }