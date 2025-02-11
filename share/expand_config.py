from copy import deepcopy
from types import SimpleNamespace

from share.toolchains import toolchains

def expand( configs:list, func ) -> list:
    configs_out:list = []
    for config in configs:
        configs_out += func( config )
    return configs_out

# # MARK: BuildTool
# def expand_buildtool( config:SimpleNamespace ) -> list:
#     configs_out:list = []
#     for buildtool in config.toolchain.platform:
#         cfg = deepcopy(config)
#         setattr( cfg, 'buildtool', buildtool )
#         configs_out.append( cfg )
#     return configs_out

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
def expand_toolchains( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for toolchain in toolchains.values():
        cfg = deepcopy(config)
        setattr(cfg, 'toolchain', toolchain )
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

def expand_host_env( config:SimpleNamespace ) -> list:
    configs_out:list = expand( [config], expand_host)
    configs_out:list = expand( configs_out, expand_toolchains)
    configs_out = expand( configs_out, expand_arch)
    configs_out = expand( configs_out, expand_platform)

    return configs_out
