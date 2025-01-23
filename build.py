#!/usr/bin/env python
import argparse
import multiprocessing
import platform
import importlib.util
import sys

from datetime import datetime
from typing import IO

import rich
from rich.console import Console
from rich.table import Table

# Local Imports
from share.ConsoleMultiplex import ConsoleMultiplex
from share.env_commands import *

console = ConsoleMultiplex()
rich._console = console

# MARK: Options
parser = argparse.ArgumentParser(prog='Build-Automation', description='Builds Things', epilog='Build All The Things!!')

parser_io = parser.add_argument_group('io')
parser_io.add_argument('-q', '--quiet', action='store_true')  # Supress output
parser_io.add_argument('--list', action='store_true')  # only list configs do not process
# Text Logger Option
parser_io.add_argument('--append', action='store_true')  # Append to the logs rather than clobber

# Filter which project/configurations get built.
parser_filter = parser.add_argument_group('project filter')
parser_filter.add_argument('--project', default='*')
parser_filter.add_argument('--filter', default='.*')

# Process actions
parser_actions = parser.add_argument_group('actions')
parser_actions.add_argument('-u', '--update', action='store_true')  # Update tools
parser_actions.add_argument('-f', '--fetch', action='store_true')  # Fetch latest source
parser_actions.add_argument('-c', '--clean', action='store_true')  # clean the build directory
parser_actions.add_argument('-p', '--prepare', action='store_true')  # prepare the build
parser_actions.add_argument('-b', '--build', action='store_true')  # build the source
parser_actions.add_argument('-t', '--test', action='store_true')  # test

# Options for actions, but I want to split this up into per action options
parser_opts = parser.add_argument_group('action options')
parser_opts.add_argument('--dry', action='store_true')
parser_opts.add_argument('--fresh', action='store_true')  # re-fresh the configuration
parser_opts.add_argument('-j', '--jobs', type=int, default=(multiprocessing.cpu_count() - 1) or 1)
parser_opts.add_argument('--gitUrl', default='')  # The Url to clone from
parser_opts.add_argument('--gitHash', default='')  # the Commit to checkout

# Create the namespace before parsing, so we can add derived options from the system
bargs = argparse.Namespace()

bargs.command = ' '.join(sys.argv)
bargs.platform = platform.system()
bargs.root_dir = pathlib.Path(__file__).parent

#re-define print_eval to take the global dry command.
from share.format import print_eval as print_eval_base
def print_eval( command ):
    print_eval_base( command, dry=project_config.dry)

# Log everything to a file
log_path = bargs.root_dir / 'build_log.txt'
console.tee(Console( file=open(log_path, 'w'), force_terminal=True), 'build_log' )

# Add all the things from the command line
parser.parse_args(namespace=bargs)

def get_interior_dict( subject )->dict:
    return { k:v for k,v in subject.__dict__.items()}

# ================[ Main Heading and Options ]=================-
console.set_window_title("AutoBuild")
h1("AutoBuild")
h3("Options", newline=False)

for k,v in get_interior_dict(bargs).items():
    print(f'  {k:14s}= {v}')

# MARK: Configs
# ==================[ Import Configurations ]==================-
project_glob = f'{bargs.project}/config.py'

print()
h4(f'Load Config Files using file glob: {project_glob}')

# Import project_config files.
config_imports:dict = {}
project_configs:dict = {}
for config_file in bargs.root_dir.glob(project_glob):
    # get the name of the project
    project_name = os.path.basename(config_file.parent)
    # Create Module Spec
    spec = importlib.util.spec_from_file_location(name='config', location=config_file)
    # import module
    config = importlib.util.module_from_spec(spec)
    # load module
    spec.loader.exec_module(config)
    # add to config dictionary
    config_imports[f'{project_name}'] = config
    project_configs[f'{project_name}'] = config.project_config

for project_name, project_config in project_configs.items():
    build_configs:dict = project_config.build_configs
    # Filter the configs in the project to match the filter criteria
    project_config.build_configs = {k: v for k, v in build_configs.items() if re.search(bargs.filter, v.name)}

# keep only projects which have a build config.
project_configs = {k: v for k, v in project_configs.items() if len(v.build_configs)}

