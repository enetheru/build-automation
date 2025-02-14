Shared Files
============
So long as there is no config.py in the folder then it wont be picked up.
This is a place to put all the infra that I need to share between scripts.


Toolchains
==========

I needed a place to put the toolchains I have on my computer and a way to
document them without polluting them.

```sh
# SCons command for msvc build
> scons verbose=yes

# SCons command for gcc/clang build
> scons verbose=yes use_mingw=yes

# CMake commands
> cmake ../
> cmake --build . --verbose -t godot-cpp-test
```

## Microsoft Visual Studio 17 2022

No special requirements, cmake will pick it up as the default if run from a
powershell cmdline

"binaryDir" : "${sourceDir}/cmake-build-msvc"

## MSYS2/ucrt64

Uses the the gcc compiler, and links to microsoft's universal c run-time.

Run all commands from within the ucrt64 msys terminal, it set's up all the
things required.

"binaryDir" : "${sourceDir}/cmake-build-ucrt64"

## MSYS2/clang64

Uses the the LLVM/clang compiler, and links to microsoft's universal c run-time.

Run all commands from within the clang64 msys terminal, it set's up all the
things required.

"binaryDir" : "${sourceDir}/cmake-build-clang64",
