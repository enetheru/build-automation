# MSYS2 Build Preparation

set -xv

echo $MSYSTEM - $(uname -a)

FRESH=
GODOTCPP=/c/build/godot-cpp
GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe
GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe

