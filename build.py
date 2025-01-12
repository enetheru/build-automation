#!/usr/bin/env python
import argparse
import multiprocessing
import platform
import importlib.util
import sys
import types

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

bargs.items = types.MethodType( lambda self: [[k,v] for k,v in self.__dict__.items() if k != 'items'], bargs)

def print_config( dict_like ):
    for k, v in dict_like.items():
        if k in ['build_configs', 'env_command']:
            continue
        print(f'  {k:14s}= {v}')
        if k in ['root_dir', 'append', 'filter', 'test', 'gitHash', 'target_root']:
            print('')


# ########################    Process Parameter Flags    ########################
if not (bargs.fetch or bargs.prepare or bargs.build or bargs.test):
    bargs.list = True

# redefine print_eval so that we can do dry runs.
from share.format import print_eval as print_and_evaluate


def print_eval(message):
    print_and_evaluate(message, bargs.dry)


# ================[ Main Heading and Options ]=================-
terminal_title("Build Automation")
h1("AutoBuild")
h3("Options", newline=False)
print_config(bargs)

# MARK: Configs
# ==================[ Import Configurations ]==================-

h3('Targets and Configs')
h4("Load Config Files")
target_glob = f'{bargs.target}/config.py'
print('  using file glob: ', target_glob)

# Import target_config files.
config_imports:dict = {}
target_configs:dict = {}
for config_file in bargs.root_dir.glob(target_glob):
    # get the name of the target
    target_name = os.path.basename(config_file.parent)
    # Create Module Spec
    spec = importlib.util.spec_from_file_location(name='config', location=config_file)
    # import module
    config = importlib.util.module_from_spec(spec)
    # load module
    spec.loader.exec_module(config)
    # add to config dictionary
    config_imports[f'{target_name}'] = config
    target_configs[f'{target_name}'] = config.target_config

# Add the items() method to the target config SimpleNamespace's
for target_name, target_config in target_configs.items():
    target_config.items = types.MethodType( lambda self: [[k,v] for k,v in self.__dict__.items() if k != 'items'], target_config)

    build_configs:dict = target_config.build_configs
    for build_name, build_config in build_configs.items():
        build_config.items = types.MethodType( lambda self: [[k,v] for k,v in self.__dict__.items() if k != 'items'], build_config)


for target_name, target_config in target_configs.items():
    build_configs:dict = target_config.build_configs
    # Filter the configs in the target to match the filter criteria
    target_config.build_configs = {k: v for k, v in build_configs.items() if re.search(bargs.filter, v.name)}

# keep only targets which have a build config.
target_configs = {k: v for k, v in target_configs.items() if len(v.build_configs)}

if not len(target_configs):
    print("No target/config matches criteria")
    exit()

h4("list target/config")
for target_name, target_config in target_configs.items():
    build_configs:dict = target_config.build_configs
    print('  target: ', target_name)
    for build_name, build_config in build_configs.items():
        print('    ', build_name)


# List only.
# FIXME this is temporarily disabled for testing.
# if bargs.list:
#     exit()

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

for target_name, target_config in target_configs.items():
    # ================[ Target Config Overrides ]==================-
    # FIXME targs.__dict__ = target_config.__dict__ | bargs.__dict__
    for k,v in bargs.items():
        if not getattr(target_config, k, False):
            setattr(target_config, k, v)

    target_config.target_name = target_name

    target_config.target_root = target_config.root_dir.joinpath(f'{target_name}')
    os.chdir(target_config.target_root)

    # =====================[ stdout Logging ]======================-
    os.makedirs(target_config.target_root.joinpath(f'logs-raw'), exist_ok=True)
    os.makedirs(target_config.target_root.joinpath(f'logs-clean'), exist_ok=True)

    # Tee stdout to log file.
    log_path = target_config.target_root.joinpath(f"logs-raw/{target_name}.txt")
    log_file = open(log_path, 'a' if target_config.append else 'w', buffering=1, encoding="utf-8")
    out_pipe.tee(log_file, target_name)

    # ================[ Target Heading / Config ]==================-
    h2(target_name)
    print(figlet(target_name, {'font': 'standard'}))
    print_config(target_config)

    # ====================[ Git Clone/Update ]=====================-
    if target_config.fetch:
        h3("Git Update/Clone Bare Repository")
        bare_git_path = target_config.target_root.joinpath('git')
        if not bare_git_path.exists():
            print_eval(f'git clone --bare "{target_config.gitUrl}" "{bare_git_path}"')
        else:
            print_eval(f'git --git-dir="{bare_git_path}" fetch --force origin *:*')
            print_eval('git log -1 --pretty=%B')
            print_eval(f'git --git-dir="{bare_git_path}" worktree list')
            print_eval(f'git --git-dir="{bare_git_path}" worktree prune')

    # Process Configs
    # MARK: pConfig
    for build_name, build_config in target_config.build_configs.items():
        terminal_title(f'{target_name} - {build_name}')

        for k,v in target_config.items():
            setattr(build_config, k, v)

        # =================[ Build Config Overrides ]==================-
        build_config.config_name = build_config.name
        build_config.build_root = build_config.target_root.joinpath(build_config.name)

        # env_command
        if 'env_command' not in build_config.__dict__:
            build_config.env_command = python_command(build_config.__dict__,
                'print( "A build Environment command was not set." )' )

        # =====================[ stdout Logging ]======================-
        log_path = build_config.target_root.joinpath(f"logs-raw/{build_config.name}.txt")
        log_file = open(log_path, 'a' if build_config.append else 'w', buffering=1, encoding="utf-8")
        out_pipe.tee(log_file, build_config.name)

        # =================[ Build Heading / Config ]==================-
        print('\n', centre(f'[ {build_config.name} ]', fill('- ', 80)))
        print_config(build_config)

        # ====================[ Run Build Script ]=====================-
        h3("Run")
        for l in build_config.env_command:
            print( l )

        build_config.stats = {'start_time': datetime.now()}
        with subprocess.Popen(build_config.env_command, stdout=subprocess.PIPE) as proc:
            for line in proc.stdout:
                # TODO I can watch for print statements here which assign statistics.
                print(line.decode('utf8').rstrip())

        # TODO create a timeout for the processing, something reasonable.
        #   this should be defined in the build config as the largest possible build time that is expected.
        #   that way it can trigger a check of the system if it is failing this test.

        build_config.stats['status'] = 'Completed'
        build_config.stats['end_time'] = datetime.now()
        build_config.stats['duration'] = build_config.stats['end_time'] - build_config.stats['start_time']

        h3(f'{build_config.target_name}/{build_config.name} - Statistics')
        for k, v in build_config.stats.items():
            print(f"  {k:14} = {v}")

        out_pipe.pop(build_config.name)

        h3("Post Run Actions")
        h4('Clean Log')
        cleanlog_path = build_config.target_root.joinpath(f"logs-clean/{build_config.name}.txt")
        with open(log_path, 'r') as log_raw, open(cleanlog_path, 'w') as log_clean:
            clean_log(log_raw, log_clean)

        print(fill(' -'))

    # remove the target output log.
    out_pipe.pop(target_name)

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
for target_name, target_config in target_configs.items():
    print(f'  {target_name}')
    for build_name, build_config in target_config.build_configs.items():
        print(f'    {build_name}')
        for k, v in build_config.stats.items():
            print(f"      {k:10} = {v}")

out_pipe.pop('build_log')
