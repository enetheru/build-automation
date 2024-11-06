#Build Preparation, Generic Variables, and all that.
$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

$godotcpp="C:\build\godot-cpp"
$fresh=

$buildRoot="$godotcpp\$hostTarget"
$buildDir="$buildRoot\cmake-build"
$testProject="$buildRoot\test\project"

# clone or update branch
git clone -b modernise c:\Godot\src\godot-cpp $buildRoot
cd $buildRoot

git reset --hard origin
git pull

# Build godot-cpp-test
New-Item -Path $buildDir -ItemType Directory -Force  
cd $buildDir

# C:\msys64\msys2_shell.cmd -defterm -no-start -e "/c/build/godot-cpp/msys2-ucrt64-cmake-w64.sh"
