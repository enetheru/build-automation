#!/bin/zsh

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

cd "$targetRoot" || return 1
config="${script%.*}"
buildRoot="$targetRoot/$config"

gitUrl=${gitUrl:-"http://github.com/enetheru/godot.git"}
gitHash=${gitHash:-"master"}

# Get the target root from this script location
# targetRoot=${targetRoot:-$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )}

declare -i columns=120
source "$root/share/format.sh"

H2 " Build $target using $platform "
echo "
  envActions  = 
  buildScript = $script

  fetch       = $fetch
  configure   = $configure
  build       = $build
  test        = $test

  procNum     = $jobs
  fresh build = $fresh
  log append  = $append

  target      = $target
  gitUrl      = $gitUrl
  gitHash     = $gitHash

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  buildRoot   = $buildRoot"

# Source Generic Variables and Actions.
source "$root/share/build-actions.sh"

# Define Common Variables and Overrides

# Source Config Override Variables and Actions
source "$targetRoot/$script"

H3 "Processing - $config"

if [ "$fetch" -eq 1 ]; then
  if ! Fetch;     then Error "Fetch Failure"  ; exit 1; fi
fi

if [ "$configure" -eq 1 ]; then
  if ! Prepare;   then Error "Prepare Failure"; exit 1; fi
fi

if [ "$build" -eq 1 ]; then
  if ! Build;     then Error "Build Failure"  ; exit 1; fi
fi

if [ "$test" -eq 1 ]; then
  if ! Test 5>&1; then Error "Test Failure"   ; fi
fi

if ! Clean;     then Error "Clean Failure"  ; fi

H2 "Completed - $config"

# TODO print Stats

