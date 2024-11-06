#TODO make the Tee-Object -Append option configurable.

$godotcpp = "C:\build\godot-cpp"
cd $godotcpp

rg -u --files | rg "memory.*o(bj)?" | ForEach-Object { rm $_ }
rg -u --files | rg "example.*o(bj)?" | ForEach-Object { rm $_ }
rg -u --files | rg "\.dll$" | ForEach-Object { rm $_ }
rg -u --files | rg "\.so$" | ForEach-Object { rm $_ }
rg -u --files | rg "\.wasm$" | ForEach-Object { rm $_ }

function Build-Target {
    param(
        $hostTarget
    )

    $buildScript="$godotcpp\$hostTarget.ps1"
    $traceLog="$godotcpp\$hostTarget.txt"
    pwsh -nop -File $buildScript | Tee-Object -FilePath $traceLog
}

$hostTargetList = @(
    'w64-cmake-msvc-w64'
    'w64-cmake-android'
    'w64-cmake-web'
);

foreach ($hostTarget in $hostTargetList)
{
    Build-Target -HostTarget $hostTarget
}


# Build using msys2
# UCRT64
@'
$msys2_shell="C:\msys64\msys2_shell.cmd -defterm -no-start -where C:\build\godot-cpp"
cmd /c $msys2_shell -ucrt64 -e /c/build/godot-cpp/msys2-ucrt64-cmake-w64.sh 2>&1
'@ | pwsh -nop -NoProfile -Command - | Tee-Object -FilePath "$godotcpp\msys2-ucrt64-cmake-w64.txt"

# CLANG64
@'
$msys2_shell="C:\msys64\msys2_shell.cmd -defterm -no-start -where C:\build\godot-cpp"
cmd /c $msys2_shell -clang64 -e /c/build/godot-cpp/msys2-clang64-cmake-w64.sh 2>&1
'@ | pwsh -nop -NoProfile -Command - | Tee-Object -FilePath "$godotcpp\msys2-clang64-cmake-w64.txt"
