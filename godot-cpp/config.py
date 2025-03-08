import copy
from types import SimpleNamespace

from share.script_preamble import *

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯
def generate( opts:SimpleNamespace ) -> dict:
    from godot.config import godot_platforms, godot_arch
    from share.snippets import source_git, show_stats
    from share.expand_config import (
        expand_host_env, expand_func, expand_list, expand_cmake, cmake_generators,
        cmake_config_types
    )

    name = 'godot-cpp'

    project = SimpleNamespace(**{
        'name':name,
        'path': opts.path / name,
        'gitdef':{
            'url':"https://github.com/enetheru/godot-cpp.git/",
            'ref':'master'
        },
        # TODO rename all 'build_configs' to 'builds'
        'build_configs' : dict[str,SimpleNamespace]()
    })

    build_base = SimpleNamespace(**{
        'verbs':['source'],
        'script_parts':[source_git]
    })

    # Host environment toolchain and build tools
    builds:list[SimpleNamespace] = expand_host_env( build_base, opts )
    builds = expand_list( builds, 'buildtool', ['scons','cmake'] )
    builds = expand_func( builds, expand_buildtools )

    # target and variants
    builds = expand_func( builds, expand_variant )

    # Naming upto now.
    for build in builds:

        toolchain = build.toolchain.name
        arch = godot_arch[build.arch]
        platform = godot_platforms[build.platform]

        name_parts = [
            build.host,
            toolchain if toolchain != 'emscripten' else None,
            platform if build.platform != 'android' else None,
            arch if arch != 'wasm32' else None,
            build.variant
        ]

        srcdir_parts = [
            build.host,
            toolchain,
            build.variant
        ]

        if build.buildtool == 'scons':
            name_parts += ['scons']
            srcdir_parts += ['scons']

        elif build.buildtool == 'cmake':
            cmake = build.cmake
            short_gen = cmake_generators[cmake['generator']]
            short_type = cmake_config_types[cmake['config_type']]
            name_parts += [
                short_gen if build.buildtool == 'cmake' else None,
                short_type if build.buildtool == 'cmake' else None,
            ]
            srcdir_parts += [
                short_gen if short_gen != build.toolchain.name else None
            ]

        build.name = '.'.join(filter(None,name_parts))
        build.source_dir = '.'.join(filter(None, srcdir_parts))

        build.verbs += ['test']
        build.script_parts += [test_script, show_stats]

    project.build_configs = {v.name: v for v in builds }
    return { project.name: project }

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

# MARK: Testing
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____       _   _                                                         │
# │ |_   _|__ __| |_(_)_ _  __ _                                               │
# │   | |/ -_|_-<  _| | ' \/ _` |                                              │
# │   |_|\___/__/\__|_|_||_\__, |                                              │
# │                        |___/                                               │
# ╰────────────────────────────────────────────────────────────────────────────╯

