#!/usr/bin/env python
import argparse
import copy
import multiprocessing
import platform
import importlib.util
import re
import sys
from datetime import datetime
from typing import IO

# Local Imports
from share.pipe import Pipe
from share.format import *

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

# Filter which target/configurations get built.
parser_filter = parser.add_argument_group('target filter')
parser_filter.add_argument('--target', default='*')
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
log_path = bargs.root_dir.joinpath('build_log.txt')
out_pipe.tee(open(log_path, 'w'), 'build_log')

# Add all the things from the command line
parser.parse_args(namespace=bargs)

def print_config(config: argparse.Namespace):
    for arg_key, arg_value in config.__dict__.items():
        print(f'  {arg_key:14s}= {arg_value}')
        if arg_key in ['root_dir', 'append', 'filter', 'test', 'gitHash']:
            print('')


# ########################    Process Parameter Flags    ########################

if not (bargs.fetch or bargs.prepare or bargs.build or bargs.test):
    bargs.list = True

# redefine print_eval so that we can do dry runs.
from share.format import print_eval as print_and_evaluate


def print_eval(message):
    print_and_evaluate(message, bargs.dry)


#############################    Print Summary    #############################
h1("AutoBuild")
terminal_title("Build Automation")
h3("Options")

print_config(bargs)

# MARK: Configs
#############################    load configurations    #############################
target_configs = {}
h3('Targets and Configs')
h4("Load Configurations")
target_glob = f'{bargs.target}/{bargs.platform}.config.py'
print('  using file glob: ', target_glob)

# Import target_config files.
for config_file in bargs.root_dir.glob(target_glob):
    # get the name of the target
    target_name = os.path.basename(config_file.parent)
    # Create Module Spec
    spec = importlib.util.spec_from_file_location(name='config', location=config_file)
    # import module
    target_config = importlib.util.module_from_spec(spec)
    # load module
    spec.loader.exec_module(target_config)
    # add to config dictionary
    target_configs[f'{target_name}'] = target_config

for target_name, target_config in target_configs.items():
    # Filter the configs in the target to match the filter criteria
    target_config.build_configs = [c for c in target_config.build_configs if re.search( bargs.filter, c.name )]

# keep only targets which have a build config.
target_configs = { k: v for k, v in target_configs.items() if len(v.build_configs) }

if not len(target_configs):
    print( "No target/config matches criteria")
    exit()

h4( "list target/config" )
for target_name, target_config in target_configs.items():
    print('  target: ', target_name)
    for build_config in target_config.build_configs:
        print('    ', build_config.name)

# List only.
# FIXME this is temporarily disabled for testing.
# if bargs.list:
#     exit()

# MARK: Defaults
#############################    Default Actions    #############################
actions = ['env', 'update', 'fetch', 'clean', 'prepare', 'build', 'test', 'relog']


def clean_log( raw_file:IO, clean_file:IO ):
    clean_file.write("Dummy clean function copies first 10 lines")
    for i in range(10):
        clean_file.write( raw_file.readline() )



def pwsh_command( defs:dict, command:str ) -> list:
    mini_script = ''
    for k, v in defs.items():
        mini_script += f'${k}="{v}"\n'
    mini_script += command
    return ['pwsh', '-Command', mini_script]

# MARK: Process
# ╓────────────────────────────────────────────────────────────────────────────╖
# ║         ██████  ██████   ██████   ██████ ███████ ███████ ███████           ║
# ║         ██   ██ ██   ██ ██    ██ ██      ██      ██      ██                ║
# ║         ██████  ██████  ██    ██ ██      █████   ███████ ███████           ║
# ║         ██      ██   ██ ██    ██ ██      ██           ██      ██           ║
# ║         ██      ██   ██  ██████   ██████ ███████ ███████ ███████           ║
# ╙────────────────────────────────────────────────────────────────────────────╜

# TODO Setup a keyboard interrupt to cancel a job and exit the loop, rather than quit the whole script.

