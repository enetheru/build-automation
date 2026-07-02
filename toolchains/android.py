"""
Module for managing Android SDK and related tools using sdkmanager.

This module defines several functions and utilities for handling Android SDK
operations, such as installing packages, listing installed components, parsing
SDK manager outputs, and setting up a toolchain for Android development. The
module enables effective integration of SDK tools with automation scripts or
build systems.

"""
import re
import subprocess
from copy import deepcopy
from types import SimpleNamespace, MethodType
from typing import cast, Mapping, Any

from share.script_preamble import *


def strip_until_installed_packages(list_installed_raw) -> str:
    """Remove text before the 'Installed packages:' marker in SDK manager output.

    Args:
        list_installed_raw (str): The raw output from sdkmanager --list_installed.

    Returns:
        str: The cleaned output starting from the packages table.
    """
    pattern = r'^.*?(?=Installed packages:\n)|Installed packages:\n'
    return re.sub(pattern, '', list_installed_raw, flags=re.DOTALL)

def parse_sdk_output(list_installed_raw) -> list[dict]:
    """Parse SDK manager output into a list of package dictionaries.

    Args:
        list_installed_raw (str): The cleaned output containing the packages table.

    Returns:
        list[dict]: A list of dictionaries with package, version, description, and location keys.
    """
    pkgs = []
    lines = list_installed_raw.strip().split('\n')
    for line in lines[2:]:  # Skip header line (Path | Version | ...)
        parts = [part.strip() for part in line.split('|')]
        if len(parts) == 4:
            pkgs.append({
                "package": parts[0].split(';')[0],
                "version": parts[1],
                "description": parts[2],
                "location": parts[3]
            })
    return pkgs

def install( self:SimpleNamespace, package_path : str ) -> str | None:
    """Install an Android SDK package using sdkmanager.

    Args:
        :param package_path: (str) The package path to install (e.g., 'build-tools;34.0.0')
        :param self:(SimpleNamespace)


    Returns:
        str or None: The command output if successful, None if the command fails.

    Raises:
        subprocess.CalledProcessError: If the installation command fails.

    """

    sdkmanager = f"{self.sdk_path}/cmdline-tools/latest/bin/sdkmanager.bat"
    try:
        # subprocess.check_output(
        #     [sdkmanager, package_path],
        #     stderr=subprocess.DEVNULL,
        #     shell=True,
        #     text=True,
        #     encoding="utf-8",
        #     errors="replace"
        # )
        stream_command( " ".join([sdkmanager, package_path]),
                        stderr_handler=lambda msg:print(msg)
                        )

    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")


