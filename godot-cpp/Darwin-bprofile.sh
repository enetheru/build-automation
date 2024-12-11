#!/bin/zsh

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Using default environment"
    return
fi

gitBranch="build_profile"
buildDir="$buildRoot/cmake-build"

function Prepare {
    H1 "prepare"
    if [ "$fresh" -eq 1 ]; then doFresh="--fresh"; else unset doFresh; fi

    mkdir -p "$buildDir"
    cd "$buildDir" || return 1

    H1 "CMake Configure"
    Format-Eval "cmake $dofresh .. -DCMAKE_BUILD_TYPE=Release -DGODOT_ENABLE_TESTING=YES -DGODOT_BUILD_PROFILE=\"../test/build_profile.json\""
}

function Build {
    H1 "CMake Build"
    if [ "$verbose" -eq 1 ]; then doVerbose="--verbose"; else unset doVerbose; fi
    if [ $jobs -gt 0 ]; then doJobs="-j $jobs"; else unset doJobs; fi

    cd "$buildDir" || return 1

    # Build
    targets=("template_debug" "template_release" "editor")
    for target in "${targets[@]}"; do
        Format-Eval "cmake --build . $doJobs $doVerbose -t godot-cpp.test.$target"
    done
}
