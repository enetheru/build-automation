"""Local hello-world used to exercise host, toolchain, platform, arch, generator, config type, and one option.

Filter so the rest of the tree is left alone:

    python cli.py --list -p ^hello$
    python cli.py -p ^hello$ -b "debug-ninja\\.llvm\\.x86_64\\.windows$" build test

`plain` prints "hello, world". `shout` passes -DHELLO_SHOUT=ON and prints "HELLO, WORLD".
The binary also prints the config name, compiler id, system, and processor.
`test` runs only when this host can execute that platform and architecture.
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
        build.can_test = host_can_run(getattr(build, 'platform', ''), getattr(build, 'arch', ''))
        build.verbs = list(build.verbs) + ['test']
        buildtool.build_dir = build.name
        buildtool.config_vars.append(f'-DHELLO_BUILD_NAME={build.name}')
        build.script_parts = list(build.script_parts) + [test_hello, show_stats]

    project.build_configs = {build.name: build for build in builds}
    return project


def host_can_run(target_platform: str, target_arch: str) -> bool:
    """True when this machine can execute a binary for that platform and architecture.

    Windows x64 can run 32-bit x86. Windows on ARM and Apple Silicon can run
    the emulated architectures those operating systems provide. Anything else,
    including Android and Emscripten, is not executed here.
    """
    import platform
    import sys

    arch_names = {
        'amd64': 'x86_64',
        'x64': 'x86_64',
        'x86_64': 'x86_64',
        'i686': 'x86',
        'i386': 'x86',
        'x86': 'x86',
        'x86_32': 'x86',
        'aarch64': 'arm64',
        'arm64': 'arm64',
        'arm64-v8a': 'arm64',
        'armv7': 'arm32',
        'armv32': 'arm32',
        'armeabi-v7a': 'arm32',
        'wasm32': 'wasm32',
        'wasm64': 'wasm64',
    }
    host_os = sys.platform
    native_platforms = {
        'win32': {'win32', 'windows'},
        'darwin': {'darwin', 'macos'},
        'linux': {'linux'},
    }.get(host_os, set())
    if str(target_platform).lower() not in native_platforms:
        return False

    host_arch = arch_names.get(platform.machine().lower(), platform.machine().lower())
    target = arch_names.get(str(target_arch).lower(), str(target_arch).lower())
    runnable = {host_arch}
    if host_os == 'win32' and host_arch == 'x86_64':
        runnable.add('x86')
    elif host_os == 'win32' and host_arch == 'arm64':
        runnable.update({'x86_64', 'x86'})
    elif host_os == 'darwin' and host_arch == 'arm64':
        runnable.add('x86_64')
    return target in runnable


def configure_hello(build: SimpleNamespace) -> bool:
    return getattr(build.buildtool, 'name', None) == 'cmake'


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
            if not build.get('can_test'):
                fmt.h(f"Skip test: host cannot run {build.get('platform')} {build.get('arch')}")
            else:
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
