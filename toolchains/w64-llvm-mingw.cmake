# Source        https://github.com/mstorsjo/llvm-mingw
# Location :    C:\llvm-mingw
set( CMAKE_SYSTEM_NAME Windows )
set( CMAKE_SYSTEM_PROCESSOR x86_64 )

#set( CMAKE_SYSROOT "C:/llvm-mingw" )

#set(triple x86_64-w64-mingw32)

#set(CMAKE_C_COMPILER ${CMAKE_SYSROOT}/bin/${triple}-gcc.exe)
##set(CMAKE_C_COMPILER_TARGET ${triple})
#
#set(CMAKE_CXX_COMPILER ${CMAKE_SYSROOT}/bin/${triple}-g++.exe)
##set(CMAKE_CXX_COMPILER_TARGET ${triple})


# which compilers to use for C and C++
set( CMAKE_C_COMPILER C:/llvm-mingw/bin/x86_64-w64-mingw32-clang.exe )
set( CMAKE_CXX_COMPILER C:/llvm-mingw/bin/x86_64-w64-mingw32-clang++.exe )

# where is the target environment located
set( CMAKE_FIND_ROOT_PATH
        C:/llvm-mingw/x86_64-w64-mingw32
        C:/llvm-mingw
)

# adjust the default behavior of the FIND_XXX() commands:
# search programs in the host environment
set( CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER )

# search headers and libraries in the target environment
set( CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY )
set( CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY )
