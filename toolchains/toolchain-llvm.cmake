set( CMAKE_SYSTEM_NAME Windows )
set( CMAKE_SYSTEM_PROCESSOR x86_64 )

# This install's clang-cl defaults to x86_64-pc-windows-msvc. Native CPU
# flags stay on only when that is the host. Another processor is a cross
# compile, and this file does not select a clang-cl target triple for it.
include( "${CMAKE_CURRENT_LIST_DIR}/native-target.cmake" )

# C and C++ both use clang-cl. CMake rejects a GNU-like clang mixed with clang-cl.
set( CMAKE_C_COMPILER "C:/Program Files/LLVM/bin/clang-cl.exe" )
set( CMAKE_CXX_COMPILER "C:/Program Files/LLVM/bin/clang-cl.exe" )
set( CMAKE_RC_COMPILER "C:/Program Files/LLVM/bin/llvm-rc.exe" )

# adjust the default behavior of the FIND_XXX() commands:
# search programs in the host environment
set( CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER )

# Host clang-cl. Search the LLVM tree and the rest of the host, so libomp,
# the Vulkan SDK, and OpenSSL are visible.
set( CMAKE_FIND_ROOT_PATH "C:/Program Files/LLVM" )
set( CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH )
set( CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH )

# clang-cl ignores -fopenmp. -openmp:llvm compiles, and libomp.lib links.
set( OpenMP_C_FLAGS "-openmp:llvm" CACHE STRING "" FORCE )
set( OpenMP_CXX_FLAGS "-openmp:llvm" CACHE STRING "" FORCE )
set( OpenMP_C_LIB_NAMES "libomp" CACHE STRING "" FORCE )
set( OpenMP_CXX_LIB_NAMES "libomp" CACHE STRING "" FORCE )
set( OpenMP_libomp_LIBRARY "C:/Program Files/LLVM/lib/libomp.lib" CACHE FILEPATH "" FORCE )


#[[ FIXME When specifying glaang++ I get the below error:
#   When cmake configures a project, it will fail to find libcmt when testing the compiler
lld-link: error: <root>: undefined symbol: mainCRTStartup

This can be mitigated somewhat by specifying it directly

set( CMAKE_CXX_FLAGS_INIT -llibcmt )

or by setting the msvc_runtime
set( CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL" )

But the build still fails.
]]#


# godot-cpp accounts for this in the detection when using clang-cl
# https://github.com/godotengine/godot/issues/43354
# https://github.com/godotengine/godot/issues/87199
# C:/build/godot-cpp/w64-cmake-llvm-w64/include\godot_cpp/core/method_bind.hpp:347:45:
#   error:
#       cannot reinterpret_cast from member pointer type 'void (ExampleRef::*)(int)'
#       to member pointer type 'void (godot::_gde_UnexistingClass::*)(int)' of different size
#set( CMAKE_CXX_FLAGS -DTYPED_METHOD_BIND )