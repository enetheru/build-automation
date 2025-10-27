from types import SimpleNamespace

from share.expand_config import expand_func, expand_host_env, expand_cmake, expand_toolchains
from share.format import h, Section

from share.script_preamble import *

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___                       _                                              │
# │  / __|___ _ _  ___ _ _ __ _| |_ ___                                        │
# │ | (_ / -_) ' \/ -_) '_/ _` |  _/ -_)                                       │
# │  \___\___|_||_\___|_| \__,_|\__\___|                                       │
# ╰────────────────────────────────────────────────────────────────────────────╯
def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    from share.snippets import source_git, show_stats, cmake_check, cmake_configure, cmake_build
    from share.config import project_base, build_base, cmake_base

    from share.config import git_base
    project = SimpleNamespace({ **vars(project_base), **{
        'name': 'orchestrator',
        'sources':{
            'git': SimpleNamespace({**vars(git_base), **{
                'url': "https://github.com/CraterCrash/godot-orchestrator.git/",
                'ref': 'main'
            }}),
        },
    }})

    return project

    build_base = SimpleNamespace({ **vars(build_base), **{
        'verbs':['source','configure', 'fresh', 'build'],
        'script_parts':[source_git, post_checkout, cmake_check, cmake_configure, cmake_build ],
        'godotcpp_profile':'extern/godot-cpp-profile.json',
        'buildtool': SimpleNamespace({ **vars(cmake_base), **{
            'targets':['orchestrator'],
        }}),
    }})

    # configs:list = expand_host_env( build_base, project )
    builds:list[SimpleNamespace] = expand_func([build_base], expand_cmake )
    configs = expand_func( builds, expand_toolchains, project )

    for cfg in configs:
        cfg.script_parts += [show_stats]

        setattr(cfg, 'source_dir', f'{cfg.host}.{cfg.toolchain.name}')
        # short_type = cmake_config_types[cfg.cmake['config_type']]
        # short_gen = cmake_generators[cfg.cmake['generator']]
        # cfg.name = f'{cfg.host}.{cfg.toolchain.name}.{cfg.arch}.{short_gen}.{short_type}'
        # cfg.cmake['build_dir'] = f'{short_gen}.{short_type}'

        if cfg.name in project.build_configs:
            h( f"[yellow]Skipping duplicate config name: {cfg.name}" )
            # TODO show the difference between the two dicts.
            continue
        project.build_configs[cfg.name] = cfg


    return project

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

