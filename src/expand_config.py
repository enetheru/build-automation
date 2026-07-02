"""
Module for configuration expansion utilities.

Provides functions that process and expand build configurations using various
attributes, properties, and toolchains. These utilities allow for the generation
of multiple configuration permutations that can be used in build systems or
toolchain-based workflows.
"""
import itertools
from copy import deepcopy
from types import SimpleNamespace

from src.config import gopts
from share.snippets import cmake_build, cmake_check, cmake_configure


def expand_func( configs_in:list[SimpleNamespace], func, *args ) -> list:
    """
    Expands a list of configurations by applying a provided function to each configuration.

    This function operates on a list of input configurations, applying a callable
    function to each configuration. If additional arguments are provided, they
    will be passed to the callable function along with each configuration.

    :param configs_in: List of configuration objects to be processed.
    :type configs_in: list[SimpleNamespace]
    :param func: A callable that processes each configuration. It should return
        a list of processed configuration objects.
    :type func: Callable
    :param args: Optional positional arguments to be passed to the callable
        along with each configuration.
    :type args: tuple
    :return: List of processed configuration objects resulting from applying the
        function to each input configuration.
    :rtype: list
    """
    configs_out:list = []
    for cfg in configs_in:
        if args: configs_out += func(cfg, *args)
        else: configs_out += func(cfg)
    return configs_out


def expand_list( configs_in:list[SimpleNamespace], prop:str, items:list ) -> list:
    """
    Expands a list of configuration objects by associating each configuration with
    each item in a given list. A deep copy of each configuration is made, and the
    specified property is updated with the corresponding item.

    :param configs_in: A list of SimpleNamespace objects representing the initial
        configurations to be expanded.
    :param prop: The property name as a string that will be updated in each
        configuration.
    :param items: A list of items used to expand the configurations by assigning
        each item to the specified property.
    :return: A new list of SimpleNamespace objects where each configuration is
        associated with each item from the provided list.
    :rtype: list
    """
    configs_out:list = []
    for cfg, item in itertools.product(configs_in, items):
        cfg = deepcopy(cfg)
        setattr(cfg, prop, item )
        configs_out.append( cfg )
    return configs_out

def expand_attr_list( config_in:SimpleNamespace, attr:str, items:list[SimpleNamespace] ) -> list:
    """
    Expands a configuration attribute based on provided items and returns a list of expanded configurations.

    This function takes an initial configuration, a specified attribute, and a list of items.
    For each item in the list, it creates a copy of the initial configuration and assigns the
    respective item to the given attribute. If an item has specific methods (`configure` or
    `expand`), the function further processes these cases to create more granular configurations.
    The method recursively expands configurations as necessary.

    :param config_in: The initial configuration to be expanded.
    :type config_in: SimpleNamespace
    :param attr: The name of the attribute in the configuration that will be expanded using items.
    :type attr: str
    :param items: A list of items used to assign values to the given attribute in the configuration.
    :type items: list[SimpleNamespace]
    :return: A list of expanded configurations based on the provided items.
    :rtype: list[SimpleNamespace]
    """
    configs_out:list[SimpleNamespace] = []

    for item in items:
        cfg = deepcopy(config_in)

        setattr(cfg, attr, deepcopy(item) )

        if hasattr( item, 'configure' ):
            cfg.configure_funcs.append( getattr(item, 'configure') )

        if hasattr( item, 'expand' ):
            configs_out += expand_func([cfg], getattr(item, 'expand') )
            continue

        configs_out.append( cfg )
    return configs_out


def expand_buildtools( config_in:SimpleNamespace, project:SimpleNamespace ) -> list:
    """
    Performs the expansion of build tools by iterating over the `buildtools` of the provided
    project and copying the incoming base configuration for each tool. Expansions and
    configurations for each build tool are added to the output list of configurations.

    :param config_in: The base configuration that is copied and extended for each build tool.
    :type config_in: SimpleNamespace
    :param project: The project containing the `buildtools` to be processed.
    :type project: SimpleNamespace
    :return: A list of extended and potentially expanded configurations for the build tools in `project`.
    :rtype: list
    """
    configs_out:list = []
    for tool in project.buildtools.keys():
        cfg = deepcopy(config_in)

        buildtool : SimpleNamespace = project.buildtools[tool]
        setattr(cfg, 'buildtool', buildtool)

        if hasattr( buildtool, 'configure' ):
            cfg.configure_funcs.append(buildtool.configure)

        if hasattr( buildtool, 'expand' ):
            configs_out += expand_func([cfg], buildtool.expand)
            continue

        configs_out.append(cfg)

    return configs_out


# MARK: Toolchain
def expand_toolchains( cfg:SimpleNamespace, project:SimpleNamespace ) -> list:
    """
    Expands the toolchains defined in the project by generating configurations for each
    combination of architecture and platform or calling the custom expander function of
    the toolchain, if available. This utility processes the toolchains in the project
    to create a list of configuration objects.

    :param cfg: The base configuration object to build upon.
    :type cfg: SimpleNamespace
    :param project: The project object that contains the toolchains to be expanded.
    :type project: SimpleNamespace
    :return: A list of expanded configuration objects based on the toolchains, architecture,
        and platform in the project.
    :rtype: list
    """
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
    """
    Expands the given CMake configuration into all combinations of CMake settings, including
    configuration types, generators, and targets. This function is intended to construct a list
    of detailed configurations based on the base configuration object provided.

    :param config: The base configuration, containing details about the build tool, toolchain,
        and associated settings required to generate multiple configurations.
    :type config: SimpleNamespace
    :return: A list of generated configurations, with each configuration representing a unique
        combination of settings derived from the base configuration.
    :rtype: list
    """
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

        if gopts.debug:
            cmake.config_vars.extend([ f'--debug-output', f'--debug-trycompile' ])
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
    """
    Generates a short string identifying the host platform and its bitness.

    This function determines the operating system's name shortened to its
    first letter and appends whether the system is 32-bit or 64-bit based
    on the architecture of the Python interpreter.

    :return: A string combining the first letter of the platform name
             and the system's bitness (e.g., "w64" for 64-bit Windows).
    :rtype: str
    """
    import sys
    bits = "64" if sys.maxsize > 2**32 else "32"
    return f'{sys.platform[0]}{bits}'


def expand_host_env( config:SimpleNamespace, project:SimpleNamespace ) -> list:
    """
    Expands the given configuration for the host environment by processing build tools and toolchains.

    This function assigns a host identifier to the `config` object, expands the configuration
    using specified build tools and toolchains, and assigns a unique name to each expanded
    configuration if not already set.

    :param config: The initial configuration to expand.
    :type config: SimpleNamespace
    :param project: The project settings and information used for expansion.
    :type project: SimpleNamespace
    :return: A list of fully expanded configurations, each with set attributes such as
        `host`, `buildtool`, and `toolchain`.
    :rtype: list
    """
    setattr( config, 'host', short_host() )

    configs_out = expand_func( [config], expand_buildtools, project )

    configs_out = expand_func( configs_out, expand_toolchains, project )

    for config in configs_out:
        if not getattr(config, 'name', None):
            setattr(config, 'name', f'{config.host}.{config.buildtool}.{config.toolchain.name}')

    return configs_out
