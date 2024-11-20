#!/bin/zsh
# shellcheck disable=SC2154,SC1090
set -Ee
prev_dir=$(pwd)

godot=/Users/enetheru/build/godot/macos-master-tr/bin/godot.macos.editor.arm64
godot_tr=/Users/enetheru/build/godot/macos-master-tr/bin/godot.macos.template_release.arm64

gitUrl=http://github.com/enetheru/godot-cpp.git
gitBranch="modernise"


H2 " Build $target using $platform "
if test -n "$BASH" ; then script=$BASH_SOURCE
elif test -n "$TMOUT"; then script=${.sh.file}
elif test -n "$ZSH_NAME" ; then script=${(%):-%x}
elif test ${0##*/} = dash; then x=$(lsof -p $$ -Fn0 | tail -1); script=${x#n}
else script=$0
fi

thisScript="$(basename "$script")"
echo "  thisScript  = $thisScript"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "$script}" )" &> /dev/null && pwd )
echo "  targetRoot  = $targetRoot"
cd "$targetRoot"

# Set pattern variable from first argument
if [ -n "${argv[1]}" ]; then
    pattern="${argv[1]}"
else
    pattern='.*'
fi
echo "  pattern     = $pattern"

# Get script count
declare -a buildScripts
buildScripts=($(find . -maxdepth 1 -type f -name "${platform}*" -print \
    | grep -e "$pattern" \
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
    # Clean up key artifacts to trigger rebuild
    # rg -u --files "$buildRoot" \
        # | rg "(memory|example).*?o(bj)?$" \
        # | xargs rm

    local prev
    prev="$(pwd)"

    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    artifacts+=("$(rg -u --files | rg "(memory|example).*?o(bj)?$")")
    artifacts+=("$(rg -u --files | rg "\.(a|lib|so|dll|dylib)$")")

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

#TestCommon(){
#    local result
#    H1 "Test" >&5
#
#    # generate the .godot folder
#    $godot -e --path "$buildRoot/test/project/" --quit --headless &> /dev/null
#    
#    # Run the test project
#    result=$( \
#        $godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
#            | tee >(cat >&5) \
#        )
#    H2 "Test - $config"
#    printf "%s\n" "$result"
#    echo "$result" | rg "PASSED" > /dev/null 2>&1
#}

TestCommon(){
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

        if ! Fetch;     then Error "Fetch Failure"  ; continue; fi
        if ! Prepare;   then Error "Prepare Failure"; continue; fi
        if ! Build;     then Error "Build Failure"  ; continue; fi
        if ! Test 5>&1; then Error "Test Failure"   ; fi
        if ! Clean;     then Error "Clean Failure"  ; fi
        
        H3 "Completed - $config"
    } 2>&1 | tee "$traceLog"

    matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern "$traceLog" | sed -E 's/ +/\n/g' \
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > "$cleanLog"
done

cd "$prev_dir"
