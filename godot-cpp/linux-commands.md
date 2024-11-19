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
