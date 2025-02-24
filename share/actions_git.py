from share.script_preamble import *
import git

# MARK: Git Checkout
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _      ___ _           _            _                              │
# │  / __(_) |_   / __| |_  ___ __| |_____ _  _| |_                            │
# │ | (_ | |  _| | (__| ' \/ -_) _| / / _ \ || |  _|                           │
# │  \___|_|\__|  \___|_||_\___\__|_\_\___/\_,_|\__|                           │
# ╰────────────────────────────────────────────────────────────────────────────╯
# TODO, if the work tree is already upto date, then skip
def git_checkout( config: dict ):
    print( t2("Git Checkout") )
    print( s2("Git Checkout") )
    opts = config['opts']
    project = config['project']
    build = config['build']

    gitdef = build['gitdef']

    gitdir = project['path'] / 'git'
    worktree_path = build["source_path"]

    if not gitdir.exists():
        fnf = FileNotFoundError()
        fnf.add_note(f'Missing bare git repo path: {gitdir}, project needs to be fetched')
        raise fnf

    repo = git.Repo( gitdir )
    remote = gitdef['remote']
    gitref = gitdef['ref'] if remote == 'origin' else f'{remote}/{gitdef['ref']}'

    short_hash = repo.git.rev_parse('--short', gitref)

    if not worktree_path.exists():
        h("Create WorkTree")
        os.chdir( gitdir )

        # Perhaps we deleted the worktree folder, in which case prune it
        repo.git.worktree('prune')

        cmd_chunks = [ 'add', '--detach', worktree_path, gitref ]
        if opts['dry']:
            print('dry-run: Skipping remaining work in git_checkout')
            return
        repo.git.worktree( *filter(None, cmd_chunks) )

    worktree = git.Repo( worktree_path )
    worktree_hash = worktree.git.rev_parse('--short', gitref)

    if short_hash != worktree_hash:
        h("Update WorkTree")
        cmd_chunks = [ '--force', '--detach', gitref ]
        if not opts['dry']:
            worktree.git.checkout( *filter(None, cmd_chunks) )
    else:
        h("WorkTree is Up-to-Date")

    print( worktree.git.log('-1') )
    print( send() )