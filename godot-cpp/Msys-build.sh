#!/bin/bash
# shellcheck disable=SC2154
set -Ee

declare -a argv=("${BASH_SOURCE[0]}")
argv+=("$1")

prev_dir=$(pwd)

target="godot-cpp"
platform=$(basename "$(uname -o)")

H2 "Build $target using $platform"

echo "
  command     = ${argv[*]}
  fresh build = $fresh
  skip tests  = $doTest
  log append  = $logAppend
  pattern     = $regexFilter"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "${argv[0]}" )" &> /dev/null && pwd )
echo "
  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot"

cd "$targetRoot"

# Set pattern variable from first argument
if [ -n "${argv[1]}" ]; then
    pattern="${argv[1]}"
    echo "  pattern     = $regexFilter"
fi

# Get script count
declare -a buildScripts
buildScripts=( \
    $(find . -maxdepth 1 -type f -name "$platform*" -printf "%f\n" \
    | grep -e "$regexFilter" \
    | grep -v build ))

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
      Error "Msys based build scripts must be source-able with no side effects
      except the declaration of the variable 'msysEnv' matching one of the msys
      environments"
      exit 1
    fi

    # Processing of the actual commands must be done in a separate script so we can pass it on
    # to the MSYS2 Environment shell.
    action="$targetRoot/$platform-build-action.sh"
    declare -a vars
    vars+=("root='$root'")
    vars+=("script='$script'")
    vars+=("gitBranch='$gitBranch'")
    /msys2_shell.cmd -"$msysEnv" -defterm -no-start -where "$targetRoot" -c "${vars[*]} $action"
done

cd "$prev_dir"
