from share.script_imports import *

import copy
from types import SimpleNamespace
from share.expand_config import expand_host_env, expand

project_config = SimpleNamespace(**{
        'gitdef':{
            'url':"https://github.com/godotengine/godot.git/",
            'ref':'master'
        },
        "build_configs": {}
    }
)

# MARK: Scripts
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _                                                      │
# │ / __| __ _ _(_)_ __| |_ ___                                                │
# │ \__ \/ _| '_| | '_ \  _(_-<                                                │
# │ |___/\__|_| |_| .__/\__/__/                                                │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯
def scons_script():
    opts:dict = {}
    toolchain:dict = {}
    project:dict = {}
    build:dict = {}
    config:dict = {}
    # start_script
    # Scons Script
    from share.actions_git import git_checkout
    from share.actions_scons import scons_build

    ok = True

    def want( action:str ) -> bool:
        return (ok
                and action in build['verbs']
                and action in opts['build_actions'])

    stats:dict = dict()
    name = build['name']

    # Use a project wide build cache
    scons:dict = build['scons']
    scons_cache = project['path'] / 'scons_cache'
    scons['build_vars'].append(f'cache_path={scons_cache.as_posix()}')
    scons['build_vars'].append('cache_limit=16')

    # Update source_dir with git_short_hash to differentiate
    gitdef = build['gitdef'] = project['gitdef'] | build['gitdef'] # TODO | opts['gitdef']
    remote:str = gitdef.get('remote', '')
    gitref =  f'{remote}/{gitdef['ref']}' if remote else gitdef['ref']

    repo = git.Repo(project['path'] / 'git')
    short_hash = repo.git.rev_parse('--short', gitref)

    if remote or gitdef['ref'] != 'master':
        build['source_dir'] += f'.{short_hash}'

    gitdef['worktree_path'] = build['source_path'] = project['path'] / build['source_dir']

    profile_name = scons.get('build_profile', None)
    if profile_name:
        profile_path = project['path'] / 'build_profiles' / f'{profile_name}.py'
        scons['build_vars'].append(f'build_profile={profile_path.as_posix()}')

    #[=================================[ Fetch ]=================================]
    if want('source'):
        console.set_window_title(f'Source - {name}')
        with Timer(name='source') as timer:
            git_checkout( config )
        stats['source'] = timer.get_dict()
        ok = timer.ok()

    #[=================================[ Clean ]=================================]
    if want('clean'):
        console.set_window_title(f'Clean - {name}')
        print(figlet("SCons Clean", {"font": "small"}))

        with Timer(name='clean', push=False) as timer:
            try:
                proc = stream_command( "scons --clean" , dry=config['dry'])
                timer.status = TaskStatus.FAILED if proc.returncode else TaskStatus.COMPLETED
            except subprocess.CalledProcessError as e:
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

scons_script.verbs = ['source', 'clean', 'build']

# MARK: Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _                                                       │
# │  / __|___ _ _  / _(_)__ _ ___                                              │
# │ | (__/ _ \ ' \|  _| / _` (_-<                                              │
# │  \___\___/_||_|_| |_\__, /__/                                              │
# │                     |___/                                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

variations = ['default', 'double', 'tracy', 'tracy_debug', 'dev_build', 'minimum']

def filter_configs(  cfg:SimpleNamespace ) -> list:

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

    return [cfg]

def expand_variations( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant in variations:
        cfg = copy.deepcopy(config)

        setattr(cfg, 'variant', variant)
        cfg.name += f".{variant}"

        'extra_suffix=<something?>'

        match variant:
            case "default":
                pass

            case 'dev_build':
                cfg.scons['build_vars'].append('dev_build=yes')
                cfg.scons['build_vars'].append('separate_debug_symbols=yes')

            case 'minimum':
                cfg.scons['build_profile'] = 'minimum'
                cfg.scons['build_vars'].append('extra_suffix=min')

            case "double":
                # what's the point in using double precision on 32 bit architectures.
                if cfg.arch not in ['x86_64', 'arm64']: continue
                cfg.scons["build_vars"].append("precision=double")

            case 'tracy':
                setattr(cfg, 'gitdef', {
                    'remote':'enetheru',
                    'url':'https://github.com/enetheru/godot.git',
                    'ref':'4.4-tracy'
                })
                cfg.scons['build_vars'].append('extra_suffix=tracy')

            case 'tracy_debug':
                setattr(cfg, 'gitdef', {
                    'remote':'enetheru',
                    'url':'https://github.com/enetheru/godot.git',
                    'ref':'4.4-tracy'
                })
                cfg.scons['build_vars'].append('debug_symbols=yes')
                cfg.scons['build_vars'].append('separate_debug_symbols=yes')
                cfg.scons['build_vars'].append('extra_suffix=tracy.dbg')

            case _:
                print( f"skipping variant: {variant}" )
                continue

        configs_out.append( cfg )
    return configs_out

def generate_configs():

    config_base = SimpleNamespace(**{
        'name':'',
        'source_dir':'',
        'script':scons_script,
        'verbs':scons_script.verbs,
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
        'armv7': 'arm32',
        'armeabi-v7a': 'arm32',
        'arm64-v8a':'arm64',
        'aarch64':'arm64',
        'i686':'x86_32',
        'x86':'x86_32',
        'x86_32':'x86_32',
        'x86_64':'x86_64',
        'wasm32':'wasm32'
    }
    for cfg in configs:
        cfg.name = f'{cfg.host}.{cfg.toolchain.name}.{cfg.arch}'
        cfg.source_dir = f'{cfg.host}.{cfg.toolchain.name}'
        cfg.scons['build_vars'].append(f'platform={godot_platforms[cfg.platform]}')
        cfg.scons['build_vars'].append(f'arch={godot_arch[cfg.arch]}')

    configs = expand( configs, expand_variations )

    configs = expand( configs, filter_configs )
    
    for cfg in configs:
        project_config.build_configs[cfg.name] = cfg

generate_configs()
