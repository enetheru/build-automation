import os
from pathlib import Path
from types import SimpleNamespace
import git
from git import GitCommandError
from rich.table import Table
from share import format as fmt
from share.config import console
from share.error import handle_error

def git_fetch_project( opts:SimpleNamespace, project:SimpleNamespace ):
    """
    Updates bare repo remotes/worktrees; clones if missing.
    :param opts:
    :param project:
    """
    g = git.cmd.Git()

    # Change to the git directory and instantiate a repo, some commands still
    # assume being inside a git dir.
    os.chdir( project.path )

    srcdef_for_clone = project.sources.get('origin') or next(iter(project.sources.values()))
    gitdir = project.path / getattr(srcdef_for_clone, 'gitdir', Path('git'))

    # Lets clone if we dont exist
    if not gitdir.exists():
        fmt.h( 'Cloning Repository' )
        repo = git.Repo.clone_from( srcdef_for_clone.url, gitdir, progress=print, bare=True, tags=True )
    else:
        repo = git.Repo( gitdir )

        fmt.h("Prune Expired Worktrees")
        repo.git.worktree('prune')
        if opts.verbose:
            fmt.h("Worktrees")
            table = Table("Worktrees", header_style="bold magenta")
            table.add_column("Path", style="cyan")
            table.add_column("Status", style="green")
            for line in repo.git.worktree('list').splitlines():
                parts = line.rsplit(maxsplit=1)
                table.add_row(parts[0] if len(parts)>1 else line, parts[-1] if len(parts)>1 else "")
            console.print(table)

    if opts.verbose:
        fmt.h("Existing Remotes:")
        table = Table("Remotes", header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="green")
        for remote in repo.remotes:
            table.add_row(remote.name, str(remote.url))
        console.print(table)

    # Keep a dictionary of remote:{refs,} to skip already processed remotes.
    fmt.h( "Looking for Updates" )
    if opts.verbose: fmt.hu()
    checked_list = []
    fetch_list = {}

    for build in project.build_configs.values():
        # collate the dictionaries, skipping empty keys
        # Make this a SimpleNamespace so we can use dot referencing
        gitdef:SimpleNamespace = SimpleNamespace({**vars(build.source_def), **vars(getattr(opts, 'srcdef', SimpleNamespace())) })

        # We need to check each remote/reference pair to see if we need to update.
        # But since we update all references for any remote, then, if the remote is
        # in our list to update, we can skip it.
        if gitdef.remote in checked_list: continue
        checked_list.append( gitdef.remote )

        # add the remote to the repo if it doesn't already exist.
        if gitdef.remote not in [remote.name for remote in repo.remotes]:
            fmt.h('adding remote:')
            if opts.verbose:
                fmt.hu(gitdef.remote)
                fmt.hu(gitdef.url)
            repo.create_remote(gitdef.remote, gitdef.url)
            fetch_list[gitdef.remote] = gitdef.ref
            continue

        import re
        sha1_re = re.compile(r'^[0-9a-f]{40}$', re.I)
        if sha1_re.match(gitdef.ref):
            try:
                repo.git.rev_parse(gitdef.ref)
                if opts.verbose:
                    fmt.hu(f"  - Fixed commit [green]{gitdef.ref[:8]}[/green]... available locally ✓")
            except GitCommandError as e:
                handle_error(f"git rev-parse fixed ref {gitdef.ref[:8]}", e, opts)
            continue

        # Check the remote for updates.
        try:
            ls_args = ['--exit-code', gitdef.url, gitdef.ref]
            if opts.verbose:
                fmt.h( f"git ls-remote {' '.join(ls_args)}" )
            response = g.ls_remote( ls_args )
            if not response:
                fmt.hu( f"git ls-remote returned '{response}'" )
                if opts.gitoverride: exit(1)
                fmt.hu( f"disabling build: '{build.name}'" )
                build.disabled = True
                continue

            remote_hash:str = response.split()[0]
            if opts.verbose:
                fmt.hu(remote_hash)
        except GitCommandError as e:
            handle_error(f"git ls-remote --exit-code {gitdef.url} {gitdef.ref}", e, opts)
            # FIXME, I need to disable this configuration if this happens.
            build.disabled = True
            continue

        cmd_arg = ''
        try:
            cmd_arg = gitdef.ref if gitdef.remote == 'origin' else f"{gitdef.remote}/{gitdef.ref}"
            if opts.verbose:
                fmt.h( f"git rev-parse {cmd_arg}" )
            local_hash = repo.git.rev_parse(cmd_arg)
            if opts.verbose:
                fmt.hu(local_hash)
        except GitCommandError as e:
            handle_error(f"git rev-parse local {cmd_arg}", e, opts)
            local_hash = None

        # Add to the list of repo's to fetch updates from
        if local_hash != remote_hash:
            fmt.hu('Update Needed')
            fetch_list[gitdef.remote] = gitdef.ref
    fmt.hd()

    if len(fetch_list):
        fmt.h( "Fetching updates:" )
        for remote, ref in fetch_list.items():
            fetch_args = ['--verbose', '--progress','--tags', '--force', remote, '*:*']
            fmt.hu(f'git fetch {' '.join(fetch_args)}')
            repo.git.fetch( *fetch_args )
    fmt.h( "[green]Up-To-Date" )
