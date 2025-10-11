from share.script_preamble import *

console = rich.console.Console()

# MARK: Git Checkout
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _      ___ _           _            _                              │
# │  / __(_) |_   / __| |_  ___ __| |_____ _  _| |_                            │
# │ | (_ | |  _| | (__| ' \/ -_) _| / / _ \ || |  _|                           │
# │  \___|_|\__|  \___|_||_\___\__|_\_\___/\_,_|\__|                           │
# ╰────────────────────────────────────────────────────────────────────────────╯
# TODO, if the work tree is already upto date, then skip
# TODO Rename source_git to something like checkout, and replace all verbs
def source_git():
    config:dict = {}
    opts:dict = {}
    project:dict = {}
    build:dict = {}
    # start_script

    # MARK: Git-Checkout
    #[=================================[ Source ]=================================]
    from git.exc import GitCommandError
    from rich.panel import Panel
    from rich.padding import Padding as rPadding

    if config['ok'] and 'source' in opts['build_actions']:
        console.set_window_title(f'Source - {build['name']}')
        section = fmt.Section( "Git Checkout" )
        section.start()

        # merge definitions project < build < opts
        srcdef = project.get('srcdef', {}) | build.get('srcdef', {}) | opts.get('srcdef', {})

        # Verify we have cloned the repo.
        gitdir = Path(srcdef.get('gitdir', 'git'))
        if not gitdir.exists():
            fnf = FileNotFoundError()
            fnf.add_note(f'Missing bare git repo path: {gitdir}, project needs to be fetched')
            # TODO Fallback to remote repo
            raise fnf

        repo = git.Repo(gitdir)
        fmt.h(f'git-dir: {gitdir.as_posix()}')

        pattern = srcdef['ref'] if srcdef['remote'] == 'origin' else f'{srcdef['remote']}/{srcdef['ref']}'
        bare_hash : git.RefLog
        try:
            bare_hash = repo.git.log('--format=%h', '-1',  pattern)
            fmt.hu( f'{repo.git.log('--oneline', '-1',  pattern)}' )
        except GitCommandError as e:
            print(e)
            exit(1)

        worktree_path = build['source_path']

        if not worktree_path.exists():
            # Perhaps we deleted the worktree folder, in which case prune it
            cmd_args = [ 'prune',
                '--verbose' if opts['verbose'] else None,
                '--dry-run' if opts['dry'] else None ]
            repo.git.worktree( *filter(None, cmd_args) )

            fmt.h("Create WorkTree")
            os.chdir( gitdir )

            cmd_args = [ 'add', '--detach', worktree_path.as_posix(), pattern ]
            if opts['dry']:
                print(f'dry-run: git worktree {' '.join(filter(None, cmd_args))}')
            else:
                repo.git.worktree( *filter(None, cmd_args) )

        if worktree_path.exists():
            worktree = git.Repo( worktree_path )
            fmt.h(f'worktree: {worktree_path.as_posix()}')

            worktree_hash = worktree.git.log('--format=%h', '-1')
            fmt.hu( f'{worktree.git.log('--oneline', '-1')}' )

            if bare_hash != worktree_hash:
                fmt.h("Updating WorkTree")
                cmd_args = [ '--force', '--detach', pattern ]
                if opts['dry']:
                    print(f'dry-run: git checkout {' '.join(filter(None, cmd_args))}')
                else:
                    worktree.git.checkout( *filter(None, cmd_args) )
            else:
                fmt.h("WorkTree is Up-to-Date")


            console.print( rPadding(
                Panel( worktree.git.log( '-1'),  expand=False, title=pattern, title_align='left', width=120 ),
                (0,0,0,fmt.pad.sizeu()) )
            )

        section.end()
        config['ok'] = True


