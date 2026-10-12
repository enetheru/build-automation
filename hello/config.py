"""Local hello-world used to exercise host, toolchain, platform, arch, generator, config type, and one option.

Filter so the rest of the tree is left alone:

    python cli.py --list -p ^hello$
    python cli.py -p ^hello$ -b "debug-ninja\\.llvm\\.x86_64\\.windows$" build test

`plain` prints "hello, world". `shout` passes -DHELLO_SHOUT=ON and prints "HELLO, WORLD".
The binary also prints the config name, compiler id, system, and processor.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from share.snippets import show_stats
from src.config import build_base, cmake_base, godot_platforms, project_base
from src.expand_config import expand_attr_list, expand_cmake, expand_func, short_host


def generate(opts: SimpleNamespace) -> SimpleNamespace:
    local = SimpleNamespace(name='local', type='local', verbs=[])

    project = SimpleNamespace({**vars(project_base), **{
        'name': 'hello',
        'verbs': [],
        'sources': {'local': local},
        'buildtools': {
            'cmake': SimpleNamespace({**vars(cmake_base), **{
                'targets': ['hello'],
                'config_vars': [],
                'build_vars': [],
                'expand': expand_cmake,
                'configure': configure_hello,
            }}),
        },
    }})

    builds: list[SimpleNamespace] = expand_func(
        [build_base], expand_attr_list, 'source_def', [local])

    builds = expand_func(
        builds, expand_attr_list, 'toolchain', list(opts.toolchains.values()))

    # generic_toolchain_expand records the pair on the toolchain.
    # expand_cmake and the mingw processor flag read build.arch.
    for build in builds:
        toolchain = build.toolchain
        if hasattr(toolchain, 'target_arch'):
            build.arch = toolchain.target_arch
            build.platform = toolchain.target_platform

    builds = expand_func(
        builds, expand_attr_list, 'buildtool', list(project.buildtools.values()))

    builds = expand_func(builds, expand_variations)

    builds = [
        build for build in builds
        if all(fn(build) for fn in getattr(build, 'configure_funcs', []))
    ]

    host = short_host()
    for build in builds:
        toolchain = build.toolchain
        buildtool = build.buildtool
        platform = getattr(build, 'platform', None)
        arch = getattr(build, 'arch', None)

        platform_name = None
        if platform not in ('android', 'emscripten'):
            platform_name = godot_platforms.get(platform, platform)

        name_parts = [
            host,
            f'{buildtool.name}-{buildtool.short_type}-{buildtool.short_gen}',
            toolchain.name,
            arch if platform != 'emscripten' else None,
            platform_name,
            build.variant if build.variant != 'plain' else None,
        ]
        build.name = '.'.join(filter(None, name_parts))
        build.host = host
        build.source_dir = Path('.')
        build.verbs = list(build.verbs) + ['test']
        buildtool.build_dir = build.name
        buildtool.config_vars.append(f'-DHELLO_BUILD_NAME={build.name}')
        build.script_parts = list(build.script_parts) + [test_hello, show_stats]

    project.build_configs = {build.name: build for build in builds}
    return project


def configure_hello(build: SimpleNamespace) -> bool:
    """Keep CMake configs. Emscripten stores its toolchain file as a one-element tuple."""
    tool = build.buildtool
    if getattr(tool, 'name', None) != 'cmake':
        return False

    toolchain_file = getattr(tool, 'toolchain', None)
    if isinstance(toolchain_file, tuple):
        if len(toolchain_file) != 1:
            return False
        tool.toolchain = toolchain_file[0]
    return True


def expand_variations(build: SimpleNamespace) -> list[SimpleNamespace]:
    kept = []
    for label, accept in variations.items():
        variant = deepcopy(build)
        variant.variant = label
        if accept(variant):
            kept.append(variant)
    return kept


def configure_shout(build: SimpleNamespace) -> bool:
    build.buildtool.config_vars.append('-DHELLO_SHOUT=ON')
    return True


variations = {
    'plain': lambda build: True,
    'shout': configure_shout,
}


def test_hello():
    config: dict = {}
    opts: dict = {}
    build: dict = {}
    stats: dict = {}
    buildtool: dict = {}
    # start_script

    if config['ok'] and 'test' in opts['build_actions']:
        with fmt.Section('Test'):
            console.set_window_title(f"Test - {build['name']}")
            build_path = Path(buildtool['build_path'])
            config_type = buildtool.get('config_type')
            candidates = []
            for name in ('hello.exe', 'hello'):
                candidates.append(build_path / name)
                if config_type:
                    candidates.append(build_path / config_type / name)

            exe = next((path for path in candidates if path.is_file()), None)
            if exe is None:
                fmt.h(f'No hello binary under {build_path.as_posix()}')
                config['ok'] = False
            else:
                expected = 'HELLO, WORLD' if str(build['name']).endswith('.shout') else 'hello, world'
                lines = []

                def collect(line):
                    lines.append(line)
                    print(line)

                with Timer(name='test') as timer:
                    stream_command(f'"{exe.as_posix()}"', dry=opts['dry'], stdout_handler=collect)
                    got = lines[0] if lines else ''
                    if not opts['dry'] and got != expected:
                        fmt.h(f'expected {expected!r}, got {got!r}')
                        timer.status = TaskStatus.FAILED
                        config['ok'] = False

                stats['test'] = timer.get_dict()
                config['ok'] = timer.ok() and config['ok']