def list_installed(self:SimpleNamespace) -> list[dict] | None:
    """
   Parse the output of a command `sdkmanager.bat --list_installed` to extract the installed packages table.
   Removes everything up to and including the "Installed packages:" line and parses the table
   into a list of dictionaries with package, version, description, and location.

   Returns:
       list: A list of dictionaries, each containing:
             - package (str): The package name (e.g., 'build-tools').
             - version (str): The package version (e.g., '34.0.0').
             - description (str): The package description (e.g., 'Android SDK Build-Tools 34').
             - location (str): The package location (e.g., 'build-tools\\34.0.0').

   Raises:
       ValueError: If the "Installed packages:" marker is not found or the table is malformed.
   """
    sdkmanager = f"{self.sdk_path}/cmdline-tools/latest/bin/sdkmanager.bat"
    try:
        output = subprocess.check_output(
            [sdkmanager, "--list_installed"],
            stderr=subprocess.DEVNULL,
            shell=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        cleaned_output = strip_until_installed_packages(output)
        return parse_sdk_output(cleaned_output)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")


def update(self, toolchain:SimpleNamespace, console:Console):
    """
    Updates the Android SDK by ensuring all required packages are installed and up-to-date. It uses the
    provided toolchain object to check the installed packages and compares them against the required
    packages. If any required package is missing or outdated, it triggers an installation process.

    :param self: Reference to the current instance of the class.
    :param toolchain: A `SimpleNamespace` object containing the Android SDK toolchain utilities.
        Specifically, it includes the `list_installed` method to retrieve installed packages
        and a `packages` dictionary of required package names as keys and their associated
        versions as values.
    :param console: A `Console` instance used to perform console operations, such as setting
        the window title for the update process.
    :return: None
    """
    console.set_window_title('Updating Android SDK')
    fmt.t2("Android Update")

    packages = toolchain.list_installed()
    print( f"installed_packages: {packages}")

    for package,version in toolchain.packages.items():
        print(f"Checking for {package};{version}")
        if not any(package["package"] == package and package["version"] == version for package in packages):
            self.install( f'{package};{version}' )


def expand(self, config:SimpleNamespace) -> list:
    """
    Expands the configuration object for multiple Android ABIs and creates a list of
    newly adapted configuration objects.

    This method iterates over the available Android ABIs, clones the provided
    configuration object, and sets specific attributes for each ABI variant.
    The list of newly modified configuration objects is then returned.

    :param self: Reference to the current instance of the class.
    :param config: A SimpleNamespace configuration object to be adapted for
        different Android ABIs.
    :return: A list of SimpleNamespace objects, each configured for a specific
        Android ABI.
    """
    configs_out:list = []
    for abi in self.abi:
        cfg = deepcopy(config)
        setattr( cfg, 'android_abi', abi )
        setattr( cfg, 'arch', abi )
        setattr( cfg, 'platform', 'android' )
        configs_out.append( cfg )

    return configs_out

def configure_cmake( build:SimpleNamespace ):
    """
    Configures the CMake build process for an Android project using the provided build context.

    This function assigns the appropriate toolchain file and configuration variables
    to the build tool based on the provided build context. The function customizes
    the environment to ensure compatibility with the specified Android platform
    and architecture.

    :param build: Namespace-like object containing build configuration details,
                  including `toolchain` and `buildtool` attributes.
    :type build: SimpleNamespace
    """
    toolchain = build.toolchain
    cmake = build.buildtool

    # add cmake flags.
    cmake.config_vars += [
        # f'-DANDROID_PLATFORM={build.platform}',
        # f'-DANDROID_ABI={build.arch}']

    ]
    cmake.toolchain = os.path.normpath(f'{toolchain.ndk_path}/build/cmake/android.toolchain.cmake')

def android_toolchain() -> SimpleNamespace | None:
    """
    Determines and configures the Android toolchain for development by inspecting environment
    variables `ANDROID_HOME` and `ANDROID_NDK`. If both variables are present, it initializes
    and returns a `SimpleNamespace` object with attributes and methods for managing the Android
    toolchain. If either variable is missing, the function returns `None`.

    The returned `SimpleNamespace` object contains pre-configured attributes for describing
    the toolchain, such as supported ABI(s), paths to SDK and NDK, as well as specific
    methods for performing updates, installations, and expanding configurations
    (e.g., for CMake integration).

    :return: A configured SimpleNamespace representing the Android toolchain, or None
             if the required environment variables are not defined.
    :rtype: SimpleNamespace | None
    """
    if 'ANDROID_HOME' not in os.environ:
        return None
    if 'ANDROID_NDK' not in os.environ:
        return None
    toolchain = SimpleNamespace(**cast( Mapping[str,Any],{
        'name':'android',
        'desc':'[Android](https://developer.android.com/tools/sdkmanager)',
        'verbs':['update'],
        'abi':['armeabi-v7a','arm64-v8a','x86','x86_64'],
        'platform':'',
        'sdk_path':os.path.normpath(os.environ['ANDROID_HOME']),
        'ndk_path':os.path.normpath(os.environ['ANDROID_NDK']),
        # 'api_level':'latest',
        'cmake':configure_cmake
    }))
    setattr(toolchain, 'update', MethodType(update, toolchain))
    setattr(toolchain, 'expand', MethodType(expand, toolchain))
    setattr(toolchain, 'install', MethodType(install, toolchain) )
    setattr(toolchain, 'configure_cmake', MethodType(configure_cmake, toolchain))

    return toolchain

# Example Output
# Loading local repository...
# [=========                              ] 25% Loading local repository...
# [=========                              ] 25% Fetch remote repository...
# [=======================================] 100% Fetch remote repository...
#
# Installed packages:
#   Path                 | Version      | Description                             | Location
#   -------              | -------      | -------                                 | -------
#   build-tools;34.0.0   | 34.0.0       | Android SDK Build-Tools 34              | build-tools\34.0.0
#   cmake;3.10.2.4988404 | 3.10.2       | CMake 3.10.2.4988404                    | cmake\3.10.2.4988404
#   cmdline-tools;16.0   | 16.0         | Android SDK Command-line Tools          | cmdline-tools\16.0
#   cmdline-tools;19.0   | 19.0         | Android SDK Command-line Tools          | cmdline-tools\19.0
#   cmdline-tools;latest | 19.0         | Android SDK Command-line Tools (latest) | cmdline-tools\latest
#   ndk;23.2.8568313     | 23.2.8568313 | NDK (Side by side) 23.2.8568313         | ndk\23.2.8568313
#   platform-tools       | 36.0.0       | Android SDK Platform-Tools              | platform-tools
#   platforms;android-34 | 3            | Android SDK Platform 34                 | platforms\android-34