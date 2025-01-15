#!/usr/bin/env python
import argparse
import multiprocessing
import platform
import importlib.util
import sys

from datetime import datetime
from typing import IO

# Local Imports
from share.pipe import Pipe
from share.format import *
from share.env_commands import *

out_pipe = Pipe()
stdout = sys.stdout
sys.stdout = out_pipe

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

# Log everything to a file
log_path = bargs.root_dir / 'build_log.txt'
out_pipe.tee(open(log_path, 'w'), 'build_log')

# Add all the things from the command line
parser.parse_args(namespace=bargs)

def get_interior_dict( subject )->dict:
    return { k:v for k,v in subject.__dict__.items()}

# ================[ Main Heading and Options ]=================-
terminal_title("Build Automation")
h1("AutoBuild")
h3("Options", newline=False)

for k,v in get_interior_dict(bargs).items():
    print(f'  {k:14s}= {v}')

# MARK: Configs
# ==================[ Import Configurations ]==================-

h3('projects and Configs')
h4("Load Config Files")
project_glob = f'{bargs.project}/config.py'
print('  using file glob: ', project_glob)

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

if not len(project_configs):
    print("No project/config matches criteria")
    exit()

h4("list project/config")
for project_name, project_config in project_configs.items():
    build_configs:dict = project_config.build_configs
    print('  project: ', project_name)
    for build_name, build_config in build_configs.items():
        print('    ', build_name)


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
        clean_file.write(raw_file.readline())


# MARK: Process
# ╓────────────────────────────────────────────────────────────────────────────╖
# ║         ██████  ██████   ██████   ██████ ███████ ███████ ███████           ║
# ║         ██   ██ ██   ██ ██    ██ ██      ██      ██      ██                ║
# ║         ██████  ██████  ██    ██ ██      █████   ███████ ███████           ║
# ║         ██      ██   ██ ██    ██ ██      ██           ██      ██           ║
# ║         ██      ██   ██  ██████   ██████ ███████ ███████ ███████           ║
# ╙────────────────────────────────────────────────────────────────────────────╜

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
    out_pipe.tee(log_file, project_name)

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

    # Process Configs
    # MARK: pConfig
    for build_name, build_config in project_config.build_configs.items():
        for k,v in get_interior_dict(project_config).items():
            if k in ['build_configs']: continue # Dont copy the list of build configs.
            setattr(build_config, k, v)

        # =================[ Build Config Overrides ]==================-
        build_config.config_name = build_config.name
        build_config.build_root = build_config.project_root / build_config.name

        # Add env_type if it doesnt exist.
        if 'env_type' not in get_interior_dict(build_config):
            build_config.env_type = ''

        # env_command
        env_commmand = []
        match build_config.env_type:
            case 'python':
                env_command = python_command(get_interior_dict(build_config), build_config.env_script )
            case 'powershell':
                env_command = pwsh_command(get_interior_dict(build_config), build_config.env_script )
            case _:
                env_command = python_command(get_interior_dict(build_config),
                'print( "A build Environment command was not set." )' )

        # =====================[ stdout Logging ]======================-
        log_path = build_config.project_root / f"logs-raw/{build_config.name}.txt"
        log_file = open(log_path, 'a' if build_config.append else 'w', buffering=1, encoding="utf-8")
        out_pipe.tee(log_file, build_config.name)

        # =================[ Build Heading / Config ]==================-
        print('\n', centre(f'[ {build_config.name} ]', fill('- ', 80)))
        terminal_title(f'{project_name} - {build_name}')
        for k,v in get_interior_dict( build_config ).items():
            if k == 'env_command':
                print(f'  {k:14s}= {v[0]} ...')
                continue
            print(f'  {k:14s}= {v}')


        # ====================[ Run Build Script ]=====================-
        h3("Run")
        print( ' '.join( env_command ) )

        build_config.stats = {'start_time': datetime.now()}
        with subprocess.Popen( env_command,
                               stderr=subprocess.STDOUT,
                               stdout=subprocess.PIPE) as proc:
            # FIXME pretty sure this evaluates after the command is completed
            #   It would be nicer if this was evaluated in realtime
            for line_bytes in proc.stdout:
                line = line_bytes.decode('utf8').rstrip()
                print(line)
                # TODO I can watch for print statements here which assign statistics.
                # FIXME if line.startswith('scrape_this|'):
                #     eval(line.split('|')[1], globals(), locals() )


        # TODO create a timeout for the processing, something reasonable.
        #   this should be defined in the build config as the largest possible build time that is expected.
        #   that way it can trigger a check of the system if it is failing this test.

        build_config.stats['status'] = 'Completed'
        build_config.stats['end_time'] = datetime.now()
        build_config.stats['duration'] = build_config.stats['end_time'] - build_config.stats['start_time']

        h3(f'{build_config.project_name}/{build_config.name} - Statistics')
        for k, v in build_config.stats.items():
            print(f"  {k:14} = {v}")

        out_pipe.pop(build_config.name)

        h3("Post Run Actions")
        h4('Clean Log')
        cleanlog_path = build_config.project_root / f"logs-clean/{build_config.name}.txt"
        with open(log_path, 'r') as log_raw, open(cleanlog_path, 'w') as log_clean:
            clean_log(log_raw, log_clean)

        print(fill(' -'))

    # remove the project output log.
    out_pipe.pop(project_name)

# MARK: Post
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                          ██████   ██████  ███████ ████████                             ║
# ║                          ██   ██ ██    ██ ██         ██                                ║
# ║                          ██████  ██    ██ ███████    ██                                ║
# ║                          ██      ██    ██      ██    ██                                ║
# ║                          ██       ██████  ███████    ██                                ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
h3("Final Stats")
print(f'  {"original_command":14} = {bargs.command}')
for project_name, project_config in project_configs.items():
    print(f'  {project_name}')
    for build_name, build_config in project_config.build_configs.items():
        print(f'    {build_name:60s} - {build_config.stats['duration']}')

out_pipe.pop('build_log')
