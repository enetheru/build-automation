# https://github.com/mstorsjo/llvm-mingw

# This toolchain file requires the compilers and tools be in the PATH

set( LLVM_MINGW_PROCESSOR ${CMAKE_HOST_SYSTEM_PROCESSOR} CACHE STRING "Select the Processor to compile for")
set_PROPERTY( CACHE LLVM_MINGW_PROCESSOR PROPERTY STRINGS "i686;x86_64;armv7;aarch64" )

# toolchain-mingw64.cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR ${LLVM_MINGW_PROCESSOR})

# The python toolchain passes LLVM_MINGW_ROOT for the tree whose bin is on
# PATH. C:/llvm-mingw remains the default when that variable is absent.
set( LLVM_MINGW_ROOT "C:/llvm-mingw" CACHE PATH "llvm-mingw installation" )
set( PREFIX "${LLVM_MINGW_ROOT}" )
# specify the cross compiler
set( CMAKE_INSTALL_PREFIX "$PREFIX/${LLVM_MINGW_PROCESSOR}-w64-mingw32" )
set( CMAKE_C_COMPILER "${LLVM_MINGW_PROCESSOR}-w64-mingw32-clang"  )
set( CMAKE_CXX_COMPILER "${LLVM_MINGW_PROCESSOR}-w64-mingw32-clang++"  )
set( CMAKE_RC_COMPILER "${LLVM_MINGW_PROCESSOR}-w64-mingw32-windres"  )
set( CMAKE_ASM_MASM_COMPILER "llvm-ml"  )
set( CMAKE_AR "${PREFIX}/bin/llvm-ar"  )
set( CMAKE_RANLIB "${PREFIX}/bin/llvm-ranlib"  )

# where is the target environment
# FIND_ROOT only rewrites other search paths. PREFIX_PATH is what
# find_package actually walks, and ONLY drops anything outside these roots.
set(CMAKE_FIND_ROOT_PATH
        ${PREFIX}
        ${PREFIX}/${LLVM_MINGW_PROCESSOR}-w64-mingw32
)
set(CMAKE_PREFIX_PATH ${CMAKE_FIND_ROOT_PATH})

# i686, armv7, and aarch64 are cross compiles from this x64 host. An
# aarch64 target on an ARM64 Windows host is not. The installed Vulkan
# SDK matches the host, so it is only added for that native case.
include("${CMAKE_CURRENT_LIST_DIR}/native-target.cmake")
if(DEFINED CMAKE_CROSSCOMPILING AND NOT CMAKE_CROSSCOMPILING)
    if(DEFINED ENV{VULKAN_SDK})
        list(APPEND CMAKE_FIND_ROOT_PATH "$ENV{VULKAN_SDK}")
        list(APPEND CMAKE_PREFIX_PATH "$ENV{VULKAN_SDK}")
    endif()
endif()

# search for programs in the build host directories
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
# for libraries and headers in the target directories
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)