"""Terrain3D, a Godot extension built with SCons.

The library is written into the source tree. Upstream builds `template_debug`
(the default, used by the editor and debug exports) and `template_release`.
There is no `editor` target: both would write `libterrain.<platform>.debug.<arch>`,
and the project never passes `target=editor`. Each toolchain and target gets
its own worktree. `install` copies `project/addons/terrain_3d` into INSTALL_PREFIX.

    python cli.py --list -p ^terrain3d$
    python cli.py -p ^terrain3d$ -b mingw64\\.x86_64\\.windows\\.template_debug$ source build install
"""
import copy
from pathlib import Path
from types import SimpleNamespace

from share.snippets import show_stats, source_git
from src.config import (
    build_base,
    git_base,
    godot_arch,
    godot_platforms,
    gopts,
    project_base,
    scons_base,
)
from src.expand_config import expand_attr_list, expand_func, short_host


# The Godot project that receives addons/terrain_3d.
INSTALL_PREFIX = Path('C:/Godot/Projects/tokisan-demo')
ADDON_REL = 'project/addons/terrain_3d'

# template_debug is the library the editor loads. template_release is the export.
TARGETS = ('template_release', 'template_debug')


def generate(opts: SimpleNamespace) -> SimpleNamespace:
    git_source = SimpleNamespace({**vars(git_base), **{
        'name': 'origin',
        'url': 'https://github.com/TokisanGames/Terrain3D.git',
        'ref': 'main',
    }})
    project = SimpleNamespace({**vars(project_base), **{
        'name': 'terrain3d',
        'verbs': ['fetch'],
        'sources': {'origin': git_source},
        'buildtools': {
            'scons': SimpleNamespace({**vars(scons_base), **{
                'expand': expand_scons,
            }}),
        },
    }})
    # project_base keeps the toolchain view from before -t filters it.
    project.toolchains = gopts.toolchains.values()

    build_start = SimpleNamespace({**vars(build_base), **{
        'verbs': ['source'],
        'script_parts': [source_git, init_submodules],
        'source_def': git_source,
    }})

    builds = expand_func(
        [build_start], expand_attr_list, 'toolchain', list(opts.toolchains.values()))

    # generic_toolchain_expand records the pair on the toolchain.
    # Android's expand records the ABI on the build and leaves the pair unset.
    for build in builds:
        toolchain = build.toolchain
        if hasattr(toolchain, 'target_arch'):
            build.arch = toolchain.target_arch
            build.platform = toolchain.target_platform

    builds = expand_func(
        builds, expand_attr_list, 'buildtool', list(project.buildtools.values()))

    builds = [
        build for build in builds
        if all(fn(build) for fn in getattr(build, 'configure_funcs', []))
    ]

    host = short_host()
    for build in builds:
        raw_platform = build.platform
        platform_name = None
        if raw_platform not in ('android', 'emscripten'):
            platform_name = godot_platforms.get(raw_platform, raw_platform)
        arch_name = None if raw_platform == 'emscripten' else build.arch
        build.name = '.'.join(filter(None, [
            host,
            build.toolchain.name,
            arch_name,
            platform_name,
            build.target,
        ]))
        build.host = host
        build.source_dir = build.name
        build.install_prefix = INSTALL_PREFIX
        build.addon_rel = ADDON_REL
        build.verbs = list(build.verbs) + ['install']
        build.script_parts = list(build.script_parts) + [install_scons, show_stats]

    project.build_configs = {build.name: build for build in builds}
    return project


def expand_scons(config: SimpleNamespace) -> list[SimpleNamespace]:
    """One row per Godot target, with the compiler flags that target needs."""
    raw_platform = getattr(config, 'platform', None)
    raw_arch = getattr(config, 'arch', None)
    platform = godot_platforms.get(raw_platform)
    arch = godot_arch.get(raw_arch)
    if not platform or not arch:
        return []

    flags = ['compiledb=yes', f'platform={platform}', f'arch={arch}']
    match config.toolchain.name:
        case 'msvc' | 'android' | 'emscripten' | 'appleclang' | 'gcc':
            pass
        case 'llvm':
            if raw_arch != 'x86_64':
                return []
            flags.append('use_llvm=yes')
        case 'llvm-mingw':
            flags += [
                'use_mingw=yes',
                'use_llvm=yes',
                f'mingw_prefix={config.toolchain.sysroot.as_posix()}',
            ]
        case 'mingw64':
            flags += [
                'use_mingw=yes',
                f'mingw_prefix={config.toolchain.sysroot.as_posix()}',
            ]
        case 'msys2-clang64':
            flags += ['use_mingw=yes', 'use_llvm=yes']
        case 'msys2-ucrt64' | 'msys2-mingw64' | 'msys2-mingw32':
            flags.append('use_mingw=yes')
        case _:
            return []

    config.verbs += ['clean', 'build']
    config.script_parts += [check_scons, clean_scons, build_scons]

    configs_out = []
    for target in TARGETS:
        cfg = copy.deepcopy(config)
        cfg.target = target
        scons = cfg.buildtool
        scons.target = target
        scons.build_dir = ''
        scons.build_vars = list(scons.build_vars) + flags + [f'target={target}']
        configs_out.append(cfg)
    return configs_out


