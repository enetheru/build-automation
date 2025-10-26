import copy
from copy import deepcopy
from types import SimpleNamespace

import share.expand_config
from share.config import gopts
from share.expand_config import expand_sourcedefs, expand_toolchains, expand_buildtools, short_host, expand_func
from share.script_preamble import *


# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯
def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    """Generate build configurations for the godot-cpp project.

    Args:
        opts (SimpleNamespace): Configuration options including the project path.

    Returns:
        dict: A dictionary mapping project names to their SimpleNamespace configurations with build configs.
    """
    from share.snippets import source_git, show_stats
    from share.expand_config import (
        expand_func
    )

    name = 'godot-cpp'

    from share.config import (project_base, scons_base, cmake_base, git_base)
    project = SimpleNamespace({**vars(project_base), **{
        'name': name,
        'path': opts.path / name,
        'sources':{
            'git': SimpleNamespace({**vars(git_base), **{
                'tag': '4.5',
                'url': "https://github.com/godotengine/godot-cpp.git/",
                'ref': 'e83fd0904c13356ed1d4c3d09f8bb9132bdc6b77'
            }}),
        },
        'buildtools': {
            'scons': SimpleNamespace({**vars(scons_base), **{
                'expand':expand_scons,
            }}),
            'cmake': SimpleNamespace({**vars(cmake_base), **{
                'expand':expand_cmake,
                'targets':['godot-cpp-test'],
                'config_vars':[
                    '-DGODOTCPP_ENABLE_TESTING=ON',
                    '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
                ]
            }}),
        },
        'toolchains': gopts.toolchains.values() # get all of them
    }})

    from share.config import build_base
    build_start = SimpleNamespace({ **vars(build_base), **{
        'verbs': ['source'],
        'script_parts': [source_git],
        'arch': 'x86_64',
        'godotcpp_build_profile' : 'test/build_profile.json',
    }})

    # Host environment toolchain and build tools
    builds:list[SimpleNamespace] = expand_func([build_start], expand_sourcedefs, project)
    builds = expand_func( builds, expand_toolchains, project )
    builds = expand_func( builds, configure_toolchain )

    builds = expand_func( builds, expand_buildtools, project )

    # target and variants
    # builds = expand_func( builds, expand_variant )

    # Naming up to now.
    for build in builds:

        buildtool = build.buildtool
        toolchain = build.toolchain

        srcdir_parts = [
            short_host(),
            buildtool.name,
        ]

        name_parts = [
            toolchain.name,
            build.arch if build.platform not in ['emscripten'] else None,
            build.platform if build.platform not in ['android', 'emscripten'] else None,
            build.godotcpp_target
        #     build.variant if build.variant != 'default' else None,
        ]

        if buildtool.name == 'scons':
            build.name = '.'.join(filter(None,srcdir_parts+name_parts))
            build.source_dir =  build.name

        elif buildtool.name == 'cmake':
            cmake = build.buildtool

            name_parts += [
                cmake.short_type,
                cmake.short_gen,
            ]

            builddir_parts = ['build'] + name_parts

            build.name = '.'.join(filter(None,srcdir_parts+name_parts))
            build.source_dir = '.'.join(filter(None, srcdir_parts))
            build.buildtool.build_dir = '.'.join(filter(None,builddir_parts))

        build.verbs += ['test']
        build.script_parts += [test_script, show_stats]

    project.build_configs = {v.name: v for v in builds }
    return project

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────╖
# ║            ███████  ██████ ██████  ██ ██████  ████████ ███████             ║
# ║            ██      ██      ██   ██ ██ ██   ██    ██    ██                  ║
# ║            ███████ ██      ██████  ██ ██████     ██    ███████             ║
# ║                 ██ ██      ██   ██ ██ ██         ██         ██             ║
# ║            ███████  ██████ ██   ██ ██ ██         ██    ███████             ║
# ╙────────────────────────────────────────────────────────────────────────────╜

# MARK: Testing
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _____       _   _                                                         │
# │ |_   _|__ __| |_(_)_ _  __ _                                               │
# │   | |/ -_|_-<  _| | ' \/ _` |                                              │
# │   |_|\___/__/\__|_|_||_\__, |                                              │
# │                        |___/                                               │
# ╰────────────────────────────────────────────────────────────────────────────╯