h3('projects and Configs')
if not len(project_configs):
    print("[red]No project/config matches criteria[/red]")
    exit()

for project_name, project_config in project_configs.items():
    build_configs:dict = project_config.build_configs
    print('  - ', project_name)
    for build_name, build_config in build_configs.items():
        print('    - ', build_name)


# List only.
if bargs.list:
    exit()

# MARK: Defaults
# ====================[ Default Commands ]=====================-
# FIXME There really are only two commands, the environment one and the clean one.
#   I need for these to be set
# TODO set the default platform environment command

def clean_log(raw_file: IO, clean_file: IO):
    clean_file.write("Dummy clean function copies first 10 lines")
    for i in range(10):
        line = raw_file.readline()
        clean_file.write( line )

# MARK: pProject
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                         ___          _        _                       │
# │ | _ \_ _ ___  __ ___ ______ | _ \_ _ ___ (_)___ __| |_                     │
# │ |  _/ '_/ _ \/ _/ -_|_-<_-< |  _/ '_/ _ \| / -_) _|  _|                    │
# │ |_| |_| \___/\__\___/__/__/ |_| |_| \___// \___\__|\__|                    │
# │                                        |__/                                │
# ╰────────────────────────────────────────────────────────────────────────────╯
# TODO Setup a keyboard interrupt to cancel a job and exit the loop, rather than quit the whole script.
for project_name, project_config in project_configs.items():
    # ================[ project Config Overrides ]==================-
    for k,v in get_interior_dict(bargs).items():
        if not getattr(project_config, k, False):
            setattr(project_config, k, v)

    project_config.project_name = project_name

    project_config.project_root = project_config.root_dir / f'{project_name}'
    os.chdir(project_config.project_root)

    # =====================[ stdout Logging ]======================-
    os.makedirs(project_config.project_root.joinpath(f'logs-raw'), exist_ok=True)
    os.makedirs(project_config.project_root.joinpath(f'logs-clean'), exist_ok=True)

    # Tee stdout to log file.
    log_path = project_config.project_root / f"logs-raw/{project_name}.txt"
    log_file = open(log_path, 'a' if project_config.append else 'w', buffering=1, encoding="utf-8")
    console.tee(Console(file=log_file, force_terminal=True), project_name)

    # ================[ project Heading / Config ]==================-
    h2(project_name)
    print(figlet(project_name, {'font': 'standard'}))
    for k,v in get_interior_dict( project_config ).items():
        if k == 'build_configs':
            print( f'  {k:14s}=')
            for s in v.keys():
                print( f'    {s}')
            continue
        print(f'  {k:14s}= {v}')

    # ====================[ Git Clone/Update ]=====================-
    if project_config.fetch:
        h3("Git Update/Clone Bare Repository")
        bare_git_path = project_config.project_root / 'git'
        if not bare_git_path.exists():
            print_eval(f'git clone --bare "{project_config.gitUrl}" "{bare_git_path}"')
        else:
            print_eval(f'git --git-dir="{bare_git_path}" fetch --force origin *:*')
            print_eval(f'git --git-dir="{bare_git_path}" log -1 --pretty=%B')
            print_eval(f'git --git-dir="{bare_git_path}" worktree list')
            print_eval(f'git --git-dir="{bare_git_path}" worktree prune')

    # MARK: pBuildConfig
    # ╭────────────────────────────────────────────────────────────────────────────╮
    # │  ___                          ___           __ _                           │
    # │ | _ \_ _ ___  __ ___ ______  / __|___ _ _  / _(_)__ _                      │
    # │ |  _/ '_/ _ \/ _/ -_|_-<_-< | (__/ _ \ ' \|  _| / _` |                     │
    # │ |_| |_| \___/\__\___/__/__/  \___\___/_||_|_| |_\__, |                     │
    # │                                                 |___/                      │
    # ╰────────────────────────────────────────────────────────────────────────────╯
    for build_name, build_config in project_config.build_configs.items():
        # =================[ Build Heading / Config ]==================-
        console.set_window_title(f'{project_name} - {build_name}')
        print('\n', centre( f'- Started: {build_name} -', fill('=', 80)))

        # =================[ Build Config Overrides ]==================-
        # update from project config
        h4('Update Configuration')
        for k,v in get_interior_dict(project_config).items():
            if k in ['build_configs']: continue # Dont copy the list of build configs.
            if v or k not in get_interior_dict(build_config).keys():
                setattr(build_config, k, v)

        # additional overrides
        build_config.config_name = build_config.name
        build_config.source_dir = build_config.project_root / build_config.name
        script_path = build_config.project_root / f'{build_config.name}.py'

        #[======================[ Format and Save Build Script ]======================]
        h4('Processing Build Script')
        script = python_preamble( build_config ) + build_config.script.format(**get_interior_dict(build_config))
        with open( script_path, 'w') as file:
            file.write( script )

        #[==========================[ Shell / Environment ]==========================]
        h4('Determine Shell Environment')
        env_command:list = list() # reset variable from previous loop
        if 'shell' in get_interior_dict(build_config).keys() and build_config.shell in shells.keys():
            print(f'    Using: {build_config.shell}')
            env_command = shells[build_config.shell].copy()
            env_command += [f'python "{script_path}"']
        else:
            print(f'    config missing key: shell, bailing on config.')
            continue

        # =====================[ stdout Logging ]======================-
        h4('Configure Logging')
        log_path = build_config.project_root / f"logs-raw/{build_config.name}.txt"
        log_file = open(log_path, 'a' if build_config.append else 'w', buffering=1, encoding="utf-8")
        console.tee(Console(file=log_file, force_terminal=True), build_config.name)

        # ====================[ Run Build Script ]=====================-
        h3("Run")
        print( ' '.join( env_command ) )

        stats = {'start_time': datetime.now()}
        build_config.stats = stats
        proc = subprocess.Popen( env_command,
                                 encoding='utf-8',
                                 stderr=subprocess.STDOUT,
                                 stdout=subprocess.PIPE)
        with proc:
            # FIXME pretty sure this evaluates after the command is completed
            #   It would be nicer if this was evaluated in realtime
            for line in proc.stdout:
                print(line.rstrip())
                # TODO I can watch for print statements here which assign statistics.
                # FIXME if line.startswith('scrape_this|'):
                #     eval(line.split('|')[1], globals(), locals() )


        # TODO create a timeout for the processing, something reasonable.
        #   this should be defined in the build config as the largest possible build time that is expected.
        #   that way it can trigger a check of the system if it is failing this test.

        stats['status'] = 'Completed' if not proc.returncode else 'Failed'
        stats['end_time'] = datetime.now()
        stats['duration'] = stats['end_time'] - stats['start_time']

        table = Table(highlight=True, min_width=80, show_header=False)
        table.add_row(build_config.name, f'{stats['status']}', f'{stats['duration']}',
                      style='red' if stats['status'] == 'Failed' else 'green' )
        print( table )

        console.pop(build_config.name)

        h3("Post Run Actions")
        h4('Clean Log')
        cleanlog_path = build_config.project_root / f"logs-clean/{build_config.name}.txt"
        with open(log_path, 'r', encoding='utf-8') as log_raw, open(cleanlog_path, 'w', encoding='utf-8') as log_clean:
            clean_log(log_raw, log_clean)

        print(centre( f'Completed: {build_config.name}', fill(' -', 80)))

    # remove the project output log.
    console.pop(project_name)

# MARK: Post
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                          ██████   ██████  ███████ ████████                             ║
# ║                          ██   ██ ██    ██ ██         ██                                ║
# ║                          ██████  ██    ██ ███████    ██                                ║
# ║                          ██      ██    ██      ██    ██                                ║
# ║                          ██       ██████  ███████    ██                                ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
table = Table(title="Stats", highlight=True, min_width=80)

table.add_column("Project/Config", style="cyan", no_wrap=True)
table.add_column("Status")
table.add_column("Time")

for project_name, project_config in project_configs.items():
    for build_name, build_config in project_config.build_configs.items():
        table.add_row(
            f'{project_name}/{build_name}',
            f'{build_config.stats['status']}',
            f'{build_config.stats['duration']}',
        style='red' if build_config.stats['status'] == 'Failed' else 'green')

print( table )

console.pop('build_log')