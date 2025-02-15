# https://github.com/mstorsjo/llvm-mingw

# This toolchain file requires the compilers and tools be in the PATH

set( LLVM_MINGW_PROCESSOR ${CMAKE_HOST_SYSTEM_PROCESSOR} CACHE STRING "Select the Processor to compile for")
set_PROPERTY( CACHE LLVM_MINGW_PROCESSOR PROPERTY STRINGS "i686;x86_64;armv7;aarch64" )

# toolchain-mingw64.cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR ${LLVM_MINGW_PROCESSOR})

set( PREFIX "C:/llvm-mingw" )
# specify the cross compiler
set( CMAKE_INSTALL_PREFIX "$PREFIX/${LLVM_MINGW_PROCESSOR}-w64-mingw32" )
set( CMAKE_C_COMPILER "${LLVM_MINGW_PROCESSOR}-w64-mingw32-clang"  )
set( CMAKE_CXX_COMPILER "${LLVM_MINGW_PROCESSOR}-w64-mingw32-clang++"  )
set( CMAKE_RC_COMPILER "${LLVM_MINGW_PROCESSOR}-w64-mingw32-windres"  )
set( CMAKE_ASM_MASM_COMPILER "llvm-ml"  )
set( CMAKE_AR "${PREFIX}/bin/llvm-ar"  )
set( CMAKE_RANLIB "${PREFIX}/bin/llvm-ranlib"  )

# where is the target environment
set(CMAKE_FIND_ROOT_PATH
        ${PREFIX}
        ${PREFIX}/${LLVM_MINGW_PROCESSOR}-w64-mingw32
)

# search for programs in the build host directories
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
# for libraries and headers in the target directories
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)