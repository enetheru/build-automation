from copy import deepcopy
from types import SimpleNamespace

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
        cfg = deepcopy(config)
        setattr(cfg, 'toolchain', toolchain )
        configs_out.append( cfg )

    configs_out = expand( configs_out, expand_arch)
    configs_out = expand( configs_out, expand_platform)

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
def expand_cmake( config:SimpleNamespace, build_type:str ) -> list:
    configs_out:list = []
    buildtool = getattr(config, 'buildtool', None)
    if buildtool is None:
        setattr(config, 'buildtool', 'cmake' )
    elif config.buildtool != 'cmake': return []

    generators = {
        'msvc':'Visual Studio 17 2022',
        'ninja':'Ninja',
        'ninja-multi':'Ninja Multi-Config',
        'mingw':'MinGW Makefiles'
    }

    for generator in generators:
        cfg = deepcopy(config)

        cmake = getattr( cfg, 'cmake', {})
        setattr( cfg, 'cmake', {
            'config_vars':['-DCMAKE_CXX_COMPILER_LAUNCHER=ccache'],
            'build_vars':[],
            'targets':['all'],
            'gen':generator,
            'generator':generators[generator],
            'build_type':build_type,
            'build_dir':'build-cmake',
        } | cmake )

        match generator:
            case 'msvc':
                if cfg.toolchain.name != generator: continue
                _A = {'x86_32':'Win32', 'x86_64':'x64', 'arm64':'ARM64'}
                cfg.cmake['config_vars'].append( f'-A {_A[cfg.arch]}')
                cfg.cmake['build_vars'].append(f'--config {build_type}')
                cfg.cmake['tool_vars'] = ['-nologo', '-verbosity:normal', "-consoleLoggerParameters:'ShowCommandLine;ForceNoAlign'"]

            case 'ninja':
                cfg.cmake['config_vars'].append(f'-DCMAKE_BUILD_TYPE={build_type}')

            case 'ninja-multi':
                cfg.cmake['build_vars'].append(f'--config {build_type}')

            case 'mingw':
                if cfg.toolchain.name != 'mingw64': continue
                cfg.cmake['config_vars'].append(f'-DCMAKE_BUILD_TYPE={build_type}')
            case _:
                continue

        configs_out.append( cfg )
    return configs_out

def expand_host( config:SimpleNamespace ) -> list:
    import sys

    bits = "64" if sys.maxsize > 2**32 else "32"

    match sys.platform:
        case 'linux':
            host = f'l{bits}'
        case 'darwin':
            host = f'd{bits}'
        case 'win32':
            host = f'w{bits}'
        case 'cygwin':
            host = f'c{bits}'
        case _: # 'aix', 'android', 'emscripten', 'ios', 'wasi'
            # I am not aware of any compilers for these platforms yet
            return []

    setattr( config, 'host', host )
    return [config]

def expand_host_env( config:SimpleNamespace, opts:SimpleNamespace ) -> list:
    configs_out:list = expand( [config], expand_host)
    configs_out = expand( configs_out, expand_toolchains, opts.toolchains )

    # configs_out = expand( configs_out, expand_buildtool )

    return configs_out
