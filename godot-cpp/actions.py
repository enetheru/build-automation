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
    if not pathlib.Path(config['build_root']).exists():
        h3("Create WorkTree")
        print_eval( f'git --git-dir="{Path(config['project_root']) / 'git'}" worktree add -d "{config['build_root']}"' )
    else:
        h3("Update WorkTree")

    # Update worktree
    os.chdir( config['build_root'])
    print_eval( f'git checkout --force -d { config['gitHash'] }' )
    print_eval( 'git log -1' )


# MARK: SCons Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║ ███████  ██████  ██████  ███    ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ██      ██    ██ ████   ██ ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████ ██      ██    ██ ██ ██  ██ ███████     ██████  ██    ██ ██ ██      ██   ██     ║
# ║      ██ ██      ██    ██ ██  ██ ██      ██     ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████  ██████  ██████  ██   ████ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def build_scons( config:dict, build_vars:list = [] ):
    name = config['config_name']
    project = config['project_name']
    build_root = Path( config['build_root'] )
    jobs = config['jobs']

    os.chdir( build_root )

    # requires SConstruct file existing in the current directory.
    if not (build_root / 'SConstruct').exists():
        raise f'Missing SConstruct in {build_root}'

    do_jobs = f'-j {jobs}' if jobs > 0 else None
    do_verbose = 'verbose=yes' if config['quiet'] is False else None

    build_vars = [do_jobs, do_verbose] + build_vars

    print( figlet( name, {'font': 'small'}) )
    h3(f'Config: { name }')
    h3(f'project: {project}')

    print_eval( f'scons {' '.join(filter(None, build_vars))}', dry=config['dry'] )

    h3('BuildScons Completed')

    fill('-')


# MARK: CMake Prep
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║    ██████ ███    ███  █████  ██   ██ ███████     ██████  ██████  ███████ ██████        ║
# ║   ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██   ██ ██      ██   ██       ║
# ║   ██      ██ ████ ██ ███████ █████   █████       ██████  ██████  █████   ██████        ║
# ║   ██      ██  ██  ██ ██   ██ ██  ██  ██          ██      ██   ██ ██      ██            ║
# ║    ██████ ██      ██ ██   ██ ██   ██ ███████     ██      ██   ██ ███████ ██            ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

def prepare_cmake( config:dict, prep_vars:list = [] ) -> dict:
    build_root = Path( config['build_root'] )

    os.chdir( build_root )

    # requires CMakeLists.txt file existing in the current directory.
    if not (build_root / 'CMakeLists.txt').exists():
        raise f'Missing CMakeLists.txt in {build_root}'

    # Check for build_dir
    if 'build_dir' in config.keys():
        build_dir = config['build_dir']
    else:
        config['build_dir'] = build_dir = build_root / 'cmake_build'

    # Create Build Directory
    if not build_dir.is_dir():
        h4("Creating $buildDir")
        os.mkdir( build_dir )

    os.chdir( build_dir )

    do_fresh = '--fresh' if config['fresh'] else None
    # do_verbose = '--verbose' if not config['quiet'] else None
    # prep_vars = [do_fresh, do_verbose] + prep_vars

    print( figlet( 'CMake Configure', {'font': 'small'}) )

    returncode = print_eval( f'cmake .. {' '.join(filter(None, prep_vars))}', dry=config['dry'] )

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

def build_cmake( config:dict, build_vars:list = [] ) -> dict:
    jobs = config['jobs']

    # requires CMakeLists.txt file existing in the current directory.
    if not Path('CMakeCache.txt').exists():
        raise f'Missing CMakeCache.txt in {os.getcwd()}'

    build_vars = [
                     f'-j {jobs}' if jobs > 0 else None,
                     '--verbose' if not config['quiet'] else None
                 ] + build_vars

    print( figlet( 'CMake Build', {'font': 'small'}) )

    returncode = print_eval( f'cmake --build . {' '.join(filter(None, build_vars))}', dry=config['dry'] )

    h3('CMake Build Completed')

    fill('-')
    return {'returncode':returncode}
