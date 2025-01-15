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
            'status': 'Fail',
            'start_time': datetime.now(),
            'end_time': 'dnf',
            'duration': 'dnf'
        })
        # FIXME print( f"scrape_this|build_config.stats['{self.stats['name']}']='started'")

    def __enter__(self):
        stats = self.stats
        h3(f'Starting {stats['name']}')
        stats['start_time'] = datetime.now()
        return self

    def __exit__(self, *exc):
        stats = self.stats
        stats['end_time'] = datetime.now()
        stats['duration'] = stats['end_time'] - stats['start_time']
        stats['status'] = 'OK'
        h4(f"Finished {stats['name']} - Duration: {stats['duration']}")
        # FIXME  print( f"scrape_this|build_config.stats['{self.stats['name']}']={repr(stats['duration'])}")
        return False

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



def build_scons( config:dict, build_vars:list = [] ):
    name = config['config_name']
    project = config['project_name']
    build_root = Path( config['build_root'] )
    jobs = config['jobs']

    os.chdir( build_root )

    # requires SConstruct file existing in the current directory.
    # SCons - Remove generated source files if exists.
    if not (build_root / 'SConstruct').exists():
        raise f'Missing SConstruct in {build_root}'

    do_jobs = f'-j {jobs}' if jobs > 0 else None
    do_verbose = 'verbose=yes' if config['quiet'] is False else None

    build_vars = [do_jobs, do_verbose] + build_vars

    figlet( name, {'font': 'small'})
    h3(f'Config: { name }')
    h3(f'project: {project}')

    print_eval( f'scons {' '.join(filter(None, build_vars))}', dry=config['dry'] )

    h3('BuildScons Completed')

    fill('-')