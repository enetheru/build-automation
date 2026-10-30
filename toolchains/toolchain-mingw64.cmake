# https://www.mingw-w64.org/build-systems/cmake/

# This toolchain file requires the compilers and tools be in the PATH

# toolchain-mingw64.cmake
# C:/mingw64 ships x86_64-w64-mingw32-gcc only. There is no i686 compiler
# in this tree. Native CPU flags stay on only when the host is Windows x64.
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
include("${CMAKE_CURRENT_LIST_DIR}/native-target.cmake")

# specify the cross compiler
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)

# The old /usr prefix is an MSYS path. CMake running on Windows never
# looks there. OpenSSL for this toolchain lives under opt/.
# FIND_ROOT alone is only a prefix for other search paths, so the same
# list has to be CMAKE_PREFIX_PATH or find_package never walks it.
# ONLY stays on so a host MSVC import library is not chosen instead.
set(_MINGW64_ROOTS
    C:/mingw64/x86_64-w64-mingw32
    C:/mingw64
    C:/mingw64/opt
)
if(DEFINED ENV{VULKAN_SDK})
    list(APPEND _MINGW64_ROOTS "$ENV{VULKAN_SDK}")
endif()
set(CMAKE_FIND_ROOT_PATH ${_MINGW64_ROOTS})
set(CMAKE_PREFIX_PATH ${_MINGW64_ROOTS})
unset(_MINGW64_ROOTS)

# search for programs in the build host directories
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
# for libraries and headers in the target directories
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)


# here is the example help given at the website.
# CMakeLists.txt
#if(MINGW)
#    message(STATUS "Building with mingw-w64")
#else()
#    message(STATUS "Not building with mingw-w64")
#endif()
#
#cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain-mingw64.cmake
#
#cmake --build build
#
#wine build/hello.exe
#Hello, Windows!