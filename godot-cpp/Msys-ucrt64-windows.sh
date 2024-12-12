#!/bin/bash
# shellcheck disable=SC2154

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# tell the build command how to run ourselves.
if [ "${1:-}" = "get_env" ]; then
    runArgs=(
        "-ucrt64"
        "-defterm"
        "-no-start"
        "-where $targetRoot"
    )
    envRun="/msys2_shell.cmd ${runArgs[*]} -c"

    return
fi


buildDir="$buildRoot/cmake-build"

function Prepare {

    H1 "Prepare"

    H3 "CMake Configure"
    doFresh=''
    if [ "$fresh" -eq 1 ]; then doFresh="--fresh"; fi

    # Create Build Directory
    if [ ! -d "$buildDir" ]; then
        H4 "Creating $buildDir"
        Format-Eval "mkdir -p $buildDir"
    fi
    cd "$buildDir" || exit 1

    # CMake Configure
    cmakeVars=(
        "-DCMAKE_BUILD_TYPE=Release"
        "-DGODOT_ENABLE_TESTING=YES"
    )

    Format-Eval "cmake $doFresh .. ${cmakeVars[*]}"
}

function Build {
    statArray=(
        "target"
        "duration"
        "size"
    )

    unset doJobs
    if [ "$jobs" -gt 0 ]; then doJobs="-j $jobs"; fi

    arch=$(uname -m)

    targets=(
        "template_release"
        "template_debug"
        "editor"
    )

    # Build Targets using SCons
    unset doVerbose
    if [ "$verbose" -eq 1 ]; then doVerbose="verbose=yes"; fi

    sconsVars=(
        "$doJobs"
        "$doVerbose"
        "use_mingw=yes"
    )

    cd "$buildRoot/test" || return 1
    for target in "${targets[@]}"; do
        H2 "$target"; H1 "Scons Build"
        start=$SECONDS

        Format-Eval "scons ${sconsVars[*]} target=$target"

        statArray+=( "scons.$target $((SECONDS - start)) n/a")
        printf "%s\n%s" "${statArray[0]}" "${statArray[-1]}" | column -t
    done

    # Build Targets using CMake
    unset doVerbose
    if [ "$verbose" -eq 1 ]; then doVerbose="--verbose"; fi

    unset doJobs
    if [ "$jobs" -gt 0 ]; then doJobs="-j $jobs"; fi

    cmakeVars=(
            "$doJobs"
            "$doVerbose"
        )

    cd "$buildRoot" || return 1
    for target in "${targets[@]}"; do
        H2 "$target"; H1 "CMake Build"
        start=$SECONDS

        Format-Eval "cmake --build . ${cmakeVars[*]} -t godot-cpp.test.$target"

        statArray+=( "cmake.$target $((SECONDS - start)) n/a")
        printf "%s\n%s" "${statArray[0]}" "${statArray[-1]}" | column -t
    done

        statArray+=( "cmake.$target $((SECONDS - start)) n/a")
        printf "%s\n" "${statArray[@]}" | column -t
}

