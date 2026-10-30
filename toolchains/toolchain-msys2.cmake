# Used when an MSYS2 environment targets a different processor than the
# host. The matching x64 environments do not load this file.
set(MSYS2_PROCESSOR "${CMAKE_HOST_SYSTEM_PROCESSOR}" CACHE STRING
    "Processor this MSYS2 environment compiles for")
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR "${MSYS2_PROCESSOR}")
include("${CMAKE_CURRENT_LIST_DIR}/native-target.cmake")
