from share.script_preamble import *

# MARK: Testing
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ ████████ ███████ ███████ ████████ ██ ███    ██  ██████                     │
# │    ██    ██      ██         ██    ██ ████   ██ ██                          │
# │    ██    █████   ███████    ██    ██ ██ ██  ██ ██   ███                    │
# │    ██    ██           ██    ██    ██ ██  ██ ██ ██    ██                    │
# │    ██    ███████ ███████    ██    ██ ██   ████  ██████                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

def godotcpp_test( config:dict ) -> bool:
    from subprocess import SubprocessError

    opts = config['opts']
    build = config['build']
    print( h2( 'Testing') )

    # FIXME use fresh to delete the .godot folder
    godot_editor = build['godot_e']
    godot_release_template = build['godot_tr']

    test_project_dir = build['source_path'] / 'test/project'
    dot_godot_dir = test_project_dir / '.godot'
    if not dot_godot_dir.exists():
        print( h1('Generating the .godot folder') )
        cmd_chunks = [
            f'"{godot_editor}"',
            '-e',
            f'--path "{test_project_dir}"',
            '--quit',
            '--headless'
        ]
        # TODO redirect stdout to null
        try:
            stream_command(' '.join(cmd_chunks), dry=opts['dry'])
        except SubprocessError as e:
            print( '[red]Godot exited abnormally during .godot folder creation')

    if not dot_godot_dir.exists() and not opts['dry']:
        print('Error: Creating .godot folder')
        return True

    print( h1("Run the test project") )
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
            dry=opts['dry'],
            stdout_handler=handle_stdout,
            stderr_handler=handle_stderr )
    except SubprocessError as e:
        result = e
        # FIXME Godot seems to exit with an error code for some reason on cmake builds only.
        #   I have to investigate why that might be.
        print( '[red]Error: Godot exited abnormally when running the test project')
        print( '    This requires investigation as it appears to only happen in cmake builds')

    from rich.panel import Panel
    rich.print(
        '',
        Panel( '\n'.join( output ),  expand=False, title='Test Execution', title_align='left', width=120 ),
        '')

    if opts['dry']:
        return False

    for line in output:
        if line.find( 'PASSED' ) > 0:
            print( h1( 'Test Succeeded' ) )
            return False

    return True
