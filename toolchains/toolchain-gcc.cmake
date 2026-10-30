# toolchain-gcc.cmake
# Host GCC. Do not set CMAKE_SYSTEM_NAME: CMake would then mark the build
# as a cross compile. The arch list is the host only.
# Native Linux build with the system GCC. The compilers must be on PATH.
set(CMAKE_C_COMPILER gcc)
set(CMAKE_CXX_COMPILER g++)
