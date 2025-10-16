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


def expand_sourcedefs( config_in:SimpleNamespace, project:SimpleNamespace ) -> list:
    configs_out:list[SimpleNamespace] = []
    for srcdef in project.sources.values():
        cfg = deepcopy(config_in)

        cfg.source_def = srcdef

        if hasattr( srcdef, 'configure' ):
            srcdef.configure(cfg)

        if hasattr( srcdef, 'expand' ):
            configs_out += expand_func([cfg], srcdef.expand)
            continue

        configs_out.append( cfg )
    return configs_out


def expand_buildtools( config_in:SimpleNamespace, project:SimpleNamespace ) -> list:
    configs_out:list = []
    for tool in project.buildtools.keys():
        cfg = deepcopy(config_in)

        buildtool : SimpleNamespace = project.buildtools[tool]
        setattr(cfg, 'buildtool', buildtool)

        if hasattr( buildtool, 'configure' ):
            buildtool.configure(cfg)

        if hasattr( buildtool, 'expand' ):
            configs_out += expand_func([cfg], buildtool.expand)
            continue

        configs_out.append(cfg)

    return configs_out


# MARK: Toolchain
def expand_toolchains( cfg:SimpleNamespace, project:SimpleNamespace ) -> list:
    configs_out:list = []
    for toolchain in project.toolchains:

        # The toolchain itself might have an expander function for variations.
        if hasattr(toolchain, 'expand'):
            cfg = deepcopy(cfg)
            setattr(cfg, 'toolchain', toolchain )
            configs_out += expand_func([cfg], getattr(toolchain, 'expand'))
            continue

        # else
        for arch, platform in itertools.product(toolchain.arch, toolchain.platform):
            cfg = deepcopy(cfg)
            setattr(cfg, 'toolchain', toolchain )
            setattr(cfg, 'arch', arch )
            setattr(cfg, 'platform', platform )
            configs_out.append( cfg )

    return configs_out


def expand_cmake( config:SimpleNamespace ) -> list:
    if config.buildtool.name != 'cmake':
        if gopts.debug: raise Exception("Expansion of cmake for non cmake build")
        return [config]

    config.verbs += ['configure', 'build']
    config.script_parts += [cmake_check, cmake_configure, cmake_build]

    toolchain = config.toolchain

    # config.cmake['config_vars'] += ['-DCMAKE_CXX_COMPILER_LAUNCHER=ccache']
    cmake_base = config.buildtool
    config_types = cmake_base.config_types
    generators = cmake_base.generators
    targets = cmake_base.targets

    configs_out:list = []
    for ctype_key, generator_key, target in itertools.product(config_types, generators, targets ):
        config_type = config_types[ ctype_key ]
        generator = generators[generator_key]

        # Handle exclusionary cases
        match generator_key:
            case 'msvc':
                # skip visual studio generator with toolchains that are not msvc
                if toolchain.name != generator_key: continue

        cfg = deepcopy(config)
        cmake = cfg.buildtool

        # Now we have selected these items, we dont need their options lists on the copied objects.
        delattr(cmake, 'generators')
        delattr(cmake, 'config_types')
        delattr(cmake, 'targets')


        cmake.config_type = config_type
        cmake.generator = generator
        cmake.target = target
        setattr(cmake, 'short_gen', generator_key)
        setattr(cmake, 'short_type', ctype_key)

        cmake.config_vars.append( f'--debug-output')
        cmake.config_vars.append( f'--debug-trycompile')
        cmake.config_vars.append( f'--fresh')
        # cmake.config_vars.append( f'--trace')



        match generator_key:
            case 'msvc':
                _A = {'x86_32':'Win32', 'x86_64':'x64', 'arm64':'ARM64'}
                cmake.config_vars.append( f'-A {_A[cfg.arch]}')
                cmake.build_vars.append(f'--config {config_type}')
                # cmake['tool_vars'] = ['-nologo', '-verbosity:normal', "-consoleLoggerParameters:'ShowCommandLine;ForceNoAlign'"]

            case 'ninja':
                cmake.config_vars.append(f'-DCMAKE_BUILD_TYPE={config_type}')

            case 'ninja-multi':
                cmake.build_vars.append(f'--config {config_type}')

            case 'mingw':
                if toolchain.name != 'mingw64': continue
                cmake.config_vars.append(f'-DCMAKE_BUILD_TYPE={config_type}')
            case _:
                if cfg.debug: raise Exception(f'Unknown config type: {config_type}')

        if hasattr(toolchain, 'cmake'):
            toolchain.cmake( cfg )

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
