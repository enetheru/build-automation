import os
from types import SimpleNamespace
from share.expand_config import expand, expand_host_env, expand_cmake

from share.script_preamble import *

project_base = {
    'name':'orchestrator',
    'gitdef':{
        'url':"https://github.com/CraterCrash/godot-orchestrator.git/",
        'ref':'main'
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

def post_checkout():
    build:dict = {}
    # start_script

    #[============================[ Post-Checkout ]============================]
    from rich.panel import Panel

    # Update submodules
    with Section( "Update Submodules" ):
        worktree_path = build['source_path']
        os.chdir( worktree_path )
        orchestrator = git.Repo( worktree_path )
        orchestrator.git.submodule('update', '--init', '--recursive' )

        # engine = git.Repo( worktree_path / 'extern' / 'godot-engine'  )
        # print( Panel( engine.git.log( '-1'),  expand=False, title='godot-engine', title_align='left', width=120 ))

        godotcpp_path = worktree_path / 'extern' / 'godot-cpp'
        godotcpp = git.Repo( godotcpp_path )
        h(f'godot-cpp: {godotcpp_path.as_posix()}')

        godotcpp.git.checkout( 'master' )
        print( Panel( godotcpp.git.log( '-1'),  expand=False, title='godot-cpp', title_align='left', width=120 ))


# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___                       _                                              │
# │  / __|___ _ _  ___ _ _ __ _| |_ ___                                        │
# │ | (_ / -_) ' \/ -_) '_/ _` |  _/ -_)                                       │
# │  \___\___|_||_\___|_| \__,_|\__\___|                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ) -> dict:
    from share.snippets import source_git, show_stats, cmake_check, cmake_configure, cmake_build

    project_base.update({
        'path': opts.path / project_base['name'],
        "build_configs": {}
    })
    project = SimpleNamespace(**project_base)

    build_base = SimpleNamespace(**{
        'name' : 'name_will_be_replaced',
        'verbs':['source','configure', 'fresh', 'build'],
        'script_parts':[source_git, post_checkout, cmake_check, cmake_configure, cmake_build ],
        'godotcpp_profile':'extern/godot-cpp-profile.json',
        'cmake':{
            'targets':['orchestrator'],
        },
    })

    configs:list = expand_host_env( build_base, opts )
    configs:list = expand( configs, expand_cmake, 'Release' )

    for cfg in configs:
        cfg.script_parts += [show_stats]

        setattr(cfg, 'source_dir', f'{cfg.host}.{cfg.toolchain.name}')
        cfg.name = f'{cfg.host}.{cfg.toolchain.name}.{cfg.arch}.{cfg.cmake['gen']}.{cfg.cmake['build_type']}'
        cfg.cmake['build_dir'] = f'{cfg.cmake['gen']}.{cfg.cmake['build_type']}'

        if cfg.name in project.build_configs:
            h( f"[yellow]Skipping duplicate config name: {cfg.name}" )
            # TODO show the difference between the two dicts.
            continue
        project.build_configs[cfg.name] = cfg

    return {project.name: project}
