import itertools
from copy import deepcopy
from types import SimpleNamespace

from share.snippets import cmake_build, cmake_check, cmake_configure


def expand( configs:list, func, *args ) -> list:
    configs_out:list = []
    for config in configs:
        if args: configs_out += func( config, *args )
        else: configs_out += func( config )
    return configs_out

# MARK: Platform
def expand_platform( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for platform in config.toolchain.platform:
        cfg = deepcopy(config)
        setattr( cfg, 'platform', platform )
        configs_out.append( cfg )
    return configs_out

# MARK: Arch
def expand_arch( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for arch in config.toolchain.arch:
        cfg = deepcopy(config)
        setattr( cfg, 'arch', arch )
        configs_out.append( cfg )
    return configs_out

# MARK: Toolchain
def expand_toolchains( config:SimpleNamespace, toolchains:dict ) -> list:
    configs_out:list = []
    for toolchain in toolchains.values():
        expander = getattr(toolchain, 'expand', None)

        if expander:
            cfg = deepcopy(config)
            setattr(cfg, 'toolchain', toolchain )
            configs_out += expander( cfg, toolchain )
            continue

        for arch, platform in itertools.product(toolchain.arch, toolchain.platform):
            cfg = deepcopy(config)
            setattr(cfg, 'toolchain', toolchain )
            setattr(cfg, 'arch', arch )
            setattr(cfg, 'platform', platform )
            configs_out.append( cfg )

    return configs_out

# # MARK: BuildTool
def expand_buildtool( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for buildtool in ['scons', 'cmake']: #TODO perhaps detect these
        cfg = deepcopy(config)
        setattr( cfg, 'buildtool', buildtool )
        configs_out.append( cfg )
    return configs_out

# MARK: CMake
cmake_config_types = {
    'Debug':'debug',
    "Release":'release',
    "RelWithDebInfo":'reldeb',
    # "MinSizeRel":'relmin',
}

cmake_generators = {
    'Visual Studio 17 2022':'msvc',
    'Ninja':'ninja',
    'Ninja Multi-Config':'ninja-multi',
    'MinGW Makefiles':'mingw',
}

def expand_cmake( config:SimpleNamespace ) -> list:
    match getattr(config, 'buildtool', None):
        case 'cmake':
            pass
        case None:
            setattr(config, 'buildtool', 'cmake' )
        case _:
            return []

    config.script_parts += [cmake_check, cmake_configure, cmake_build]
    config.verbs += ['configure', 'build']

    setattr( config, 'cmake', {
        'config_vars':['-DCMAKE_CXX_COMPILER_LAUNCHER=ccache'],
        'build_vars':[],
        'targets':[],
        'build_dir':'build-cmake',
    } | getattr( config, 'cmake', {}) )

    configs_out:list = []
    for config_type, generator in itertools.product(cmake_config_types, cmake_generators ):
        cfg = deepcopy(config)
        cmake = cfg.cmake
        cmake['config_type'] = config_type
        cmake['generator'] = generator

        short_gen = cmake_generators[generator]
        short_type = cmake_config_types[config_type]

        match short_gen:
            case 'msvc':
                if cfg.toolchain.name != short_gen: continue
                _A = {'x86_32':'Win32', 'x86_64':'x64', 'arm64':'ARM64'}
                cmake['config_vars'].append( f'-A {_A[cfg.arch]}')
                cmake['build_vars'].append(f'--config {config_type}')
                # cmake['tool_vars'] = ['-nologo', '-verbosity:normal', "-consoleLoggerParameters:'ShowCommandLine;ForceNoAlign'"]

            case 'ninja':
                cmake['config_vars'].append(f'-DCMAKE_BUILD_TYPE={config_type}')
                cmake['build_dir'] += f'-{short_type}'

            case 'ninja-multi':
                cmake['build_vars'].append(f'--config {config_type}')

            case 'mingw':
                if cfg.toolchain.name != 'mingw64': continue
                cmake['config_vars'].append(f'-DCMAKE_BUILD_TYPE={config_type}')
                cmake['build_dir'] += f'-{short_type}'
            case _:
                continue

        configs_out.append( cfg )
    return configs_out

def short_host() -> str:
    import sys
    bits = "64" if sys.maxsize > 2**32 else "32"
    return f'{sys.platform[0]}{bits}'

def expand_host_env( config:SimpleNamespace, opts:SimpleNamespace ) -> list:
    setattr( config, 'host', short_host() )

    configs_out = expand( [config], expand_toolchains, opts.toolchains )

    # configs_out = expand( configs_out, expand_buildtool )
    for config in configs_out:
        if not getattr(config, 'name', None):
            setattr(config, 'name', f'{config.host}.{config.toolchain.name}.{config.arch}.{config.platform}')

    return configs_out
