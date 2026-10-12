cmake_minimum_required(VERSION 3.16)
project(hello LANGUAGES CXX)

option(HELLO_SHOUT "Print the greeting in upper case" OFF)
if(NOT HELLO_BUILD_NAME)
    set(HELLO_BUILD_NAME "manual")
endif()

add_executable(hello src/main.cpp)
# $<CONFIG> is the configuration being built. Multi-config generators compile
# Debug, Release, and RelWithDebInfo from this one cache, so the name has to
# be chosen then, not at configure time.
if(CMAKE_CONFIGURATION_TYPES)
    target_compile_definitions(hello PRIVATE "HELLO_BUILD=\"${HELLO_BUILD_NAME} $<CONFIG>\"")
else()
    target_compile_definitions(hello PRIVATE "HELLO_BUILD=\"${HELLO_BUILD_NAME}\"")
endif()
target_compile_definitions(hello PRIVATE
    "HELLO_COMPILER=\"${CMAKE_CXX_COMPILER_ID}\""
    "HELLO_SYSTEM=\"${CMAKE_SYSTEM_NAME}\""
    "HELLO_ARCH=\"${CMAKE_SYSTEM_PROCESSOR}\""
)
if(HELLO_SHOUT)
    target_compile_definitions(hello PRIVATE HELLO_SHOUT)
endif()
