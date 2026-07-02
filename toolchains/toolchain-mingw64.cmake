# https://www.mingw-w64.org/build-systems/cmake/

# This toolchain file requires the compilers and tools be in the PATH

# toolchain-mingw64.cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# specify the cross compiler
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)

# where is the target environment
set(CMAKE_FIND_ROOT_PATH /usr/x86_64-w64-mingw32)

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