def test_script():
    """Generate test configurations for SCons-based builds.

    Returns:
        list[SimpleNamespace]: List of configurations for testing different targets (e.g., template_release, template_debug).
    """
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    toolchain:dict = {}

    # start_script

    #[==================================[ Test ]==================================]
    from rich.panel import Panel
    from subprocess import SubprocessError, CompletedProcess
    from share.format import p
    from json import dumps

    import re

    def get_export_templates() -> list[SimpleNamespace]:

        export_set_template = SimpleNamespace(**{
            'type':'export_template',
            'version':str(),
            'platform':str(),
            'arch':str(),
            'editor':str(),
            'release':str(),
            'debug':str(),
        })

        set_list = list[SimpleNamespace]()
        path = Path('C:/Users/nicho/AppData/Roaming/Godot/export_templates')

        # Regular expression pattern
        export_template_pattern = re.compile(
            r"^(?P<platform>linux|windows)_(?P<type>debug|release)[_.](?P<arch>arm32|arm64|x86_32|x86_64)"
        )

        if not (path.exists() and path.is_dir()):
            return []
        try:
            for export_folder in Path(path).iterdir():
                if not export_folder.is_dir(): continue

                for file in export_folder.iterdir():
                    match = export_template_pattern.match(file.name)
                    if not match: continue

                    search_criteria = {"version": export_folder.name}

                    info = match.groupdict()

                    # Clean up: Remove None values and handle console flag
                    info = {k: v for k, v in info.items() if v is not None}

                    search_criteria['platform'] = info.pop('platform')
                    search_criteria['arch'] = info.pop('arch')

                    export_set = next(
                        (d for d in set_list
                         if all( hasattr(d,k) and getattr(d,k) == v
                                 for k, v in search_criteria.items()
                        )), None)
                    if export_set is None:
                        export_set = SimpleNamespace({**vars(export_set_template), **search_criteria})
                        set_list.append(export_set)

                    setattr(export_set, info['type'], file)

        except PermissionError:
            print("Permission denied")

        return set_list

    def collect_godots() -> dict:
        godot_arches = ['x86_64', 'x86_32', 'arm64', 'arm32', 'wasm32']

        # find all builds in the Godot build folder to test against.
        godot_path = Path( opts['path'] / 'godot' )
        godot_sets = {}
        for child in godot_path.glob(f'{toolchain['host']}*/'):
            # Get all the executables in the folder
            files = [f.name for f in (child / 'bin').glob('*.exe')]
            files = [*filter( lambda f: 'godot' in f , files )]
            files = [*filter( lambda f: 'console' not in f , files )]

            if not len(files):
                continue

            set_folder = child.name

            for f in files:
                # Chop up the godot.windows.target.* in to pieces and process them
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

                # update the dictionary
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

    def run_tests( data : SimpleNamespace ):
        config['ok'] = False
        console.set_window_title(f'Test - {build['name']}')

        # FIXME use fresh to delete the .godot folder

        for set_name, set_value in data.godot_sets.items():
            if data.dot_godot_dir.exists():
                break
            fmt.h(f'Generating the .godot folder using: {set_name}')
            try: gen_dot_folder( set_value )
            except SubprocessError as e:
                print( '[red]Godot exited abnormally during .godot folder creation')
                if opts['debug']: raise e


        if not data.dot_godot_dir.exists() and not opts['dry']:
            print('[red]Error: Creating .godot folder')
            testing_results += ['Creation of .godot folder failed.']
            config['ok'] = False
            return []

        if opts['dry']:
            fmt.h( 'Dry-Run: Test Completed' )
            config['ok'] = True
            return []

        talley = 0
        for set_name, set_value in godot_sets.items():
            if opts['verbose']:
                fmt.t3("Running Test")
                fmt.h('Using Fileset:')
                p( set_value, pretty=True )
            result = run_test( set_value )
            if result['status'] == 'Success': talley += 1
            testing_results.append( result )

        test_data['results'] = testing_results

    def testing_setup() -> SimpleNamespace:
        export_templates =  get_export_templates()

        godot_sets = collect_godots()
        num_sets = len(godot_sets)

        fmt.h(f'Found {num_sets} godot exe file sets to test with')
        # if not num_sets:
        #     raise Exception( "There are no godot executables found")

        test_case = SimpleNamespace(**{
            'name':str(),
            'result':False,
            'msg':str(),
            'exe_set':SimpleNamespace()
        })

        rig = SimpleNamespace(**{
            'test_dir':build['source_path'] / 'test/project',
            'num_tests':len(godot_sets),
            'godot_sets':godot_sets,
            'num_sets':num_sets,
            'talley':0,
            'cases':list[SimpleNamespace](),
            'results':list[SimpleNamespace]()
        })

        for template in export_templates:
            if template.platform != 'windows':
                continue
            rig.cases.append( SimpleNamespace({**vars(test_case),**{


            }}))

        if not rig.cases:
            raise Exception( "There are no test cases")

        return rig


    if config['ok'] and 'test' in opts['build_actions']:
        with fmt.Section( "Testing" ):
            test_rig = testing_setup()
            if test_rig is None:
                config['ok'] = False
            else:
                run_tests( test_rig )

                success = test_rig.talley == test_rig.num_tests

                results:dict = {
                    'status': 'Success' if success else 'Failed',
                    'duration': f'{test_rig.talley} / {test_rig.num_tests}',
                }
                print('json:', dumps({'test':results}, default=str))
                stats['test'] = results


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
    buildtool:dict = {}
    # start_script

    #[=================================[ Check ]=================================]
    scons = buildtool

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

        with Timer(name='clean', push=False) as timer, fmt.Section("SCons Clean"):
            try:
                proc = stream_command( "scons --clean -s" , dry=opts['dry'])
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


