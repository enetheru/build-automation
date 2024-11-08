set( CMAKE_SYSTEM_NAME Windows )
set( CMAKE_SYSTEM_PROCESSOR x86_64 )

# which compilers to use for C and C++
set(CMAKE_C_COMPILER   "C:/Program Files/LLVM/bin/clang.exe")
set(CMAKE_CXX_COMPILER "C:/Program Files/LLVM/bin/clang++.exe")
set(CMAKE_RC_COMPILER "C:/Program Files/LLVM/bin/llvm-rc.exe")

# where is the target environment located
set(CMAKE_FIND_ROOT_PATH
        "C:/Program Files/LLVM" # I dont know why this is here, I thought it was in the below folder
        "C:/llvm"               # ninja is still here, but nothing else.
)

# adjust the default behavior of the FIND_XXX() commands:
# search programs in the host environment
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# search headers and libraries in the target environment
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
