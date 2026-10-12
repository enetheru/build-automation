"""Microsoft Visual Studio toolchain."""
import shlex
import subprocess
from types import SimpleNamespace, MethodType

from src.config import toolchain_base
from toolchains.expand import generic_toolchain_expand


def msvc_toolchain() -> SimpleNamespace:
    """MSVC toolchain. The shell enters a VS DevShell for this install."""
    instance_cmd = "C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"
    instance_id = subprocess.check_output([instance_cmd, '-property', 'instanceId']).strip().decode()
    installation_path = subprocess.check_output([instance_cmd, '-property', 'installationPath']).strip().decode()

    toolchain = SimpleNamespace({**vars(toolchain_base), **{
        'name': 'msvc',
        'desc': '# Microsoft Visual Studio',
        'shell': ["pwsh", "-Command",
                  f""" "&{{Import-Module '{shlex.quote(installation_path).strip("'")}\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; Enter-VsDevShell {instance_id} -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'}};" """],
        "arch_list": ['x86_64'],
        'platform_list': ['win32'],
    }})
    setattr(toolchain, 'expand', MethodType(generic_toolchain_expand, toolchain))
    return toolchain
