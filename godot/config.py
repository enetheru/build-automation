import copy
from types import SimpleNamespace

from share.expand_config import expand_host_env, expand
from share.script_preamble import *

project_base:dict = {
    'name':'godot',
    'gitdef':{
        'url':"https://github.com/godotengine/godot.git/",
        'ref':'master'
    }
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
    stats:dict = {}
    # start_script

    #[=================================[ Source ]=================================]
    from share.actions_git import git_checkout

    repo = git.Repo(project['path'] / 'git')

    if config['ok'] and 'source' in build['verbs'] and 'source' in opts['build_actions']:
        console.set_window_title(f'Source - {build['name']}')

        # if we have specified a different git repository than expected, add the shorthash to the name.
        gitdef = build['gitdef'] = project['gitdef'] | build['gitdef'] | opts['gitdef']
        remote:str = gitdef.get('remote', '')
        gitref =  f'{remote}/{gitdef['ref']}' if remote else gitdef['ref']

        if opts['gitdef']:
            short_hash = repo.git.rev_parse('--short', gitref)
            build['source_dir'] += f'.{short_hash}'

        gitdef['worktree_path'] = build['source_path'] = project['path'] / build['source_dir']

        with Timer(name='source') as timer:
            git_checkout( config )
        stats['source'] = timer.get_dict()
        config['ok'] = timer.ok()

    if not opts['quiet']:
        print( repo.git.log('-1') )

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

def clean_scons():
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    build:dict = {}
    # start_script
    from subprocess import CalledProcessError

    #[=================================[ Clean ]=================================]
    if config['ok'] and 'clean' in build['verbs'] and 'clean' in opts['build_actions']:
        console.set_window_title(f'Clean - {build['name']}')
        print(h2("SCons Clean"))

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

def build_scons():
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    project:dict = {}
    build:dict = {}
    # start_script

    #[=================================[ Build ]=================================]
    from share.actions_scons import scons_build
    scons:dict = build['scons']

    if config['ok'] and 'build' in build['verbs'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')

        profile_name = scons.get('build_profile', None)
        if profile_name:
            profile_path = project['path'] / f'build_profiles/{profile_name}.py'
            scons['build_vars'].append(f'build_profile="{profile_path.as_posix()}"')

        with Timer(name='build') as timer:
            scons_build( config )
        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()

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
def config_double( cfg:SimpleNamespace ) -> bool:
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.scons["build_vars"].append("precision=double")
    return True
variations['double'] = config_double

# MARK: dev_build
def config_dev( cfg:SimpleNamespace ) -> bool:
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.scons['build_vars'].append('dev_build=yes')
    cfg.scons['build_vars'].append('separate_debug_symbols=yes')
    return True

variations['dev_build'] = config_dev

def config_minim( cfg:SimpleNamespace ) -> bool:
    cfg.scons['build_profile'] = 'minimum'
    cfg.scons['build_vars'].append('extra_suffix=min')
    return True

variations['minimum'] = config_minim

def tracy_script():
    # start_script

    #[=================================[ Tracy ]=================================]
    # TODO implement the necessary details to fetch the submodules
    print( "TODO implement the necessary details to fetch the submodules" )
    exit(1)

def config_tracy( cfg:SimpleNamespace ) -> bool:
    cfg.verbs.append( 'tracy' )
    setattr(cfg, 'tracy_script', tracy_script )

    setattr(cfg, 'gitdef', {
        'remote':'enetheru',
        'url':'https://github.com/enetheru/godot.git',
        'ref':'4.4-tracy'
    })
    cfg.source_dir.append( 'tracy' )
    cfg.scons['build_vars'].append('extra_suffix=tracy')
    return True

variations['tracy'] = config_tracy

def config_tracy_dbg( cfg:SimpleNamespace ) -> bool:
    cfg.verbs.append( 'tracy' )
    setattr(cfg, 'tracy_script', tracy_script )

    setattr(cfg, 'gitdef', {
        'remote':'enetheru',
        'url':'https://github.com/enetheru/godot.git',
        'ref':'4.4-tracy'
    })
    cfg.source_dir.append( 'tracy' )
    cfg.scons['build_vars'].append('debug_symbols=yes')
    cfg.scons['build_vars'].append('separate_debug_symbols=yes')
    cfg.scons['build_vars'].append('extra_suffix=tracy.dbg')
    return True

variations['tracy_debug'] = config_tracy_dbg

# MARK: Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _                                                       │
# │  / __|___ _ _  / _(_)__ _ ___                                              │
# │ | (__/ _ \ ' \|  _| / _` (_-<                                              │
# │  \___\___/_||_|_| |_\__, /__/                                              │
# │                     |___/                                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def config_toolchains( cfg:SimpleNamespace ) -> SimpleNamespace:
    match cfg.toolchain.name:
        case "llvm":
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "llvm-mingw" | "msys2-clang64":
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            cfg.scons["build_vars"].append("use_mingw=yes")

        case 'appleclang':
            cfg.scons['build_vars'].append('generate_bundle=yes')

    return cfg

def expand_variations( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant, config_func in variations.items():
        cfg = copy.deepcopy(config)

        setattr(cfg, 'variant', variant)
        cfg.name.append( variant )

        if config_func( cfg ): # Only keep variants who's configuration step succeeds.
            configs_out.append( cfg )

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
        "build_configs": {}
    })
    project = SimpleNamespace(**project_base)

    config_base = SimpleNamespace(**{
        'name':[],
        'variant':'null',
        'source_dir':[],
        'verbs':['source', 'check'],
        'source_script':source_git,
        'check_script':check_scons,

        "scons": {
            "targets": ["template_release", "template_debug", "editor"],
            "build_vars":["compiledb=yes"]
        }
    })

    configs = expand_host_env( config_base )
    godot_platforms = {
        'android':'android',
        'darwin':'macos',
        'emscripten':'web',
        'ios':'ios',
        'linux':'linux',
        'win32':'windows'
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
    for cfg in configs:
        cfg.name = [cfg.host, cfg.toolchain.name, cfg.arch]
        cfg.source_dir = [cfg.host, cfg.toolchain.name]
        cfg.scons['build_vars'].append(f'platform={godot_platforms[cfg.platform]}')
        cfg.scons['build_vars'].append(f'arch={godot_arch[cfg.arch]}')

    configs = expand( configs, expand_variations )

    configs = filter( None, [config_toolchains(cfg) for cfg in configs] )
    
    for cfg in configs:
        cfg.verbs.append( 'build' )
        setattr(cfg, 'build_script', build_scons )

        cfg.verbs.append( 'clean' )
        setattr(cfg, 'clean_script', clean_scons )

        cfg.verbs.append( 'stats' )
        setattr(cfg, 'stats_script', stats_script )

        if isinstance(cfg.name, list): cfg.name = '.'.join(cfg.name)
        if isinstance(cfg.source_dir, list): cfg.source_dir = '.'.join(cfg.source_dir)
        project.build_configs[cfg.name] = cfg

    return {project.name:project}
