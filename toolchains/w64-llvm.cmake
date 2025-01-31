set( CMAKE_SYSTEM_NAME Windows )
set( CMAKE_SYSTEM_PROCESSOR x86_64 )

# which compilers to use for C and C++
#set( CMAKE_C_COMPILER "C:/Program Files/LLVM/bin/clang.exe" )

set( CMAKE_CXX_COMPILER "C:/Program Files/LLVM/bin/clang-cl.exe" )
set( CMAKE_RC_COMPILER "C:/Program Files/LLVM/bin/llvm-rc.exe" )

# adjust the default behavior of the FIND_XXX() commands:
# search programs in the host environment
set( CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER )

# search headers and libraries in the target environment
set( CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY )
set( CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY )


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