def show_stats():
    config:dict = {}
    stats:dict = {}
    # start_script

    #[=================================[ Stats ]=================================]
    from rich.table import Table
    table = Table(title="Stats", highlight=True, min_width=80)

    table.add_column("Section", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Duration", style="green")

    for cmd_name, cmd_stats in stats.items():
        table.add_row( cmd_name, f'{cmd_stats['status']}', f'{cmd_stats['duration']}')

    console.print( table )
    if not config['ok']: exit(1)

# MARK: CMake
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ __  __      _         ___         _      _                           │
# │  / __|  \/  |__ _| |_____  / __| __ _ _(_)_ __| |_                         │
# │ | (__| |\/| / _` | / / -_) \__ \/ _| '_| | '_ \  _|                        │
# │  \___|_|  |_\__,_|_\_\___| |___/\__|_| |_| .__/\__|                        │
# │                                          |_|                               │
# ╰────────────────────────────────────────────────────────────────────────────╯

def cmake_check():
    project:dict = {}
    build:dict = {}
    # start_script

    # MARK: CMake-Check
    #[=============================[ CMake-Check ]=============================]
    cmake = build['buildtool']

    source_path = build.setdefault("source_path", project['path'] / build['source_dir'])

    # requires CMakeLists.txt file existing in the current directory.
    if not (source_path / "CMakeLists.txt").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"Missing CMakeLists.txt in {source_path}")
        raise fnf

    build_dir = cmake.setdefault('build_dir', 'cmake-build')
    build_path = cmake.setdefault('build_path', source_path / build_dir )

    # Create Build Directory
    if not build_path.is_dir():
        fmt.t3(f"Creating {cmake['build_dir']}")
        os.mkdir(build_path)

    try:
        os.chdir(build_path)
    except FileNotFoundError as fnf:
        fnf.add_note(f'Missing Folder {build_path}')
        raise fnf

def cmake_configure():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    # MARK: CMake-Configure
    #[===========================[ CMake-Configure ]===========================]
    cmake = build['buildtool']

    if config['ok'] and 'configure' in opts['build_actions']:
        fmt.h2("CMake Configure")
        fmt.s1("CMake Configure")
        console.set_window_title(f'Configure - {build['name']}')

        config_opts = [
            "--fresh" if 'fresh' in opts['build_actions'] else None,
            "--log-level=VERBOSE" if not opts["quiet"] else None,
            f'-S "{build['source_path']}"',
            f'-B "{cmake['build_path']}"',
        ]

        if 'toolchain' in cmake:
            toolchain_file = cmake['toolchain']
            config_opts.append( f'--toolchain "{os.fspath(toolchain_file)}"' )

        if 'generator' in cmake:
            config_opts.append( f'-G "{cmake['generator']}"' )

        if "config_vars" in cmake:
            config_opts += cmake["config_vars"]

        with Timer(name='configure') as timer:
            stream_command(f'cmake {' '.join(filter(None, config_opts))}', dry=opts['dry'])
            print('')

        fmt.send()
        stats['configure'] = timer.get_dict()
        config['ok'] = timer.ok()


def cmake_build():
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    # MARK: CMake-Build
    #[=============================[ CMake-Build ]=============================]
    import copy
    cmake = build['buildtool']

    if config['ok'] and 'build' in opts['build_actions']:
        fmt.t2("CMake Build")
        console.set_window_title('Build - {name}')

        build_path:Path = cmake['build_path']

        build_opts = [
            f'--build {build_path.as_posix()}',
            "--verbose" if not opts["quiet"] else None,
            f"-j {opts['jobs']}",
        ]
        build_opts += cmake.get("build_vars", [])

        with Timer(name='build') as timer:
            targets = ' '.join(cmake.get('targets', []))
            fmt.s2(f" Building targets: {targets or 'default'} ")
            target_opts = copy.copy(build_opts)
            if targets:
                target_opts.append(f" --target {targets}")

            if "tool_vars" in cmake:
                target_opts.append('--')
                target_opts += cmake["tool_vars"]

            stream_command(f'cmake {' '.join(filter(None, target_opts))}', dry=opts["dry"])
            print('')
            # TODO I was working on putting all or no --target arguments rather than looping over them.
            # for target in cmake["targets"]:
            #     s2(f" Building target: {target} ")
            #     target_opts = copy.copy(build_opts)
            #     target_opts.append(f" --target {target}")
            #
            #     if "tool_vars" in cmake:
            #         target_opts.append('--')
            #         target_opts += cmake["tool_vars"]
            #
            #     stream_command(f'cmake {' '.join(filter(None, target_opts))}', dry=opts["dry"])
            #     print('')

        fmt.send()
        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()