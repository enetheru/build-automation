from pathlib import Path
from share.format import *

# MARK: Git Fetch
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║           ██████  ██ ████████     ███████ ███████ ████████  ██████ ██   ██             ║
# ║          ██       ██    ██        ██      ██         ██    ██      ██   ██             ║
# ║          ██   ███ ██    ██        █████   █████      ██    ██      ███████             ║
# ║          ██    ██ ██    ██        ██      ██         ██    ██      ██   ██             ║
# ║           ██████  ██    ██        ██      ███████    ██     ██████ ██   ██             ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def git_fetch( config:dict ):
    print( figlet( 'Git Fetch', {'font': 'small'}) )
    print(f'  gitURL={config['gitUrl']}')
    print(f'  gitHash={config['gitHash']}')

    # Create worktree is missing
    if not pathlib.Path(config['source_dir']).exists():
        h4("Create WorkTree")
        cmd_chunks = [
            'git',
            f'--git-dir="{Path(config['project_root']) / 'git'}"',
            'worktree', 'add', f'-d "{config['source_dir']}"'
        ]
        print_eval( ' '.join(cmd_chunks), dry=config['dry'] )
    else:
        h4("Update WorkTree")

    # Update worktree
    os.chdir( config['source_dir'])
    print_eval( f'git checkout --force -d { config['gitHash'] }', dry=config['dry'] )
    print_eval( 'git log -1', dry=config['dry'] )

    print( centre( ' Git Fetch finished ', fill('- ') ) )


# MARK: SCons Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║ ███████  ██████  ██████  ███    ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ██      ██    ██ ████   ██ ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████ ██      ██    ██ ██ ██  ██ ███████     ██████  ██    ██ ██ ██      ██   ██     ║
# ║      ██ ██      ██    ██ ██  ██ ██      ██     ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████  ██████  ██████  ██   ████ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def scons_build( config:dict ):
    print( figlet( 'SCons Build', {'font': 'small'}) )

    scons:dict = config['scons']
    jobs = config['jobs']

    if 'build_dir' in scons.keys():
        build_dir = Path( scons['build_dir'] )
        if not build_dir.is_absolute():
            build_dir = Path(config['source_dir']) / build_dir
    else:
        build_dir = Path( config['source_dir'] )

    os.chdir( build_dir )

    # requires SConstruct file existing in the current directory.
    if not (build_dir / 'SConstruct').exists():
        print(f'[red]Missing SConstruct in {build_dir}')
        raise 'Missing SConstruct'

    cmd_chunks = [
        'scons',
        f'-j {jobs}' if jobs > 0 else None,
        'verbose=yes' if config['quiet'] is False else None,
    ]
    if 'build_vars' in scons.keys():
        cmd_chunks += scons['build_vars']

    for target in scons['targets']:
        h3(f'Building {target}')
        build_command:str = ' '.join(filter(None, cmd_chunks))
        build_command += f' target={target}'

        print_eval( build_command, dry=config['dry'] )

    print( centre( ' SCons build finished ', fill('- ') ) )


# MARK: CMake Prep
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║    ██████ ███    ███  █████  ██   ██ ███████     ██████  ██████  ███████ ██████        ║
# ║   ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██   ██ ██      ██   ██       ║
# ║   ██      ██ ████ ██ ███████ █████   █████       ██████  ██████  █████   ██████        ║
# ║   ██      ██  ██  ██ ██   ██ ██  ██  ██          ██      ██   ██ ██      ██            ║
# ║    ██████ ██      ██ ██   ██ ██   ██ ███████     ██      ██   ██ ███████ ██            ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def cmake_configure( config:dict ):
    cmake = config['cmake']

    source_dir = Path( config['source_dir'] )

    os.chdir( source_dir )

    # requires CMakeLists.txt file existing in the current directory.
    if not (source_dir / 'CMakeLists.txt').exists():
        raise f'Missing CMakeLists.txt in {source_dir}'

    # determine build directory
    if 'build_dir' in cmake.keys():
        build_dir = Path(cmake['build_dir'])
    else:
        build_dir = Path('build-cmake')

    if not build_dir.is_absolute():
        cmake['build_dir'] = build_dir = source_dir / build_dir

    # Create Build Directory
    if not build_dir.is_dir():
        h4(f"Creating {build_dir}")
        os.mkdir( build_dir )

    os.chdir( build_dir )

    config_command = [
        'cmake',
        '--fresh' if config['fresh'] else None,
        '--log-level=VERBOSE' if not config['quiet'] else None,
        f'-S "{source_dir}"',
        f'-B "{build_dir}"']

    if 'config_vars' in cmake.keys():
        config_command += cmake['config_vars']

    print( figlet( 'CMake Configure', {'font': 'small'}) )

    print_eval( ' '.join(filter(None, config_command)), dry=config['dry'] )

    print( centre( ' CMake Configure Completed ', fill('- ') ) )

# MARK: CMake Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║  ██████ ███    ███  █████  ██   ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ██      ██ ████ ██ ███████ █████   █████       ██████  ██    ██ ██ ██      ██   ██     ║
# ║ ██      ██  ██  ██ ██   ██ ██  ██  ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║  ██████ ██      ██ ██   ██ ██   ██ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def cmake_build( config:dict ):
    jobs:int = config['jobs']
    cmake:dict = config['cmake']

    # requires CMakeLists.txt file existing in the current directory.
    if not (Path(cmake['build_dir']) / 'CMakeCache.txt').exists():
        print(f'Missing CMakeCache.txt in {cmake['build_dir']}')
        raise 'Missing CMakeCache.txt'

    chunks =  [
        'cmake',
        f'--build "{cmake['build_dir']}"',
        f'-j {jobs}' if jobs > 0 else None,
        '--verbose' if not config['quiet'] else None,
    ]

    if 'build_vars' in cmake.keys():
        chunks += cmake['build_vars']

    for target in cmake['targets']:
        build_command:str = ' '.join(filter(None, chunks))
        build_command += f' --target {target}'

        if 'tool_vars' in cmake.keys():
            build_command += ' ' + ' '.join(filter(None, cmake['tool_vars']))

        print( figlet( 'CMake Build', {'font': 'small'}) )
        print_eval( build_command, dry=config['dry'] )

    print( centre( ' CMake Build Completed ', fill('- ') ) )