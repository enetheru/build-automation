
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
    # get a reference to the git command so we can use it independently of a
    # repository
    g = git.cmd.Git()

    # Change to the git directory and instantiate a repo, some commands still
    # assume being inside a git dir.
    os.chdir( project.project_dir )
    gitdef = project.gitdef
    gitdef['dir'] = project.project_dir / "git"

    if not gitdef['dir'].exists():
        h4( 'Cloning' )
        if project['dry']: return
        repo = git.Repo.clone_from( gitdef['url'], gitdef['dir'], progress=print,  bare=True, tags=True )
    else:
        repo = git.Repo( gitdef['dir'] )

    remotes = {remote.name:remote.url for remote in repo.remotes}

    updatable:set = set()
    for name, config in project.build_configs.items():
        gitdef = getattr( config, 'gitdef', None )

        # Early Out
        if not gitdef: continue
        if not 'url' in gitdef: continue
        if gitdef['remote'] in updatable: continue

        # What are we looking for? if it doesnt exist, then we can skip because
        # it will fallback to to the project, and we will always update that.
        gitref = gitdef.get( 'ref', None )
        if not gitref: continue

        print( "Comparing remote and local git references" )

        remote_ref:str = g.ls_remote( gitdef['url'], gitdef['ref'] )


        # This only gets the first occurrance.
        local_ref = next(x for x in repo.git.show_ref().splitlines() if gitdef['ref'] in x)

        if local_ref != remote_ref:
            print( "local and remote references differ, adding to update list" )
            print( "local ref:", local_ref )
            print( "remote ref:", remote_ref )
            updatable.add( gitdef['remote'] )

    print( "list of remotes that have updates" )
    print( updatable )

    # Simple version with no checking.
    # for remote in remotes:
    #     repo.git.fetch( '-v', '--force', remote, '*:*' )

    return

    # Do this for all build configs and branches.
    h4( 'Updating' )
    g = git.cmd.Git()
    refs:str = g.ls_remote( gitdef['url'], gitdef['ref'] )
    print( '    remote:', refs.split()[0] )
    remote_ref = refs.split()[0]


    local_ref = repo.git.show( project.git['ref'], '--format=%H', '-s' )
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
    git_hash = config.get('gitref', None)
    source_dir = config.get("source_dir", config['project_dir'] / config['name'] )

    if not git_dir.exists():
        fnf = FileNotFoundError()
        fnf.add_note(f'Missing bare git repo path: {git_dir}, project needs to be fetched')
        raise fnf

    repo = git.Repo( git_dir )
    latest = repo.git.show(config['gitref'], '--format=%h', '-s')

    if not source_dir.exists():
        h4("Create WorkTree")
        os.chdir( git_dir )
        cmd_chunks = [ 'add', '--detach', source_dir, git_hash ]
        if config['dry']:
            print('dry-run: Skipping remaining work in git_checkout')
            return
        repo.git.worktree( *filter(None, cmd_chunks) )

    worktree = git.Repo( source_dir )
    if latest != worktree.git.show(config['gitref'], '--format=%h', '-s'):
        h4("Update WorkTree")
        cmd_chunks = [ '--force', '--detach', git_hash ]
        if not config['dry']:
            worktree.git.checkout( *filter(None, cmd_chunks) )
    else:
        h4("WorkTree is Up-to-Date")

    print( worktree.git.show() )
    print(align(" Git Checkout Finished ", line=fill("- ")))

def short_hash( config:SimpleNamespace) -> str:
    gitdef = config.gitdef
    git_dir = config.project_dir / "git"
    repo = git.Repo( git_dir )
    return repo.git.show(gitdef['ref'], '--format=%h', '-s')