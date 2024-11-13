#!/bin/bash
set -Ee

declare -a argv=("${BASH_SOURCE[0]}")
argv+=("$1")

prev_dir=$(pwd)

godot=${godot:-echo}
godot_tr=${godot_tr:-echo}

export gitUrl=http://github.com/enetheru/godot-cpp.git
export gitBranch="modernise"

: "${target:="$( basename "$(dirname -- "${argv[0]}")")"}"
: "${platform:="$( basename "$(uname -o)")"}"
H2 " Build $target using $platform "

echo "  command     = ${argv[*]}"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "${argv[0]}" )" &> /dev/null && pwd )
echo "  targetRoot  = $targetRoot"
cd "$targetRoot"

# Set pattern variable from first argument
if [ -n "${argv[1]}" ]; then
    pattern="${argv[1]}"
    echo "  pattern     = $pattern"
fi

# Get script count
declare -a buildScripts=($(find . -maxdepth 1 -type f -name "$platform*" -printf "%f\n" | grep -v build))
declare -i scriptCount=${#buildScripts[@]}
echo "  Script count: $scriptCount"

#Fail if no scripts
if [ $scriptCount -eq 0 ]; then
    Error "No build scripts found"
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

# Process Scripts
for script in "${buildScripts[@]}"; do
    # shellcheck disable=SC1090
    source "$script" # Fetch the msysEnv variable
    if [ -z "$msysEnv" ]; then
      Error "Msys based build scripts must be sourcable with no side effects except the declaration of
        the variable 'msysEnv' matching one of the msys environments"
      exit 1
    fi

    action="$targetRoot/$platform-build-action.sh"
    vars="root=\"$root\" script=\"$script\""
    /msys2_shell.cmd -"$msysEnv" -defterm -no-start -where "$targetRoot" -c "$vars $action"
done

cd "$prev_dir"
