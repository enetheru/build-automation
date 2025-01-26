from pathlib import Path
from share.format import *

# MARK: Testing
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ ████████ ███████ ███████ ████████ ██ ███    ██  ██████                     │
# │    ██    ██      ██         ██    ██ ████   ██ ██                          │
# │    ██    █████   ███████    ██    ██ ██ ██  ██ ██   ███                    │
# │    ██    ██           ██    ██    ██ ██  ██ ██ ██    ██                    │
# │    ██    ███████ ███████    ██    ██ ██   ████  ██████                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

def godotcpp_test( config:dict ) -> bool:
    print( figlet( 'Testing', {'font': 'small'}) )

    # FIXME use fresh to delete the .godot folder

    test_project_dir = Path(config['source_dir']) / 'test/project'
    dot_godot_dir = test_project_dir / '.godot'
    if not dot_godot_dir.exists():
        h4('Generating the .godot folder')
        cmd_chunks = [
            config['godot_e'],
            '-e',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        # TODO redirect stdout to null
        print_eval(' '.join(cmd_chunks), dry=config['dry'])

    if not dot_godot_dir.exists():
        print('Error: Creating .godot folder')
        return True

    h4("Run the test project")
    cmd_chunks = [
        config['godot_tr'],
        f'--path "{test_project_dir}"',
        '--quit',
        '--headless'
    ]
    # TODO Capture the output of the command
    print_eval(' '.join(cmd_chunks), dry=config['dry'])

    # Because of the capture of stdout for the variable, we need to tee it to a
    # custom file descriptor which is being piped to stdout elsewhere.
    # result="$($godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
    #         | tee >(cat >&5))"

    # Split the result into lines, skip the empty ones.
    # declare -a lines=()
    # while IFS=$'\n' read -ra line; do
    # if [ -n "${line//[[:space:]]/}" ]; then
    # lines+=("$line")
    # fi
    # done <<< "$result"

    # printf "%s\n" "${lines[@]}" >> "$targetRoot/summary.log"

    # returns true if the last line includes PASSED
    # [[ "${lines[-1]}" == *"PASSED"* ]]
    return False
