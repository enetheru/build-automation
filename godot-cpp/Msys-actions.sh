#!/bin/bash

# Configuration variables and functions to pass the main script
# Note, the main script is bash, so this needs to conform to bash standards.
if [ "$1" = "get_config" ]; then
    gitUrl=${gitUrl:-"http://github.com/enetheru/godot-cpp.git"}
    gitBranch=${gitBranch:-"master"}

    function CleanLog {
        H3 "This is a generic CleanLog function."

        # replace these tokens with newlines
        splitOn=" && | -- "

        # Lines to ignore
        notMatch='notmatch'
        notMatch+='|^scons:' #'rm -f|vcxproj'
        notMatch+='|^  Removing.*'

        notMatch+="|cmake.exe -E rm -f"

        # Lines to keep
        lineMatch='  . (cmake|scons)' # Commands to keep
        lineMatch+='| == (Config|Target)'           # Info to keep
        lineMatch+='|example\.cpp'
        lineMatch+='|editor_plugin_registration\.cpp'
        lineMatch+='|libgodot-cpp\.windows.*?x86_64\.a'

        # Erase prefixes and junk from lines
        erase="=="
        erase+="|\[[0-9]+\/[0-9]+\] "           # removes cmake things like: [1/5]
        erase+='|C:\\msys64\\clang64\\bin\\'    # Location of msys bin path
        erase+='|C:\\msys64\\ucrt64\\bin\\'     # Location of msys bin path
        erase+='|C:\/build\/godot-cpp\/Msys-clang64-windows\/'
        erase+='|C:\/build\/godot-cpp\/Msys-ucrt64-windows\/'
        erase+='|C:\/msys64\/ucrt64\/bin\/x86_64-w64-mingw32-' # ucrt detected compiler prefixes

        # re-join lines who's options had a space in them
        joins='(Target|Config):'
        joins+='|-E|-j|--build|-t|--target|--config'   # CMake/SCons
        joins+='|-o|-MT|-MF'         # gcc Options
        joins+='|\/D'                 # MSVC Options
        joins+="|-arch|-framework|-isysroot|-install_name"

        # Ignore default options and options that dont effect the build to cut down on the noise
        ignore='-MD|-MT|-MF'
        ignore+='|󰞷'

        # Default Windows Libs Linked with cmake
        ignore+='|-lkernel32|-luser32|-lgdi32|-lwinspool|-lshell32|-lole32|-loleaut32|-luuid|-lcomdlg32|-ladvapi32'

        # object files on their own line
        ignore+='|^.*\.o(bj)?$'

        newLines='^cmake$|^scons$|^clang\+\+$|^ar$|^.*exe$|^g\+\+$|^gcc-ar$'

        sed -E "s/$splitOn/\n/g" "$1" \
            | sed -En "/$notMatch/d;/$lineMatch/p" \
            | sed -E "s/$erase//g" \
            | sed -E 's/ +/\n/g' \
            | sed -E ":start
                \$!N; s/($joins)\n/\1 /;t start
                P;D" \
            | sed -E "/$ignore/d" \
            | sed -E "s/($newLines)/\n\1/" \
            | sed 'N; /^\n$/d;P;D' # remove empty lines
    }

    return
fi

# bash defaults
set -e          # error and quit when( $? != 0 )
set -u          # error and quit on unbound variable
set -o pipefail # halt when a pipe failure occurs
#set -x          # execute and print

# Setup a secondary file descriptor for piping to stdout so that we can split stdout
# to console, and continue to pipe it to commands
exec 5>&1

source "$root/share/format.sh"
source "$root/share/build-actions.sh"

trap 'echo "Script Failure";Finalise \(${stats[*]}\); exit 1' 1 2 3 6 14 15

#### Setup our variables

if [ -z "${root:-}" ]; then exit 1; fi
if [ -z "${script:-}" ]; then exit 1; fi

if [ "${platform:-}" = "Darwin" ]; then
    jobs=${jobs:-$(( $(sysctl -n hw.ncpu) -1 ))}
else
    jobs=${jobs:-$(( $(nproc) -1 ))}
fi
verbose="${verbose:-1}"

targetRoot=${targetRoot:-$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )}

config="${config:-${script%.*}}"

buildRoot="$targetRoot/$config"

godot="/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe"
godot_tr="/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe"

#### Write Summary ####

SummariseConfig

# Add custom things to Summary
echo "
  MSYSTEM     = $MSYSTEM
  godot       = $godot
  godot_tr    = $godot_tr"

cd "$targetRoot" || return 1

# Host Platform Values and Functions
source "$root/share/build-actions.sh"

function PrepareScons {
    echo TODO
}

function TestCommon {
    local result

    Figlet "Test"

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

# override build actions
source "$targetRoot/$script"

declare -a stats=()
for item in "fetch" "prepare" "build" "test"; do
    [ ! "$item" ] && AArrayUpdate stats $item "Fail"
done

H3 "$config - Processing"

DefaultProcess

H3 "$config - completed"
Finalise "${stats[@]}"