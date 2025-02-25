import copy
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

def source_git():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    project:dict = {}
    build:dict = {}
    # start_script

    #[=================================[ Source ]=================================]
    from share.actions_git import git_checkout
    from git.exc import GitCommandError

    if config['ok'] and 'source' in opts['build_actions']:
        console.set_window_title(f'Source - {build['name']}')
        section = Section( "Git Checkout" )
        section.start()

        # merge definitions project < build < opts
        gitdef = project['gitdef'] | build['gitdef'] | opts['gitdef']

        # Verify we have cloned the repo.
        gitdir = project['gitdir']
        if not gitdir.exists():
            fnf = FileNotFoundError()
            fnf.add_note(f'Missing bare git repo path: {gitdir}, project needs to be fetched')
            raise fnf

        repo = git.Repo(gitdef['gitdir'])

        pattern = gitdef['ref'] if gitdef['remote'] == 'origin' else f'{gitdef['remote']}/{gitdef['ref']}'
        try:
            bare_hash = repo.git.rev_parse('--short', pattern)
        except GitCommandError as e:
            print(e)
            exit(1)

        if 'override' in gitdef:
            build['source_dir'] += f'.{bare_hash}'

        build['source_path'] = project['path'] / build['source_dir']


        worktree_path = build["source_path"]

        if not worktree_path.exists():
            # Perhaps we deleted the worktree folder, in which case prune it
            cmd_args = [ 'prune',
                '--verbose' if opts['verbose'] else None,
                '--dry-run' if opts['dry'] else None ]
            repo.git.worktree( filter(None, cmd_args) )

            h("Create WorkTree")
            os.chdir( gitdir )

            cmd_args = [ 'add', '--detach', worktree_path, pattern ]
            if opts['dry']:
                print(f'dry-run: git worktree {' '.join(filter(None, cmd_args))}')

            else:
                repo.git.worktree( filter(None, cmd_args) )

        if worktree_path.exists():
            worktree = git.Repo( worktree_path )
            worktree_hash = worktree.git.rev_parse('--short', pattern)

            if bare_hash != worktree_hash:
                h("Update WorkTree")
                cmd_args = [ '--force', '--detach', pattern ]
                if opts['dry']:
                    print(f'dry-run: git checkout {' '.join(filter(None, cmd_args))}')
                else:
                    worktree.git.checkout( filter(None, cmd_args) )
            else:
                h("WorkTree is Up-to-Date")

            print( worktree.git.log('-1') )

        section.end()
        config['ok'] = True

