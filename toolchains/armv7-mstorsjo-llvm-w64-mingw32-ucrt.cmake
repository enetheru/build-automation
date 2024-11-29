set( CMAKE_SYSTEM_NAME Windows )
set( CMAKE_SYSTEM_PROCESSOR armv7 )

# which compilers to use for C and C++
set( CMAKE_C_COMPILER C:/llvm-mingw/bin/armv7-w64-mingw32-clang.exe )
set( CMAKE_CXX_COMPILER C:/llvm-mingw/bin/armv7-w64-mingw32-clang++.exe )

# where is the target environment located
set( CMAKE_FIND_ROOT_PATH
        C:/llvm-mingw/armv7-w64-mingw32
        C:/llvm-mingw
)

# adjust the default behavior of the FIND_XXX() commands:
# search programs in the host environment
set( CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER )

# search headers and libraries in the target environment
set( CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY )
set( CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY )
