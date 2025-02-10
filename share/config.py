from copy import deepcopy
from types import SimpleNamespace

from share.toolchains import toolchains


# MARK: Arch
def expand_arch( config:SimpleNamespace ) -> list:
    configs_out:list = []

    for arch in config.toolchain.arch:
        cfg = deepcopy(config)

        cfg.name += f".{arch}"
        setattr( cfg, 'arch', arch )

        configs_out.append( cfg )
    return configs_out

# MARK: Toolchain
def expand_toolchains( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for toolchain in toolchains.values():
        cfg = deepcopy(config)

        cfg.name += f".{toolchain.name}"
        setattr(cfg, 'toolchain', toolchain )

        configs_out += expand_arch( cfg )

    return configs_out

def expand_config( config:SimpleNamespace ) -> list:
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
    return expand_toolchains( config )

