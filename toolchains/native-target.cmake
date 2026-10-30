# Include after CMAKE_SYSTEM_NAME and CMAKE_SYSTEM_PROCESSOR are set.
# CMakeDetermineSystem marks every toolchain that sets SYSTEM_NAME as a
# cross compile unless CMAKE_CROSSCOMPILING is already defined. Set it
# FALSE only when the target names this machine. Leave it unset for a
# real cross compile so CMake sets TRUE and native CPU flags stay off.
#
# Windows reports AMD64 and ARM64. The triples use x86_64, i686, aarch64.

if(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "^(AMD64|amd64|x86_64|x64)$")
    set(_autobuild_host_family "x64")
elseif(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "^(i686|i386|x86|x86_32)$")
    set(_autobuild_host_family "x86")
elseif(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "^(aarch64|ARM64|arm64)$")
    set(_autobuild_host_family "arm64")
elseif(CMAKE_HOST_SYSTEM_PROCESSOR MATCHES "^(armv7|armv6|arm)$")
    set(_autobuild_host_family "arm32")
else()
    set(_autobuild_host_family "")
endif()

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(AMD64|amd64|x86_64|x64)$")
    set(_autobuild_target_family "x64")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(i686|i386|x86|x86_32)$")
    set(_autobuild_target_family "x86")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|ARM64|arm64)$")
    set(_autobuild_target_family "arm64")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(armv7|armv6|arm)$")
    set(_autobuild_target_family "arm32")
else()
    set(_autobuild_target_family "")
endif()

if(CMAKE_SYSTEM_NAME STREQUAL CMAKE_HOST_SYSTEM_NAME
        AND _autobuild_host_family STREQUAL _autobuild_target_family
        AND NOT _autobuild_target_family STREQUAL "")
    set(CMAKE_CROSSCOMPILING FALSE)
endif()

unset(_autobuild_host_family)
unset(_autobuild_target_family)