def test_script():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    #[==================================[ Test ]==================================]
    from subprocess import SubprocessError
    from rich.panel import Panel

    def gen_dot_folder():
        cmd_parts = [
            f'"{godot_editor}"',
            '-e',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        stream_command(' '.join(cmd_parts), dry=opts['dry'])

    def run_test() -> list:
        cmd_parts = [
            f'"{godot_release_template}"',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        output = ['']
        stream_command( ' '.join(cmd_parts), dry=opts['dry'],
            stdout_handler=lambda msg: output.append(msg),
            stderr_handler=lambda msg: output.append( f'[red]{msg}[/red]' ) )
        return output

    while config['ok'] and 'test' in opts['build_actions']:
        config['ok'] = False
        console.set_window_title(f'Test - {build['name']}')
        with Timer(name='test') as timer, Section("Testing"):

            godot_editor = build['godot_e']
            godot_release_template = build['godot_tr']

            test_project_dir = build['source_path'] / 'test/project'
            dot_godot_dir = test_project_dir / '.godot'

            if dot_godot_dir.exists():
                # FIXME use fresh to delete the .godot folder
                pass
            else:
                h('Generating the .godot folder')
                try: gen_dot_folder()
                except SubprocessError as e:
                    print( '[red]Godot exited abnormally during .godot folder creation')
                    raise e

            if not dot_godot_dir.exists() and not opts['dry']:
                print('[red]Error: Creating .godot folder')
                timer.status = TaskStatus.FAILED
                break

            h("Run the test project")
            if opts['dry']:
                h( 'Dry-Run: Test Completed' )
                timer.status = TaskStatus.COMPLETED
                config['ok'] = True
                break

            try: output = run_test()
            except SubprocessError as e:
                # FIXME Godot exited abnormally when running the test project
                print( '[red]Error: Godot exited abnormally when running the test project')
                print( '    This requires investigation as it appears to only happen in cmake builds')
                timer.status = TaskStatus.FAILED
                break

            print( Panel( '\n'.join( output ),  expand=False, title='Test Execution', title_align='left', width=120 ))

            for line in output:
                if line.find( 'PASSED' ) > 0:
                    h( 'Test Succeeded' )
                    timer.status = TaskStatus.COMPLETED
                    config['ok'] = True
                    break
                else:
                    timer.status = TaskStatus.FAILED
            break

        stats['test'] = timer.get_dict()
        config['ok'] = timer.ok()

def stats_script():
    config:dict = {}
    stats:dict = {}
    # start_script

    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(title="Stats", highlight=True, min_width=80)

    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Duration", style="green")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}')

    rich.print( table )
    if not config['ok']: exit(1)

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

    if config['ok'] and 'build' in build['verbs'] and 'build' in opts['build_actions']:
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
    if config['ok'] and 'clean' in build['verbs'] and 'clean' in opts['build_actions']:
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

# MARK: CMake Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ __  __      _         ___         _      _                           │
# │  / __|  \/  |__ _| |_____  / __| __ _ _(_)_ __| |_                         │
# │ | (__| |\/| / _` | / / -_) \__ \/ _| '_| | '_ \  _|                        │
# │  \___|_|  |_\__,_|_\_\___| |___/\__|_| |_| .__/\__|                        │
# │                                          |_|                               │
# ╰────────────────────────────────────────────────────────────────────────────╯

def check_cmake():
    project:dict = {}
    build:dict = {}
    # start_script

    #[===============================[ Check ]===============================]
    cmake = build['cmake']

    source_path = build.setdefault("source_path", project['path'] / build['source_dir'])

    # requires CMakeLists.txt file existing in the current directory.
    if not (source_path / "CMakeLists.txt").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"Missing CMakeLists.txt in {source_path}")
        raise fnf

    build_dir = cmake.setdefault('build_dir', f'build-{build['platform']}-{build['arch']}-{build['variant']}')
    build_path = cmake.setdefault('build_path', source_path / build_dir )

    # Create Build Directory
    if not build_path.is_dir():
        t3(f"Creating {cmake['build_dir']}")
        os.mkdir(build_path)

    try:
        os.chdir(build_path)
    except FileNotFoundError as fnf:
        fnf.add_note(f'Missing Folder {build_path}')
        raise fnf

def configure_cmake():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    toolchain:dict = {}
    # start_script

    #[===============================[ Configure ]===============================]
    cmake = build['cmake']

    if config['ok'] and 'configure' in build['verbs'] and 'configure' in opts['build_actions']:
        h2("CMake Configure")
        s1("CMake Configure")
        console.set_window_title(f'Configure - {build['name']}')

        config_opts = [
            "--fresh" if 'fresh' in opts['build_actions'] else None,
            "--log-level=VERBOSE" if not opts["quiet"] else None,
            f'-S "{build['source_path']}"',
            f'-B "{cmake['build_path']}"',
        ]

        if 'cmake' in toolchain:
            tc = toolchain['cmake']
            if 'toolchain' in tc:
                toolchain_file = opts["path"] / toolchain['cmake']['toolchain']
                config_opts.append( f'--toolchain "{os.fspath(toolchain_file)}"' )
            for var in tc.get('config_vars', []):
                config_opts.append(var)

        if 'generator' in cmake:
            config_opts.append( f'-G "{cmake['generator']}"' )

        if "config_vars" in cmake:
            config_opts += cmake["config_vars"]

        if 'godot_build_profile' in cmake:
            profile_path:Path = build['source_path'] / cmake['godot_build_profile']
            config_opts.append( f'-DGODOT_BUILD_PROFILE="{profile_path.as_posix()}"' )

        with Timer(name='configure') as timer:
            stream_command(f'cmake {' '.join(filter(None, config_opts))}', dry=opts['dry'])
            print('')

        send()
        stats['configure'] = timer.get_dict()
        config['ok'] = timer.ok()


def build_cmake():
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    #[=================================[ Build ]=================================]
    import copy
    cmake = build['cmake']

    if config['ok'] and 'build' in build['verbs'] and 'build' in opts['build_actions']:
        h2("CMake Build")
        console.set_window_title('Build - {name}')

        build_path:Path = cmake['build_path']

        build_opts = [
            f'--build {build_path.as_posix()}',
            "--verbose" if not opts["quiet"] else None,
            f"-j {opts['jobs']}",
        ]
        build_opts += cmake.get("build_vars", [])

        with Timer(name='build') as timer:
            for target in cmake["targets"]:
                s2(f" Building target: {target} ")
                target_opts = copy.copy(build_opts)
                target_opts.append(f" --target {target}")

                if "tool_vars" in cmake:
                    target_opts.append('--')
                    target_opts += cmake["tool_vars"]

                stream_command(f'cmake {' '.join(filter(None, target_opts))}', dry=opts["dry"])
                print('')

        send()
        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()

# MARK: Configure
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ██████  ███    ██ ███████ ██  ██████  ██    ██ ██████  ███████    │
# │ ██      ██    ██ ████   ██ ██      ██ ██       ██    ██ ██   ██ ██         │
# │ ██      ██    ██ ██ ██  ██ █████   ██ ██   ███ ██    ██ ██████  █████      │
# │ ██      ██    ██ ██  ██ ██ ██      ██ ██    ██ ██    ██ ██   ██ ██         │
# │  ██████  ██████  ██   ████ ██      ██  ██████   ██████  ██   ██ ███████    │
# ╰────────────────────────────────────────────────────────────────────────────╯

def gen_scons( cfg:SimpleNamespace ) -> bool:
    cfg.verbs += ['check', 'build', 'clean']
    setattr(cfg, 'check_script', check_scons )
    setattr(cfg, 'build_script', build_scons )
    setattr(cfg, 'clean_script', clean_scons )

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
    cfg.verbs += ['check', 'configure', 'build']
    setattr(cfg, 'check_script', check_cmake )
    setattr(cfg, 'configure_script', configure_cmake )
    setattr(cfg, 'build_script', build_cmake )

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
        'source_script':source_git
    })

    # Host environment toolchain and build tools
    configs = expand_host_env( config_base, opts )
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

    for cfg in configs:
        cfg.verbs.append( 'test' )
        setattr(cfg, 'test_script', test_script )
        cfg.verbs.append( 'stats' )
        setattr(cfg, 'stats_script', stats_script )

        cfg.name.append( cfg.buildtool )
        cfg.source_dir.append( cfg.buildtool )

    for cfg in sorted( configs, key=lambda value: value.name ):
        if isinstance(cfg.name, list): cfg.name = '.'.join(cfg.name)
        if isinstance(cfg.source_dir, list): cfg.source_dir = '.'.join(cfg.source_dir)

        project.build_configs[cfg.name] = cfg

    return {project.name:project }