for target_name, target_config in target_configs.items():
    # base config options are mutable, so lets restore for each target.
    targs = copy.deepcopy(bargs)

    # TODO per target overrides.
    targs.target_name = target_name

    targs.target_root = targs.root_dir.joinpath(f'{target_name}')
    os.chdir(targs.target_root)

    # Make sure the log directories exist.
    os.makedirs(targs.target_root.joinpath(f'logs-raw'), exist_ok=True)
    os.makedirs(targs.target_root.joinpath(f'logs-clean'), exist_ok=True)

    # Tee stdout to log file.
    log_path = targs.target_root.joinpath(f"logs-raw/{target_name}.txt")
    log_file = open(log_path, 'a' if targs.append else 'w', buffering=1, encoding="utf-8")
    out_pipe.tee(log_file, target_name)

    h2(target_name)
    print_config(targs)

    # Clone if not already
    if targs.fetch:
        h3("Git Update/Clone Bare Repository")
        bare_git_path = targs.target_root.joinpath('git')
        if not bare_git_path.exists():
            print_eval(f'git clone --bare "{targs.gitUrl}" "{bare_git_path}"')
        else:
            print_eval(f'git --git-dir="{bare_git_path}" fetch --force origin *:*')
            print_eval('git log -1 --pretty=%B')
            print_eval(f'git --git-dir="{bare_git_path}" worktree list')
            print_eval(f'git --git-dir="{bare_git_path}" worktree prune')

    # Process Configs
    for build_config in target_config.build_configs:
        # copy target config, so we dont pollute it.
        cargs = copy.deepcopy(targs)

        # TODO Per Config Overrides.
        cargs.config_name = build_config.name
        build_config.env_command = 'pwsh -c'

        # Tee stdout to log file.
        log_path = targs.target_root.joinpath(f"logs-raw/{build_config.name}.txt")
        log_file = open(log_path, 'a' if targs.append else 'w', buffering=1, encoding="utf-8")
        out_pipe.tee(log_file, build_config.name)

        # Heading
        h2(build_config.name)
        print(figlet("traceLog"))

        print_config(build_config)

        cargs.build_root = cargs.target_root.joinpath(build_config.name)

        h3(f'Processing {target_name}.{build_config.name}')
        terminal_title(f'{target_name} - {build_config.name}')

        print_config(cargs)
        build_config.stats = {'start_time': datetime.now()}

        #FIXME this needs to be set in the configuration, this is a dummy option.
        build_config.env_command = pwsh_command( cargs.__dict__,
            'Write-Host "Hello $target_name - $config_name!"' )

        h3("Run")
        with subprocess.Popen(build_config.env_command, stdout=subprocess.PIPE) as proc:
            for line in proc.stdout:
                # TODO I can watch for print statements here which assign statistics.
                print( line.decode('utf8').rstrip() )

        # TODO create a timeout for the processing, something reasonable.
        #   this should be defined in the build config as the largest possible build time that is expected.
        #   that way it can trigger a check of the system if it is failing this test.

        build_config.stats['status'] = 'Completed'
        build_config.stats['end_time'] = datetime.now()
        build_config.stats['duration'] = build_config.stats['end_time'] - build_config.stats['start_time']

        h3(f'{targs.target_name}/{build_config.name} - Statistics')
        for k,v in build_config.stats.items():
            print( f"  {k:14} = {v}" )

        out_pipe.pop(build_config.name)

        h3( "Post Run Actions" )
        h4('Clean Log')
        cleanlog_path = targs.target_root.joinpath(f"logs-clean/{build_config.name}.txt")
        with open( log_path, 'r' ) as log_raw, open( cleanlog_path, 'w' ) as log_clean:
            clean_log( log_raw, log_clean )

        print( fill( ' -') )

    # remove the target output log.
    out_pipe.pop(target_name)

h3( "Final Stats" )
print( f'  {"original_command":14} = {bargs.command}' )
for target_name, target_config in target_configs.items():
    print( f'  {target_name}' )
    for build_config in target_config.build_configs:
        print( f'    {build_config.name}')
        for k,v in build_config.stats.items():
            print( f"      {k:10} = {v}" )

out_pipe.pop('build_log')