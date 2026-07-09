#!/usr/bin/env python
"""Git utilities for source fetching and overrides."""
import os
from pathlib import Path
from types import SimpleNamespace

from rich.table import Table

from src import format as fmt
from src.ConsoleMultiplex import ConsoleMultiplex
from src.error import handle_error

import re

import git
from git import GitCommandError, Repo

console = ConsoleMultiplex()

#MARK: Override
def git_override(opts: SimpleNamespace):
    """Add ONE transient source definition (copied from 'origin') when --giturl/--gitref is used."""
    commit_hash = ""
    from git import GitCommandError
    import git
    from copy import deepcopy

    g = git.cmd.Git()

    for project in opts.projects.values():
        if 'origin' not in getattr(project, 'sources', {}):
            fmt.h("Skipping project: {name} ".format(name=project.name))
            continue

        origin_src = project.sources['origin']
        override_src = deepcopy(origin_src)

        gitdef = getattr(opts, 'gitdef', {})
        if gitdef.get('url'):
            override_src.url = gitdef['url']
        if gitdef.get('ref'):
            override_src.ref = gitdef['ref']
        if gitdef.get('remote'):
            override_src.remote = gitdef.get('remote', 'origin')

        try:
            fmt.h(f"git ls-remote {override_src.url} {override_src.ref}")
            response = g.ls_remote(override_src.url, override_src.ref)
            commit_hash = response.split()[0] if response else None
        except GitCommandError as e:
            if not handle_error(f"git ls-remote {override_src.url} {override_src.ref}", e, opts):
                commit_hash = None

        if commit_hash:
            fmt.hu(commit_hash)
            override_src.resolved_commit = commit_hash
            project.sources['override'] = override_src
            break


#MARK: Fetch
def git_fetch_project(opts: SimpleNamespace, project: SimpleNamespace):
    """Handle git fetch/prune/add-remote/ls-remote/rev-parse for project builds/sources."""
    if opts.dry:
        fmt.h("Dry-Run: Skipping Fetch")
        return

    os.chdir(project.path)

    srcdef_for_clone = project.sources.get('origin') or next(iter(project.sources.values()))
    gitdir = project.path / getattr(srcdef_for_clone, 'gitdir', Path('git'))

    # Ensure git repo exists, and is clean
    if not gitdir.exists():
        fmt.h('Cloning Repository')
        repo = git.Repo.clone_from(srcdef_for_clone.url, gitdir, progress=print, bare=True, tags=True)
    else:
        repo = git.Repo(gitdir)
        prune_worktrees(opts, repo)

    # print remotes
    if opts.verbose:
        fmt.h("Existing Remotes:")
        table = Table("Remotes", header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="green")
        for remote in repo.remotes:
            table.add_row(remote.name, str(remote.url))
        console.print(table)

    # update
    fmt.h("Looking for Updates")
    if opts.verbose: fmt.hu()
    checked_list = []
    fetch_list = {}

    # Accept full SHA1 or common short hashes (4+ hex chars)
    sha_re = re.compile(r'^[0-9a-f]{4,40}$', re.I)

    # Foreach build config
    for build in project.build_configs.values():
        # derive the final source definition by merging the generated config with the cmdline override.
        gitdef: SimpleNamespace = SimpleNamespace(
            {**vars(build.source_def), **vars(getattr(opts, 'srcdef', SimpleNamespace()))})

        # skip remotes we have already checked, or add it to the checked list.
        if gitdef.remote in checked_list: continue
        checked_list.append(gitdef.remote)

        # Add the new remote to the bare repo if it doesnt exist, and add it to the list to fetch
        if gitdef.remote not in [remote.name for remote in repo.remotes]:
            add_remote( repo, gitdef, opts)
            fetch_list[gitdef.remote] = gitdef.ref
            continue

        # If we are being passed a commit hash, full or short, continue if it exists.
        if sha_re.match(gitdef.ref) and resolve_local_ref( repo, gitdef.ref, opts):
            if opts.verbose:
                fmt.hu(f"  - Fixed commit [green]{gitdef.ref[:8]}[/green]... available locally ✓")
            continue

        # get the remote hash for the ref we want. or disable the build if it does not exist
        remote_hash = resolve_remote_ref(gitdef.url, gitdef.ref, opts)
        if not remote_hash:
            fmt.hu(f"disabling build: '{build.name}'")
            build.disabled = True
            continue

        # FIXME, i should re-arrange the testing logic so that i can more appropriately disable
        #  build configurations

        # test the local bare repo to see if it contains the ref
        ref = gitdef.ref if gitdef.remote == 'origin' else f"{gitdef.remote}/{gitdef.ref}"
        local_hash = resolve_local_ref(repo, ref, opts)
        if not local_hash:
            fmt.hu(f"local ref not yet available: {ref}")
            fetch_list[gitdef.remote] = gitdef.ref
            continue

        # if the remote ref, and the local ref are different, we need to fetch.
        if local_hash != remote_hash:
            fmt.hu('Local and remote hash difference, update Needed')
            fetch_list[gitdef.remote] = gitdef.ref

    fmt.hd()

    if len(fetch_list):
        fmt.h("Fetching updates:")
        for remote, ref in fetch_list.items():
            fetch_args = ['--verbose', '--progress', '--tags', '--force', remote, '*:*']
            fmt.hu(f'git fetch {" ".join(fetch_args)}')
            repo.git.fetch(*fetch_args)
    fmt.h("[green]Up-To-Date")


#MARK: Prune
def prune_worktrees(opts, repo):
    """

    :param opts:
    :param repo:
    """
    fmt.h("Prune Expired Worktrees")
    repo.git.worktree('prune')
    if opts.verbose:
        fmt.h("Worktrees")
        table = Table("Worktrees", header_style="bold magenta")
        table.add_column("Path", style="cyan")
        table.add_column("Status", style="green")
        for line in repo.git.worktree('list').splitlines():
            parts = line.rsplit(maxsplit=1)
            table.add_row(parts[0] if len(parts) > 1 else line, parts[-1] if len(parts) > 1 else "")
        console.print(table)


#MARK: AddRemote
def add_remote(repo:Repo, gitdef, opts):
    """

    :param opts:
    :param repo:
    :param gitdef:
    """
    fmt.h('adding remote:')
    if opts.verbose:
        fmt.hu(gitdef.remote)
        fmt.hu(gitdef.url)
    repo.create_remote(gitdef.remote, gitdef.url)


#MARK: ResolveRemote
def resolve_remote_ref(url, ref, opts):
    """
    Resolve the remote commit hash for a named ref.
    Returns the hash if the remote advertises the ref, otherwise None.
    """
    g = git.cmd.Git()
    try:
        ls_args = ['--exit-code', url, ref]
        if opts.verbose:
            fmt.h(f"git ls-remote {' '.join(ls_args)}")
        response = g.ls_remote(ls_args)
        if not response:
            fmt.hu(f"git ls-remote returned '{response}'")
            if getattr(opts, 'gitoverride', False):
                exit(1)
            return None

        remote_hash = response.split()[0]
        if opts.verbose:
            fmt.hu(remote_hash)
        return remote_hash
    except GitCommandError as e:
        handle_error(f"git ls-remote --exit-code {url} {ref}", e, opts)
        return None

#MARK: ResolveLocal
def resolve_local_ref(repo:Repo, ref: str, opts):
    try:
        # --verify is reliable for both full and abbreviated hashes
        local_hash = repo.git.rev_parse('--verify', '--quiet', ref)
        return local_hash
    except GitCommandError as e:
        handle_error(f"git rev-parse --verify --quiet {ref[:8]}", e, opts)
        return None
