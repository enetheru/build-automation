#!/usr/bin/env bash
# shellcheck disable=SC2154,SC1090
set -Ee
prev_dir=$(pwd)

godot=$root/godot/linux-master/bin/godot.linuxbsd.editor.x86_64
godot_tr=$root/godot/linux-master-tr/bin/godot.linuxbsd.template_release.x86_64

gitUrl=http://github.com/enetheru/godot-cpp.git
gitHash=${gitHash:-"master"}


H2 " Build $target using $platform "
if test -n "$BASH" ; then script=${BASH_SOURCE[0]}
#elif test -n "$TMOUT"; then script=${.sh.file}
#elif test -n "$ZSH_NAME" ; then script=${(%):-%x}
#elif test ${0##*/} = dash; then x=$(lsof -p $$ -Fn0 | tail -1); script=${x#n}
else script=$0
fi

thisScript="$(basename "$script")"
# Defaults
fetch=${fetch:-1}
configure=${configure:-1}
build=${build:-1}
test=${test:-1}

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "$script}" )" &> /dev/null && pwd )

echo "  thisScript  = $thisScript"
echo "  fetch       = $fetch"
echo "  configure   = $configure"
echo "  build       = $build"
echo "  test        = $test"
echo
echo "  fresh       = $fresh"
echo "  append      = $append"
echo
echo "  target      = $target"
echo "  branch      = $gitHash"
echo 
echo "  matches     = $regexFilter"
echo
echo "  godot.editor            = $godot"
echo "  godot.template_release  = $godot_tr"
echo
echo "  gitUrl      = $gitUrl"
echo "  gitHash   = $gitHash"
echo
echo "  platform    = $platform"
echo "  root        = $root"
echo "  targetRoot  = $targetRoot"
echo

cd "$targetRoot"

# Get script count
declare -a buildScripts
buildScripts=($(find . -maxdepth 1 -type f -name "${platform}*" -print \
    | grep -e "$regexFilter" \
    | grep -v "build" ))

echo "  Script count: ${#buildScripts}"

#Fail if no scripts
if [ ${#buildScripts} -eq 0 ]; then
    echo
    echo "  ${RED}Error: No build scripts found${NC}"
    cd "$prev_dir"
    exit 1
fi

# Print Scripts
echo "  Scripts:"
for script in "${buildScripts[@]}"; do
    echo "    $script"
done

# Make sure the log directories exist.
mkdir -p "$targetRoot/logs-raw"
mkdir -p "$targetRoot/logs-clean"

# Some steps are identical.
PrepareCommon(){
    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    artifacts+=($(rg -u --files | rg "(memory|example).*?o(bj)?$"))
    artifacts+=($(rg -u --files | rg "\.(a|lib|so|dll|dylib)$"))

    if [ ${#artifacts[@]} -gt 0 ]; then
      H3 "Prepare"
      Warning "Deleting key Artifacts"
      for item in "${artifacts[@]}"; do
        echo "rm '$item'"
        rm "$item"
      done
    fi

    if [ ! -d "cmake-build" ]; then
        Format-Command 'mkdir -p "cmake-build"'
        mkdir -p "cmake-build" | exit 1
    fi
}

TestCommon(){
    H3 "Test Disabled"
    return
    local result

    H1 "Test"

    printf "\n" >> "$targetRoot/summary.log"
    H4 "$config" >> "$targetRoot/summary.log"

    if [ ! -d "$buildRoot/test/project/.godot" ]; then
        H4 "Generate the .godot folder"
        Format-Command "$godot -e --path \"$buildRoot/test/project/\" --quit --headless"

        # Capture the output of this one silently because it always fails, and
        # succeeds. We can dump it if it's a real failure.
        result=$($godot -e --path "$buildRoot/test/project/" --quit --headless 2>&1)

        if [ ! -d "$buildRoot/test/project/.godot" ]; then
            echo "$result"
            Error "Creating .godot folder" >> "$targetRoot/summary.log"
            return 1
        fi
    else
        H4 "The .godot folder has already been generated."
    fi

    H4 "Run the test project"
    Format-Command "$godot_tr --path \"$buildRoot/test/project/\" --quit --headless"

    # Because of the capture of stdout for the variable, we need to tee it to a
    # custom file descriptor which is being piped to stdout elsewhere.
    result="$($godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
        | tee >(cat >&5))"

    # Split the result into lines, skip the empty ones.
    declare -a lines=()
    while IFS=$'\n' read -ra line; do
        if [ -n "${line//[[:space:]]/}" ]; then
            lines+=("$line") 
        fi
    done <<< "$result"

    printf "%s\n" "${lines[@]}" >> "$targetRoot/summary.log"

    # returns true if the last line includes PASSED
    [[ "${lines[-1]}" == *"PASSED"* ]]
}

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

# Process Scripts
for script in "${buildScripts[@]}"; do
    cd "$targetRoot"

    config=${script%.*}

    traceLog="$targetRoot/logs-raw/${config}.txt"
    cleanLog="$targetRoot/logs-clean/${config}.txt"
    echo "
  traceLog    = $traceLog
  cleanLog    = $cleanLog"

    buildRoot="$targetRoot/$config"

    source "$root/share/build-actions.sh"
    source "$targetRoot/$script"

    {
        H2 "Processing - $config"
        echo "  Build Root = $buildRoot"

        if [ $fetch -eq 1 ]; then
            if ! Fetch;     then Error "Fetch Failure"  ; return 1; fi
        fi
        if [ $configure -eq 1 ]; then
            if ! Prepare;   then Error "Prepare Failure"; return 1; fi
        fi
        if [ $build -eq 1 ]; then
            if ! Build;     then Error "Build Failure"  ; return 1; fi
        fi
        if [ $test -eq 1 ]; then
            if ! Test 5>&1; then Error "Test Failure"   ; fi
        fi

        if ! Clean;     then Error "Clean Failure"  ; fi
        
        H3 "Completed - $config"
    } 2>&1 | tee "$traceLog"

    matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern "$traceLog" | sed -E 's/ +/\n/g' \
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > "$cleanLog"
done

cd "$prev_dir"
