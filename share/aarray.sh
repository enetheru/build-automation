##################################- [A]Array -##################################
 #                                                                            #
 #          ███  █████  ███  █████  ██████  ██████   █████  ██    ██          #
 #          ██  ██   ██  ██ ██   ██ ██   ██ ██   ██ ██   ██  ██  ██           #
 #          ██  ███████  ██ ███████ ██████  ██████  ███████   ████            #
 #          ██  ██   ██  ██ ██   ██ ██   ██ ██   ██ ██   ██    ██             #
 #          ███ ██   ██ ███ ██   ██ ██   ██ ██   ██ ██   ██    ██             #
 #                                                                            #
################################################################################

#### Associative arrays ####
# Because macos is using a really old version of bash I cant use associative
# arrays in my base build script.

function AArrayUpdate {
    if [ -z "${1:-}" ]; then echo "no array name given"; exit 1; fi
    if [ -z "${2:-}" ]; then echo "no key given"; exit 1; fi
    if [ -z "${3:-}" ]; then echo "no value given"; exit 1; fi

    declare -n array=$1
    key=${2//\"/}
    value=${3//\"/}

    size=${#array[@]}

    declare -i new=1
    declare -i i=0
    if [ "$size" -gt 0 ]; then
        for (( i=0; i<size; i++ )); do
            pair="${array[$i]}"
            pKey="${pair%:*}"
#            pValue="${pair#*:}"
            if [ "$key" = "$pKey" ]; then
                new=0
                break
            fi
        done
    fi

    # Add new key
    if [ -n "$key" ] && [ $new -eq 1 ]; then
        array+=("${key}:${value}")
    fi

    # Update key
    if [ -n "$key" ] && [ $new -eq 0 ]; then
        array[i]="${key}:${value}"
    fi
}

function AArrayGet {
    if [ -z "${1:-}" ]; then echo "no arrayName given"; exit 1; fi
    if [ -z "${2:-}" ]; then echo "no key given"; exit 1; fi

    declare -n array=$1
    key=${2//\"/}

    size=${#array[@]}
    if [ "$size" -eq 0 ]; then echo "empty array"; exit 1; fi

    for (( i=0; i<size; i++ )); do
        pair="${array[$i]}"
        pKey="${pair%:*}"
        pValue="${pair#*:}"
        if [ "$key" == "$pKey" ]; then
            echo "${pValue}"
            return
        fi
    done
}