def build_scons():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    buildtool:dict = {}
    stats:dict = {}
    # start_script

    #[=================================[ Build ]=================================]

    if config['ok'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')
        with Timer(name='build') as timer, fmt.Section('Scons Build'):

            scons: dict     = buildtool

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

            build_command: str = " ".join(filter(None, cmd_chunks))
            stream_command(build_command, dry=opts['dry'])

        stats['build'] = timer.get_dict()
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
    buildtool:dict = {}
    # start_script

    # MARK: Pre-CMake
    #[==============================[ Pre-CMake ]==============================]
    # This exists because we dont know the location of the build profiel until
    # after the repo is cloned.
    cmake = buildtool
    if 'godotcpp_build_profile' in build:
        profile_path:Path = build['source_path'] / build['godotcpp_build_profile']
        cmake['config_vars'].append( f'-DGODOTCPP_BUILD_PROFILE="{profile_path.as_posix()}"' )

# MARK: Expansion
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ ███████ ██   ██ ██████   █████  ███    ██ ███████ ██  ██████  ███    ██    │
# │ ██       ██ ██  ██   ██ ██   ██ ████   ██ ██      ██ ██    ██ ████   ██    │
# │ █████     ███   ██████  ███████ ██ ██  ██ ███████ ██ ██    ██ ██ ██  ██    │
# │ ██       ██ ██  ██      ██   ██ ██  ██ ██      ██ ██ ██    ██ ██  ██ ██    │
# │ ███████ ██   ██ ██      ██   ██ ██   ████ ███████ ██  ██████  ██   ████    │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: ToolChains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ _____         _  ___ _         _                                           │
# │|_   _|__  ___| |/ __| |_  __ _(_)_ _  ___                                  │
# │  | |/ _ \/ _ \ | (__| ' \/ _` | | ' \(_-<                                  │
# │  |_|\___/\___/_|\___|_||_\__,_|_|_||_/__/                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def configure_toolchain(config:SimpleNamespace) -> list[SimpleNamespace]:
    if config.toolchain.name != 'android':
        return [config]
    tc = config.toolchain
    ndk_version = '28.1.13356709'
    setattr(tc, 'packages', {
        'platform-tools':'',
        "build-tools":"35.0.0",
        "platforms":"android-35",
        "cmdline-tools":"latest",
        "cmake":"3.10.2.4988404",
        'ndk':ndk_version,
    })
    setattr(tc, 'ndk_path', f'{tc.sdk_path}\\ndk\\{ndk_version}')
    setattr(tc, 'api_level', '35')

    return [config]

# MARK: BuildTools
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___      _ _    _ _____         _                                         │
# │ | _ )_  _(_) |__| |_   _|__  ___| |___                                     │
# │ | _ \ || | | / _` | | |/ _ \/ _ \ (_-<                                     │
# │ |___/\_,_|_|_\__,_| |_|\___/\___/_/__/                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Scons
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                                                                       │
# │ / __| __ ___ _ _  ___                                                      │
# │ \__ \/ _/ _ \ ' \(_-<                                                      │
# │ |___/\__\___/_||_/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_scons( config:SimpleNamespace ) -> list[SimpleNamespace]:
    from godot.config import godot_platforms, godot_arch

    config.verbs += ['build', 'clean']
    config.script_parts +=  [check_scons, clean_scons, build_scons]

    platform = godot_platforms[config.platform]
    arch = godot_arch[config.arch]

    config.buildtool = deepcopy(config.buildtool)
    scons = config.buildtool
    scons.build_dir = 'test'
    scons.build_vars += [
        "compiledb=yes",
        f"platform={platform}",
        f"arch={arch}",
        "build_profile=build_profile.json",
    ]

    match config.toolchain.name:
        case 'msvc' | 'android' | 'emscripten' | 'appleclang':
            pass
        case "llvm":
            if config.arch != 'x86_64': return []
            scons.build_vars.append("use_llvm=yes")

        case "llvm-mingw":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")
            scons.build_vars.append(f"mingw_prefix={config.toolchain.sysroot.as_posix()}")

        case "mingw64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append(f"mingw_prefix={config.toolchain.sysroot.as_posix()}")

        case "msys2-clang64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")

        case "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            scons.build_vars.append("use_mingw=yes")

        case _:
            return []

    # Split the compile up into individual targets
    configs_out = []
    for target in ["template_release", "template_debug", "editor"]:
        cfg = copy.deepcopy(config)
        setattr(cfg, 'godotcpp_target', target)

        scons = cfg.buildtool
        scons.target = target
        scons.build_vars.append(f'target={target}')

        configs_out.append( cfg )

    return configs_out

