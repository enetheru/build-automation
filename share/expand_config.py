import itertools
from copy import deepcopy
from types import SimpleNamespace

from share.config import gopts
from share.snippets import cmake_build, cmake_check, cmake_configure

def expand_func( configs_in:list[SimpleNamespace], func, *args ) -> list:
    configs_out:list = []
    for cfg in configs_in:
        if args: configs_out += func(cfg, *args)
        else: configs_out += func(cfg)
    return configs_out


def expand_list( configs_in:list[SimpleNamespace], prop:str, items:list ) -> list:
    configs_out:list = []
    for cfg, item in itertools.product(configs_in, items):
        cfg = deepcopy(cfg)
        setattr(cfg, prop, item )
        configs_out.append( cfg )
    return configs_out


def expand_buildtools( config_in:SimpleNamespace, project:SimpleNamespace ) -> list:
    configs_out:list = []
    for tool in project.buildtools.keys():
        cfg = deepcopy(config_in)
        setattr(cfg, 'buildtool', project.buildtools[tool])
        configs_out.append(cfg)
    return configs_out


# MARK: Toolchain
def expand_toolchains( cfg:SimpleNamespace ) -> list:
    configs_out:list = []
    for toolchain in gopts.toolchains.values():
        toolchain_expand = getattr(toolchain, 'expand', None)

        if toolchain_expand:
            cfg = deepcopy(cfg)
            setattr(cfg, 'toolchain', toolchain )
            configs_out += cfg.toolchain.expand( cfg )
            continue

        for arch, platform in itertools.product(toolchain.arch, toolchain.platform):
            cfg = deepcopy(cfg)
            setattr(cfg, 'toolchain', toolchain )
            setattr(cfg, 'arch', arch )
            setattr(cfg, 'platform', platform )
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
    if config.buildtool.name != 'cmake': return [config]

    config.verbs += ['configure', 'build']
    config.script_parts += [cmake_check, cmake_configure, cmake_build]



    # config.cmake['config_vars'] += ['-DCMAKE_CXX_COMPILER_LAUNCHER=ccache']

    configs_out:list = []
    for config_type, generator in itertools.product(cmake_config_types, cmake_generators ):
        cfg = deepcopy(config)
        cmake = cfg.buildtool
        cmake.config_type = config_type
        cmake.generator = generator

        short_gen = cmake_generators[generator]
        short_type = cmake_config_types[config_type]

        match short_gen:
            case 'msvc':
                if cfg.toolchain.name != short_gen: continue
                _A = {'x86_32':'Win32', 'x86_64':'x64', 'arm64':'ARM64'}
                cmake.config_vars.append( f'-A {_A[cfg.arch]}')
                cmake.build_vars.append(f'--config {config_type}')
                # cmake['tool_vars'] = ['-nologo', '-verbosity:normal', "-consoleLoggerParameters:'ShowCommandLine;ForceNoAlign'"]

            case 'ninja':
                cmake.config_vars.append(f'-DCMAKE_BUILD_TYPE={config_type}')
                cmake.build_dir += f'-{short_type}'

            case 'ninja-multi':
                cmake.build_vars.append(f'--config {config_type}')

            case 'mingw':
                if cfg.toolchain.name != 'mingw64': continue
                cmake.config_vars.append(f'-DCMAKE_BUILD_TYPE={config_type}')
                cmake.build_dir += f'-{short_type}'
            case _:
                continue

        configs_out.append( cfg )
    return configs_out

def short_host() -> str:
    import sys
    bits = "64" if sys.maxsize > 2**32 else "32"
    return f'{sys.platform[0]}{bits}'


def expand_host_env( config:SimpleNamespace, project:SimpleNamespace ) -> list:
    setattr( config, 'host', short_host() )

    configs_out = expand_func( [config], expand_buildtools, project )

    configs_out = expand_func( configs_out, expand_toolchains )

    for config in configs_out:
        if not getattr(config, 'name', None):
            setattr(config, 'name', f'{config.host}.{config.buildtool}.{config.toolchain.name}')

    return configs_out
