# Build Commands for godot-cpp

This document lists the build commands used for these subfolders.

I updated all the ones that rely on my changes using this command
```bash
for I in */; do cd $I; git pull; cd ..; done
```

```powershell
Get-ChildItem -Directory | ForEach-Object -Parallel { cd $_ ; git pull; cd .. }
```

## msvc.scons
```powershell
# Clone godot-cpp
cd C:\build\godot-cpp
git clone c:\Godot\src\godot-cpp msvc.scons
cd msvc.scons

# Compile the test project
cd test
scons -j 12 verbose=yes target=template_release

# Generate the .godot folder
$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
&$godot -e --path .\project\ --headless --quit *>$null

# Run test project
$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"
&$godot_tr --path .\project\ --headless --quit
```

## msvc.cmake
```powershell
# Clone godot-cpp
cd C:\build\godot-cpp
git clone c:\Godot\src\godot-cpp msvc.cmake
cd msvc.cmake

# Compile the test project
mdkdir cmake-build
cd cmake-build
cmake ../ && cmake --build . --verbose -t godot-cpp-test --config Release

# Generate the .godot folder
$godot = C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe
$godot -e --path ..\test\project\ --headless --quit *>$null

# Run the test project
$godot_tr = C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe
$godot_tr --path ..\test\project\ --headless --quit
```

## ucrt64.scons
```bash
# Clone godot-cpp
cd /c/build/godot-cpp
git clone /c/Godot/src/godot-cpp ucrt64.scons
cd ucrt64.scons

# Compile the test project
cd test
scons -j 12 verbose=yes target=template_release use_mingw=yes
 
# generate the .godot folder
GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe
$GODOT -e --path ..\test\project\ --quit --headless 2&> /dev/null 

# Run the test project
GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe
$GODOT_TR --path ..\test\project\ --quit --headless
```

## ucrt64.cmake

```bash
# Clone godot-cpp
cd /c/build/godot-cpp
git clone /c/Godot/src/godot-cpp ucrt64.cmake
cd ucrt64.cmake

# Compile the test project
mkdir cmake-build
cd cmake-build
cmake ../ && cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# generate the .godot folder
GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe
$GODOT -e --path ..\test\project\ --quit --headless 2&> /dev/null 

# Run the test project
GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe
$GODOT_TR --path ..\test\project\ --quit --headless
```

## clang64.scons

```bash
# Clone godot-cpp
cd /c/build/godot-cpp
git clone /c/Godot/src/godot-cpp clang64.scons
cd clang64.scons

# Compile the test project
cd test
scons -j 12 verbose=yes target=template_release use_mingw=yes use_llvm=yes
 
# generate the .godot folder
GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe 
$GODOT -e --path project/ --quit --headless 2&> /dev/null

# Run the test project
GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe
$GODOT_TR --path project/ --quit --headless
```

## clang64.cmake
```bash
# Clone godot-cpp
cd /c/build/godot-cpp
git clone /c/Godot/src/godot-cpp clang64.cmake
cd clang64.cmake

# Compile the test project
mkdir cmake-build
cd cmake-build
cmake ../ && cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# generate the .godot folder
GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe
$GODOT -e --path ../test/project/ --quit --headless 2&> /dev/null 

# Run the test project
GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe
$GODOT_TR --path ../test/project/ --quit --headless
```

## clion.cmake
Built using the inbuilt toolchain and clion features

Then opened terminal to project dir.
```powershell
PowerShell 7.4.6
PS C:\build\godot-cpp\clion.cmake> $godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
PS C:\build\godot-cpp\clion.cmake> &$godot -e --path .\test\project\ --headless --quit *>$null            
PS C:\build\godot-cpp\clion.cmake> $godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"             
PS C:\build\godot-cpp\clion.cmake> &$godot_tr --path .\test\project\ --headless --quit
```
Tests passed.

## android.scons
```powershell
# Clone godot-cpp
cd C:\build\godot-cpp
git clone c:\Godot\src\godot-cpp android.scons
cd android.scons

# Compile the test project
cd test
scons -j 12 verbose=yes platform=android target=template_release arch=x86_64

# TODO Testing
```

## android.cmake

```powershell
# Clone godot-cpp
cd C:\build\godot-cpp
git clone c:\Godot\src\godot-cpp android.cmake
cd android.cmake

# Compile godot-cpp-test
mkdir cmake-build
cd cmake-build
cmake ../ -GNinja --toolchain C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake -DANDROID_PLATFORM=android-29 -DANDROID_ABI=x86_64
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# TODO Testing
```

## emscripten.scons

```powershell
# Start emcmdprompt and change to ps
C:\emsdk\emcmdprompt.bat
pwsh.exe

# clone godot-cpp
cd C:\build\godot-cpp
git clone c:\Godot\src\godot-cpp emsdk.scons
cd emsdk.scons

# Compile godot-cpp-test
cd test
scons -j 12 verbose=yes platform=web target=template_release

# TODO Test
```

## emscripten.cmake

```powershell
# Start emcmdprompt and change to ps
C:\emsdk\emcmdprompt.bat
pwsh.exe

# clone godot-cpp
cd C:\build\godot-cpp
git clone c:\Godot\src\godot-cpp emsdk.cmake
cd emsdk.cmake

# Compile godot-cpp-test
> mkdir cmake-build
> cd cmake-build
> emcmake.bat cmake ../
> cmake --build . -j 12 --verbose -t template_release --config Release

# TODO Test
```
