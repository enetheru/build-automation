import os
import time
from datetime import datetime
from contextlib import ContextDecorator
from pathlib import Path

from share.format import *

class Timer(ContextDecorator):
    def __init__(self, container:dict ):
        if not container:
            self.stats = {'name':'timer'}
        else:
            self.stats = container

        self.stats.update(**{
            'status': 'Pending',
            'duration': 'dnf'
        })
        # FIXME print( f"scrape_this|build_config.stats['{self.stats['name']}']='started'")

    def __enter__(self):
        stats = self.stats
        h3(f'Starting {stats['name']}')
        self.start_time = datetime.now()
        self.stats['status'] = 'Started'
        return self

    def __exit__(self, *exc):
        stats = self.stats
        self.end_time = datetime.now()
        stats['duration'] = self.end_time - self.start_time
        stats['status'] = 'Completed'
        h4(f"Finished {stats['name']} - Duration: {stats['duration']}")
        # FIXME  print( f"scrape_this|build_config.stats['{self.stats['name']}']={repr(stats['duration'])}")
        return False

# MARK: Git Fetch
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║           ██████  ██ ████████     ███████ ███████ ████████  ██████ ██   ██             ║
# ║          ██       ██    ██        ██      ██         ██    ██      ██   ██             ║
# ║          ██   ███ ██    ██        █████   █████      ██    ██      ███████             ║
# ║          ██    ██ ██    ██        ██      ██         ██    ██      ██   ██             ║
# ║           ██████  ██    ██        ██      ███████    ██     ██████ ██   ██             ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def git_fetch( config:dict ):
    # Create worktree is missing
    if not pathlib.Path(config['source_dir']).exists():
        h3("Create WorkTree")
        print_eval( f'git --git-dir="{Path(config['project_root']) / 'git'}" worktree add -d "{config['source_dir']}"', dry=config['dry'] )
    else:
        h3("Update WorkTree")

    # Update worktree
    os.chdir( config['source_dir'])
    print_eval( f'git checkout --force -d { config['gitHash'] }', dry=config['dry'] )
    print_eval( 'git log -1', dry=config['dry'] )


# MARK: SCons Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║ ███████  ██████  ██████  ███    ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ██      ██    ██ ████   ██ ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████ ██      ██    ██ ██ ██  ██ ███████     ██████  ██    ██ ██ ██      ██   ██     ║
# ║      ██ ██      ██    ██ ██  ██ ██      ██     ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████  ██████  ██████  ██   ████ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def scons_build( config:dict ):
    scons:dict = config['scons']

    jobs = config['jobs']
    returncode:int=0

    build_dir = Path( scons['build_dir'] )
    if not build_dir.is_absolute():
        build_dir = Path(config['source_dir']) / build_dir

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
        build_command:str = ' '.join(filter(None, cmd_chunks))
        build_command += f' target={target}'

        print( figlet( 'SCons Build', {'font': 'small'}) )
        returncode = print_eval( build_command, dry=config['dry'] )

    h3('BuildScons Completed')

    fill('-')
    return {'returncode':returncode}


# MARK: CMake Prep
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║    ██████ ███    ███  █████  ██   ██ ███████     ██████  ██████  ███████ ██████        ║
# ║   ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██   ██ ██      ██   ██       ║
# ║   ██      ██ ████ ██ ███████ █████   █████       ██████  ██████  █████   ██████        ║
# ║   ██      ██  ██  ██ ██   ██ ██  ██  ██          ██      ██   ██ ██      ██            ║
# ║    ██████ ██      ██ ██   ██ ██   ██ ███████     ██      ██   ██ ███████ ██            ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def cmake_configure( config:dict ) -> dict:
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

    returncode = print_eval( ' '.join(filter(None, config_command)), dry=config['dry'] )

    h3('CMake Configure Completed')

    fill('-')
    return {'returncode':returncode}

# MARK: CMake Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║  ██████ ███    ███  █████  ██   ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ██      ██ ████ ██ ███████ █████   █████       ██████  ██    ██ ██ ██      ██   ██     ║
# ║ ██      ██  ██  ██ ██   ██ ██  ██  ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║  ██████ ██      ██ ██   ██ ██   ██ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def cmake_build( config:dict ) -> dict:
    jobs:int = config['jobs']
    cmake:dict = config['cmake']
    returncode:int=0

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
        returncode = print_eval( build_command, dry=config['dry'] )

    h3('CMake Build Completed')

    fill('-')
    return {'returncode':returncode}
