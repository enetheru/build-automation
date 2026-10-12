cmake_minimum_required(VERSION 3.16)
project(hello LANGUAGES CXX)

option(HELLO_SHOUT "Print the greeting in upper case" OFF)
if(NOT HELLO_BUILD_NAME)
    set(HELLO_BUILD_NAME "manual")
endif()

add_executable(hello src/main.cpp)
target_compile_definitions(hello PRIVATE
    "HELLO_BUILD=\"${HELLO_BUILD_NAME}\""
    "HELLO_COMPILER=\"${CMAKE_CXX_COMPILER_ID}\""
    "HELLO_SYSTEM=\"${CMAKE_SYSTEM_NAME}\""
    "HELLO_ARCH=\"${CMAKE_SYSTEM_PROCESSOR}\""
)
if(HELLO_SHOUT)
    target_compile_definitions(hello PRIVATE HELLO_SHOUT)
endif()