def test_script():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    #[==================================[ Test ]==================================]
    from rich.panel import Panel
    from subprocess import SubprocessError, CompletedProcess
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
    project:dict = {}
    toolchain:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    #[=================================[ Build ]=================================]
    from os import environ
    from time import sleep

    if config['ok'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')
        with Timer(name='build') as timer, Section('Scons Build'):

            scons: dict     = build["scons"]

            try: os.chdir( scons['build_path'] )
            except FileNotFoundError as fnf:
                fnf.add_note( f'Missing Folder {scons['build_path']}' )
                raise fnf

            jobs = opts["jobs"]
            cmd_chunks = [
                "scons",
                f"-j {jobs}" if jobs > 0 else None,
                "verbose=yes" if opts["verbose"] else None,
            ]
            if "build_vars" in scons.keys():
                cmd_chunks += scons["build_vars"]

            for target in scons["targets"]:
                h(f"Building {target}")
                build_command: str = " ".join(filter(None, cmd_chunks + [f"target={target}"]))

                sleep(3)
                # I found that if i dont clean the repository then files are unfortunately wrong.
                stream_command('scons --clean -s ', env=toolchain['env'], dry=opts['dry'])
                # FIXME Sometimes i get an exception when this runs
                #   scons: Could not remove 'C:\build\godot-cpp\w64.llvm-mingw.default.scons.5458596\gen\src\classes\resource.cpp'
                #   The process cannot access the file because it is being used by another process
                sleep(3)

                stream_command(build_command, env=toolchain['env'], dry=opts['dry'])

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
        cmake['config_vars'].append( f'-DGODOTCPP_BUILD_PROFILE="{profile_path.as_posix()}"' )

# MARK: Expansion
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ ███████ ██   ██ ██████   █████  ███    ██ ███████ ██  ██████  ███    ██    │
# │ ██       ██ ██  ██   ██ ██   ██ ████   ██ ██      ██ ██    ██ ████   ██    │
# │ █████     ███   ██████  ███████ ██ ██  ██ ███████ ██ ██    ██ ██ ██  ██    │
# │ ██       ██ ██  ██      ██   ██ ██  ██ ██      ██ ██ ██    ██ ██  ██ ██    │
# │ ███████ ██   ██ ██      ██   ██ ██   ████ ███████ ██  ██████  ██   ████    │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: BuildTools
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___      _ _    _ _____         _                                         │
# │ | _ )_  _(_) |__| |_   _|__  ___| |___                                     │
# │ | _ \ || | | / _` | | |/ _ \/ _ \ (_-<                                     │
# │ |___/\_,_|_|_\__,_| |_|\___/\___/_/__/                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_buildtools( config:SimpleNamespace ) -> list[SimpleNamespace]:
    from share.expand_config import expand_cmake

    configs_out = []
    for tool in ['scons', 'cmake']:
        cfg = copy.deepcopy(config)

        setattr(cfg, 'buildtool', tool )
        match tool:
            case 'scons':
                configs_out += expand_scons( cfg )

            case 'cmake':
                cfg.script_parts += [pre_cmake]
                setattr( cfg, 'cmake', {
                    'godot_build_profile':'test/build_profile.json',
                    'targets':['godot-cpp.test.template_release','godot-cpp.test.template_debug','godot-cpp.test.editor'],
                    'config_vars':  ['-DGODOTCPP_ENABLE_TESTING=ON']
                })
                configs_out += expand_cmake( cfg )
    return configs_out

# MARK: Scons
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                                                                       │
# │ / __| __ ___ _ _  ___                                                      │
# │ \__ \/ _/ _ \ ' \(_-<                                                      │
# │ |___/\__\___/_||_/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_scons( config:SimpleNamespace ) -> list[SimpleNamespace]:
    from godot.config import godot_platforms, godot_arch

    match getattr(config, 'buildtool', None):
        case 'scons':
            pass
        case None:
            setattr(config, 'buildtool', 'scons' )
        case _: #ignore if buildtool is something other than None or scons
            return [config]


    config.verbs += ['build', 'clean']
    config.script_parts +=  [check_scons, build_scons, clean_scons,]

    platform = godot_platforms[config.platform]
    arch = godot_arch[config.arch]

    setattr( config, 'scons', {
                                  'build_dir':'test',
                                  "build_vars":[
                                      "compiledb=yes",
                                      f"platform={platform}",
                                      f"arch={arch}",
                                      "build_profile=build_profile.json",
                                  ],
                                  "targets": ["template_release", "template_debug", "editor"],
                              } | getattr( config, 'scons', {}) )

    match config.toolchain.name:
        case 'msvc' | 'android' | 'emscripten' | 'appleclang':
            pass
        case "llvm":
            if config.arch != 'x86_64': return []
            config.scons["build_vars"].append("use_llvm=yes")

        case "llvm-mingw":
            config.scons["build_vars"].append("use_mingw=yes")
            config.scons["build_vars"].append("use_llvm=yes")
            config.scons["build_vars"].append(f"mingw_prefix={config.toolchain.sysroot}")

        case "msys2-clang64":
            config.scons["build_vars"].append("use_mingw=yes")
            config.scons["build_vars"].append("use_llvm=yes")

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            config.scons["build_vars"].append("use_mingw=yes")

        case _:
            return []

    return [config]

# MARK: Variations
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _      _   _                                                │
# │ \ \ / /_ _ _ _(_)__ _| |_(_)___ _ _  ___                                   │
# │  \ V / _` | '_| / _` |  _| / _ \ ' \(_-<                                   │
# │   \_/\__,_|_| |_\__,_|\__|_\___/_||_/__/                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Variant Config
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _          _      ___           __ _                        │
# │ \ \ / /_ _ _ _(_)__ _ _ _| |_   / __|___ _ _  / _(_)__ _                   │
# │  \ V / _` | '_| / _` | ' \  _| | (__/ _ \ ' \|  _| / _` |                  │
# │   \_/\__,_|_| |_\__,_|_||_\__|  \___\___/_||_|_| |_\__, |                  │
# │                                                    |___/                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: double
def variant_double( cfg:SimpleNamespace ) -> bool:
    setattr( cfg, 'variant', 'double' )
    if cfg.arch not in ['x86_64', 'arm64']: return False
    match cfg.buildtool:
        case 'scons':
            cfg.scons["build_vars"].append("precision=double")
        case 'cmake':
            cfg.cmake["config_vars"].append("-DGODOTCPP_PRECISION=double")
    return True

def expand_variant( config:SimpleNamespace ) -> list:
    configs_out:list = []

    variations = {
        'default': lambda cfg: True,
        'double': variant_double
        # TODO
        # nothreads
        # hotreload
        # exceptions
        # staticcpp
        # debugcrt
    }

    for variant, configure_func in variations.items():
        cfg = copy.deepcopy(config)
        setattr( cfg, 'variant', variant )

        if not configure_func( cfg ): # Skip variants who's configuration step fails.
            continue

        configs_out.append( cfg )
    return configs_out