# MARK: CMake
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___ __  __      _                                                         │
# │ / __|  \/  |__ _| |_____                                                   │
# │| (__| |\/| / _` | / / -_)                                                  │
# │ \___|_|  |_\__,_|_\_\___|                                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_cmake_target( config:SimpleNamespace ) -> list[SimpleNamespace]:
    configs_out = []
    for target in ["template_release", "template_debug", "editor"]:
        cfg = copy.deepcopy(config)
        setattr(cfg, 'godotcpp_target', target)
        cmake = cfg.buildtool
        cmake.config_vars.append(f'-DGODOTCPP_TARGET={target}')
        configs_out.append( cfg )
    return configs_out

def expand_cmake( config:SimpleNamespace ) -> list[SimpleNamespace]:
    """Expand CMake build configurations for different targets.

    Args:
        config (SimpleNamespace): The base build configuration.

    Returns:
        list[SimpleNamespace]: List of configurations for CMake targets (e.g., template_release, template_debug).
    """

    # Add the cmake script section
    config.script_parts += [pre_cmake]

    # use the builtin expander for config types and generators.
    configs_out = expand_func( [config], share.expand_config.expand_cmake  )

    # Expand the targets
    configs_out = expand_func( configs_out, expand_cmake_target  )

    for config in configs_out:
        delattr(config.buildtool, 'expand')
    return configs_out

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
def variant_debug_symbols( cfg:SimpleNamespace ) -> bool:
    """Configure a build with debug symbols.

    Args:
        cfg (SimpleNamespace): The build configuration to modify.

    Returns:
        bool: True if the configuration was successfully applied, False otherwise.
    """
    setattr( cfg, 'variant', 'debug' )
    if cfg.arch not in ['x86_64', 'arm64']: return False
    match cfg.buildtool:
        case 'scons':
            cfg.scons.build_vars.append("debug_symbols=yes")
        case 'cmake':
            return False
    return True

# MARK: double
def variant_double( cfg:SimpleNamespace ) -> bool:
    """Configure a build with double precision.

    Args:
        cfg (SimpleNamespace): The build configuration to modify.

    Returns:
        bool: True if the configuration was successfully applied, False otherwise.
    """
    setattr( cfg, 'variant', 'double' )
    if cfg.arch not in ['x86_64', 'arm64']: return False
    match cfg.buildtool:
        case 'scons':
            cfg.scons.build_vars.append("precision=double")
        case 'cmake':
            cfg.cmake.config_vars.append("-DGODOTCPP_PRECISION=double")
    return True


def expand_variant( config:SimpleNamespace ) -> list:
    """Expand build configurations for different variants (e.g., debug, double).

    Args:
        config (SimpleNamespace): The base build configuration.

    Returns:
        list[SimpleNamespace]: List of configurations with applied variants.
    """
    configs_out:list = []

    variations = {
        'default': lambda default_accept: True,
        'double': variant_double,
        'debug': variant_debug_symbols,
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
