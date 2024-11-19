#!/bin/bash
set -Ee

declare -i columns=120
source "$root/share/format.sh"

H2 "using $script ..."
echo "  MSYSTEM     = $MSYSTEM"

config="${script%.*}"



#export gitUrl=http://github.com/enetheru/godot-cpp.git
export gitUrl="C:\godot\src\godot-cpp"
export gitBranch="modernise"

echo "
  gitUrl      = $gitUrl
  gitBranch   = $gitBranch"

godot="/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe"
godot_tr="/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe"

echo "
  godot       = $godot
  godot_tr    = $godot_tr"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )

traceLog="$targetRoot/logs-raw/${config}.txt"
cleanLog="$targetRoot/logs-clean/${config}.txt"
echo "
  traceLog    = $traceLog
  cleanLog    = $cleanLog"

# Some steps are identical.
PrepareCommon(){
    local prev=$(pwd)
    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    artifacts+=($(rg -u --files \
        | rg "(memory|example).*?o(bj)?$"))
    artifacts+=($(rg -u --files \
        | rg "\.(a|lib|so|dll|dylib)$"))

    if [ -n "${artifacts[*]}" ]; then
      H3 "Prepare"
      Warning "Deleting key Artifacts"
      for item in "${artifacts[@]}"; do
        echo "rm '$item'"
        rm "$item"
      done
    fi
    cd "$prev"
}

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

TestCommon(){
    H1 "Test" >&5

    printf "\n" >> "$targetRoot/summary.log"
    H4 "$config" >> "$targetRoot/summary.log"

    # generate the .godot folder
    Format-Command "$godot -e --path \"$buildRoot/test/project/\" --quit --headless"
    $godot -e --path "$buildRoot/test/project/" --quit --headless &> /dev/null
    
    # Run the test project
    local result
    Format-Command "$godot_tr --path \"$buildRoot/test/project/\" --quit --headless"
    result=$( $godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
            | tee >(cat >&5) )

    H2 "Test - $config"
    printf '%s' "$result"
    echo "$result" | rg "PASSED" > /dev/null 2>&1
}

cd "$targetRoot"

# Process and Log Actions
{
    H2 "Processing - $config"

    buildRoot="$targetRoot/$config"
    echo "  Build Root = $buildRoot"

    source "$root/share/build-actions.sh"
    source "$targetRoot/$script"

    if ! Fetch;   then Error "Fetch Failure"  ; exit 1; fi
    if ! Prepare; then Error "Prepare Failure"; exit 1; fi
    if ! Build;   then Error "Build Failure"  ; exit 1; fi
    if ! Test;    then Error "Test Failure"   ; fi
    if ! Clean;   then Error "Clean Failure"  ; fi

    H3 "Completed - $config"
} 2>&1 | tee "$traceLog"

matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
rg -M2048 $matchPattern "$traceLog" | sed -E 's/ +/\n/g' \
    | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > "$cleanLog"
