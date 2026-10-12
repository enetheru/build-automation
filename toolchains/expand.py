"""Shared arch and platform expansion for a toolchain."""
import itertools
import platform
from copy import deepcopy
from types import SimpleNamespace


def generic_toolchain_expand(self: SimpleNamespace, build: SimpleNamespace) -> list:
    """One build per architecture and platform on this toolchain."""
    configs_out: list = []

    for target_arch, target_platform in itertools.product(self.arch_list, self.platform_list):
        tc = deepcopy(self)
        setattr(tc, 'host_arch', platform.machine())
        setattr(tc, 'target_platform', target_platform)
        setattr(tc, 'target_arch', target_arch)

        build = deepcopy(build)
        setattr(build, 'toolchain', tc)
        configs_out.append(build)

    return configs_out
