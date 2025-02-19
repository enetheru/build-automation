
import os
import git
from types import SimpleNamespace

from share.format import figlet, h4, align, fill

# MARK: Git Fetch Projects
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _     ___    _      _      ___          _        _                 │
# │  / __(_) |_  | __|__| |_ __| |_   | _ \_ _ ___ (_)___ __| |_ ___           │
# │ | (_ | |  _| | _/ -_)  _/ _| ' \  |  _/ '_/ _ \| / -_) _|  _(_-<           │
# │  \___|_|\__| |_|\___|\__\__|_||_| |_| |_| \___// \___\__|\__/__/           │
# │                                              |__/                          │
# ╰────────────────────────────────────────────────────────────────────────────╯

def project_fetch_update( project:SimpleNamespace ):

    os.chdir( project.project_dir )
    git_dir = project.project_dir / "git"

    if not git_dir.exists():
        h4( 'Cloning' )
        if project['dry']: return
        repo = git.Repo.clone_from( project.gitUrl, git_dir, progress=print,  bare=True, tags=True )
    else:
        h4( 'Updating' )
        g = git.cmd.Git()
        refs:str = g.ls_remote( project.gitUrl, project.gitHash )
        print( '    remote:', refs.split()[0] )
        remote_ref = refs.split()[0]

        repo = git.Repo( git_dir )
        local_ref = repo.git.show( project.gitHash, '--format=%H', '-s' )
        print( '    local:', local_ref )

        if remote_ref == local_ref:
            print( "    Repository is Up-to-Date" )
        else:
            repo.git.fetch( '-v', '--force', 'origin', '*:*' )

    # Show the latest commit
    print( repo.git.show() )

    # prune and show the worktrees
    repo.git.worktree('prune')
    print( repo.git.worktree('list') )

# MARK: Git Checkout
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _      ___ _           _            _                              │
# │  / __(_) |_   / __| |_  ___ __| |_____ _  _| |_                            │
# │ | (_ | |  _| | (__| ' \/ -_) _| / / _ \ || |  _|                           │
# │  \___|_|\__|  \___|_||_\___\__|_\_\___/\_,_|\__|                           │
# ╰────────────────────────────────────────────────────────────────────────────╯
# TODO, if the work tree is already upto date, then skip
def git_checkout(config: dict):
    title = figlet("Git Checkout", {"font": "small"})
    title = [line for line in title.splitlines()]
    print( '\r'.join(title) )
    # FIXME ^^, i should be able to just print the figlet title, but something is wrong.

    git_dir = config['project_dir'] / 'git'
    git_hash = config.get('gitHash', None)
    source_dir = config["source_dir"]

    if not git_dir.exists():
        fnf = FileNotFoundError()
        fnf.add_note(f'Missing bare git repo path: {git_dir}, project needs to be fetched')
        raise fnf

    repo = git.Repo( git_dir )
    latest = repo.git.show(config['gitHash'], '--format=%h', '-s')

    if not source_dir.exists():
        h4("Create WorkTree")
        os.chdir( git_dir )
        cmd_chunks = [ 'add', '--detach', source_dir, git_hash ]
        if config['dry']:
            print('dry-run: Skipping remaining work in git_checkout')
            return
        repo.git.worktree( *filter(None, cmd_chunks) )

    worktree = git.Repo( source_dir )
    if latest != worktree.git.show(config['gitHash'], '--format=%h', '-s'):
        h4("Update WorkTree")
        cmd_chunks = [ '--force', '--detach', git_hash ]
        if not config['dry']:
            worktree.git.checkout( *filter(None, cmd_chunks) )
    else:
        h4("WorkTree is Up-to-Date")

    print( worktree.git.show() )
    print(align(" Git Checkout Finished ", line=fill("- ")))