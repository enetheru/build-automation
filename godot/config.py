#!/usr/bin/env python
import copy
from types import SimpleNamespace
import rich
from share.expand_config import expand_host_env, expand
from share.format import *
from share.run import stream_command

project_config = SimpleNamespace(
    **{"gitUrl": "https://github.com/godotengine/godot.git/", "build_configs": {}}
    # TODO Update Verbs
)


# MARK: Scripts
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___         _      _                                                      │
# │ / __| __ _ _(_)_ __| |_ ___                                                │
# │ \__ \/ _| '_| | '_ \  _(_-<                                                │
# │ |___/\__|_| |_| .__/\__/__/                                                │
# │               |_|                                                          │
# ╰────────────────────────────────────────────────────────────────────────────╯

def scons_script( config:dict, console:rich.console.Console ):
    from share.Timer import Timer, TaskStatus
    from share.actions import git_checkout, scons_build

    ok = True

    def want( action:str ) -> bool:
        return (ok
                and action in config['verbs']
                and action in config['actions'])

    stats:dict = dict()
    name = config['name']

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

variations = ['default', 'double']

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

        match variant:
            case "default":
                pass

            case "double":
                # what's the point in using double precision on 32 bit architectures.
                if cfg.arch not in ['x86_64', 'arm64']: continue

                cfg.name += f".{variant}"
                cfg.scons["build_vars"].append("precision=double")

            case _:
                print( f"skipping variant: {variant}" )
                continue

        configs_out.append( cfg )
    return configs_out

def generate_configs():
    config_base = SimpleNamespace(**{
        'name':'',
        'script':scons_script,
        'verbs':scons_script.verbs,
        "scons": {
            "targets": ["template_release", "template_debug", "editor"],
            "build_vars":["compiledb=yes"]
        }
    })

    configs = expand_host_env( config_base )
    for cfg in configs:
        cfg.name = f'{cfg.host}.{cfg.toolchain.name}.{cfg.arch}'
        cfg.scons['build_vars'].append(f'platform={cfg.platform}')
        cfg.scons['build_vars'].append(f'arch={cfg.arch}')

    configs = expand( configs, expand_variations )

    configs = expand( configs, filter_configs )
    
    for cfg in configs:
        project_config.build_configs[cfg.name] = cfg

generate_configs()
