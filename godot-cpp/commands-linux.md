
## godot-master


## scons
```bash
# Clone godot-cpp
cd ~/build/godot-cpp
git clone /c/Godot/src/godot-cpp linux-scons
cd linux.scons

# Compile the test project
cd test
scons verbose=yes target=template_release
 
# generate the .godot folder
GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe
$GODOT -e --path ..\test\project\ --quit --headless 2&> /dev/null 

# Run the test project
GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe
$GODOT_TR --path ..\test\project\ --quit --headless
```

Working on getting the toolchain for emscripten and android working.

on arch linux

extra/emscripten doesnt appear to provide the things requred.

trying aur/emsdk

ok the aur pckage dies, looks like I just needed to logout and back in again to
fresh my environment.. I hve the tools available now.
