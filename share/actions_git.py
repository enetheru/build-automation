from share.script_imports import *
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
    print( figlet("Git Checkout", {"font": "small"}) )
    project = config['project']
    build = config['build']
    gitdef = build['gitdef']

    gitdir = Path(gitdef['gitdir'])
    worktree_path = gitdef["worktree_path"]

    if not gitdir.exists():
        fnf = FileNotFoundError()
        fnf.add_note(f'Missing bare git repo path: {gitdir}, project needs to be fetched')
        raise fnf

    repo = git.Repo( gitdir )

    gitref:str = gitdef.get('remote', '')
    gitref =  f'{gitref}/{gitdef['ref']}' if gitref else gitdef['ref']

    short_hash = repo.git.rev_parse('--short', gitref)

    if not worktree_path.exists():
        h4("Create WorkTree")
        os.chdir( gitdir )
        cmd_chunks = [ 'add', '--detach', worktree_path, gitref ]
        if config['dry']:
            print('dry-run: Skipping remaining work in git_checkout')
            return
        repo.git.worktree( *filter(None, cmd_chunks) )

    worktree = git.Repo( worktree_path )
    worktree_hash = worktree.git.rev_parse('--short', gitref)

    if short_hash != worktree_hash:
        h4("Update WorkTree")
        cmd_chunks = [ '--force', '--detach', gitref ]
        if not config['dry']:
            worktree.git.checkout( *filter(None, cmd_chunks) )
    else:
        h4("WorkTree is Up-to-Date")

    # print( worktree.git.show() )
    print(align(" Git Checkout Finished ", line=fill("- ")))