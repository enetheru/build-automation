#!/bin/bash

# EXIT trap function
function report_error() {
    last_ret_code="$?"
    if [[ $last_ret_code -ne 0 ]]; then
        echo -e "\n\nFAILURE: \"$last_command\" command failed with exit code $last_ret_code.\n" >&2
        exit $last_ret_code
    fi
}

# DEBUG trap function
function debug_tracking() {
    last_command="$current_command"
    current_command=$BASH_COMMAND

    printf "%.0s=" $(seq 1 $(tput cols))
    echo -e "\n\n\n"
    printf "%.0s=" $(seq 1 $(tput cols))
    echo -e "$current_command"
    printf "%.0s." $(seq 1 $(tput cols))
}

# force exit on first failure
set -e

# enable history expansion
set -o history -o histexpand

# call report_error() on exit
trap 'report_error' EXIT

# keep track of the last executed command
trap 'debug_tracking' DEBUG