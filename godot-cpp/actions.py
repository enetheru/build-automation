from pathlib import Path

from share.format import *
from share.run import stream_command


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
    godot_editor = Path(config['godot_e'])
    godot_release_template = Path(config['godot_tr'])

    test_project_dir = Path(config['source_dir']) / 'test/project'
    dot_godot_dir = test_project_dir / '.godot'
    if not dot_godot_dir.exists():
        h4('Generating the .godot folder')
        cmd_chunks = [
            f'"{godot_editor}"',
            '-e',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        # TODO redirect stdout to null
        try:
            stream_command(' '.join(cmd_chunks), dry=config['dry'])
        except subprocess.SubprocessError as e:
            print( '[red]Godot exited abnormally during .godot folder creation')

    if not dot_godot_dir.exists():
        print('Error: Creating .godot folder')
        return True

    h4("Run the test project")
    cmd_chunks = [
        f'"{godot_release_template}"',
        f'--path "{test_project_dir}"',
        '--quit',
        '--headless'
    ]
    output = ['']
    def handle_stdout( msg ):
        output.append( f'{msg}' )
        # print( msg )
    def handle_stderr( msg ):
        output.append( f'[red]{msg}[/red]' )
        # print( msg )
    try:
        result = stream_command(
            ' '.join(cmd_chunks),
            dry=config['dry'],
            stdout_handler=handle_stdout,
            stderr_handler=handle_stderr )
    except subprocess.SubprocessError as e:
        result = e
        # FIXME Godot seems to exit with an error code for some reason on cmake builds only.
        #   I have to investigate why that might be.
        print( '[red]Error: Godot exited abnormally when running the test project')
        print( '    This requires investigation as it appears to only happen in cmake builds')

    from rich.panel import Panel
    print(
        '',
        Panel( '\n'.join( output ),  expand=False, title='Test Execution', title_align='left', width=120 ),
        '')

    for line in output:
        if line.find( 'PASSED' ) > 0:
            h4( 'Test Succeeded' )
            return False

    return True