def init_submodules():
    config: dict = {}
    opts: dict = {}
    build: dict = {}
    stats: dict = {}
    # start_script

    # godot-cpp is a submodule. The parent checkout does not contain it.
    if config['ok'] and 'source' in opts['build_actions']:
        with fmt.Section('Submodules'), Timer(name='submodules') as timer:
            source = Path(build['source_path'])
            if not source.is_dir():
                if not opts['dry']:
                    fmt.h(f'ERROR: no source worktree at {source.as_posix()}')
                    timer.status = TaskStatus.FAILED
            else:
                os.chdir(source)
            if timer.ok():
                stream_command(
                    ['git', 'submodule', 'update', '--init', '--', 'godot-cpp'],
                    dry=opts['dry'])
        stats['submodules'] = timer.get_dict()
        config['ok'] = timer.ok()


def check_scons():
    project: dict = {}
    build: dict = {}
    buildtool: dict = {}
    # start_script

    scons = buildtool
    rel = scons.get('build_dir') or ''
    build_path = project['path'] / build['source_dir']
    if rel:
        build_path = build_path / rel
    scons['build_path'] = build_path

    try:
        os.chdir(build_path)
    except FileNotFoundError as missing:
        missing.add_note(f'Missing folder {build_path}')
        raise missing

    if not (build_path / 'SConstruct').exists():
        missing = FileNotFoundError()
        missing.add_note(f'Missing SConstruct in {build_path}')
        raise missing


def clean_scons():
    config: dict = {}
    opts: dict = {}
    build: dict = {}
    stats: dict = {}
    buildtool: dict = {}
    # start_script

    if config['ok'] and 'clean' in opts['build_actions']:
        console.set_window_title(f'Clean - {build["name"]}')
        with fmt.Section('SCons Clean'), Timer(name='clean') as timer:
            os.chdir(buildtool['build_path'])
            stream_command(
                ['scons', '--clean', '-s', *buildtool.get('build_vars', [])],
                dry=opts['dry'])
        stats['clean'] = timer.get_dict()
        config['ok'] = timer.ok()


def build_scons():
    config: dict = {}
    opts: dict = {}
    build: dict = {}
    stats: dict = {}
    buildtool: dict = {}
    # start_script

    if config['ok'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build["name"]}')
        with fmt.Section('SCons Build'), Timer(name='build') as timer:
            os.chdir(buildtool['build_path'])
            jobs = opts['jobs']
            cmd = ['scons']
            if jobs > 0:
                cmd.append(f'-j{jobs}')
            if opts['verbose']:
                cmd.append('verbose=yes')
            cmd.extend(buildtool.get('build_vars', []))
            stream_command(cmd, dry=opts['dry'])
        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()


def install_scons():
    config: dict = {}
    opts: dict = {}
    build: dict = {}
    stats: dict = {}
    # start_script

    # Copies the addon, including the library this worktree just built.
    if config['ok'] and 'install' in opts['build_actions']:
        console.set_window_title(f'Install - {build["name"]}')
        with fmt.Section('Install'), Timer(name='install') as timer:
            import shutil
            source = (Path(build['source_path']) / build['addon_rel']).resolve()
            dest = (Path(build['install_prefix']).expanduser().resolve()
                    / 'addons' / source.name)
            fmt.h(f'Destination: {dest.as_posix()}')
            if dest == source or source in dest.parents or dest in source.parents:
                fmt.h(f'ERROR: install path {dest.as_posix()} overlaps the source tree')
                timer.status = TaskStatus.FAILED
            elif not source.is_dir() and not opts['dry']:
                fmt.h(f'ERROR: missing addon at {source.as_posix()}')
                timer.status = TaskStatus.FAILED
            elif not opts['dry']:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source, dest, dirs_exist_ok=True)
        stats['install'] = timer.get_dict()
        config['ok'] = timer.ok()
