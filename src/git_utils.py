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
from git import GitCommandError

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

    g = git.cmd.Git()

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

    # Foreach build?
    for build in project.build_configs.values():
        # derive the final source definition by merging the generated config with the cmdline override.
        gitdef: SimpleNamespace = SimpleNamespace(
            {**vars(build.source_def), **vars(getattr(opts, 'srcdef', SimpleNamespace()))})

        # skip remotes we have already checked, or add it to the checked list.
        if gitdef.remote in checked_list: continue
        checked_list.append(gitdef.remote)

        # Add the new remote to the bare repo if it doesnt exist, and add it to the list to fetch
        if gitdef.remote not in [remote.name for remote in repo.remotes]:
            add_remote( opts, repo, gitdef)
            fetch_list[gitdef.remote] = gitdef.ref
            continue

        # If we are being passed a commit hash, full or short, test that it exists.
        # FIXME I think this is premature since a repo may not be fetched yet, so it cant be tested.

        # Accept full SHA1 or common short hashes (4+ hex chars)
        sha_re = re.compile(r'^[0-9a-f]{4,40}$', re.I)
        if sha_re.match(gitdef.ref):
            ensure_commit_exists( repo, gitdef.ref, opts)
            continue

        # What are we doing. git ls-remote, search the remote for a ref?
        try:
            ls_args = ['--exit-code', gitdef.url, gitdef.ref]
            if opts.verbose:
                fmt.h(f"git ls-remote {' '.join(ls_args)}")
            response = g.ls_remote(ls_args)
            if not response:
                fmt.hu(f"git ls-remote returned '{response}'")
                if getattr(opts, 'gitoverride', False): exit(1)
                fmt.hu(f"disabling build: '{build.name}'")
                build.disabled = True
                continue

            remote_hash: str = response.split()[0]
            if opts.verbose:
                fmt.hu(remote_hash)
        except GitCommandError as e:
            handle_error(f"git ls-remote --exit-code {gitdef.url} {gitdef.ref}", e, opts)
            build.disabled = True
            continue

        cmd_arg = ''
        try:
            cmd_arg = gitdef.ref if gitdef.remote == 'origin' else f"{gitdef.remote}/{gitdef.ref}"
            if opts.verbose:
                fmt.h(f"git rev-parse {cmd_arg}")
            local_hash = repo.git.rev_parse(cmd_arg)
            if opts.verbose:
                fmt.hu(local_hash)
        except GitCommandError as e:
            handle_error(f"git rev-parse local {cmd_arg}", e, opts)
            local_hash = None

        if local_hash != remote_hash:
            fmt.hu('Update Needed')
            fetch_list[gitdef.remote] = gitdef.ref

    fmt.hd()

    if len(fetch_list):
        fmt.h("Fetching updates:")
        for remote, ref in fetch_list.items():
            fetch_args = ['--verbose', '--progress', '--tags', '--force', remote, '*:*']
            fmt.hu(f'git fetch {" ".join(fetch_args)}')
            repo.git.fetch(*fetch_args)
    fmt.h("[green]Up-To-Date")

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

def add_remote(opts, repo, gitdef):
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


def ensure_commit_exists(repo, ref: str, opts):
    """
    Check if a commit (full or abbreviated SHA) exists in the repo.
    Calls handle_error internally on failure.
    Returns True if the commit exists, False otherwise.
    """
    try:
        # --verify is reliable for both full and abbreviated hashes
        repo.git.rev_parse('--verify', '--quiet', ref)
        if opts.verbose:
            fmt.hu(f"  - Fixed commit [green]{ref[:8]}[/green]... available locally ✓")
    except GitCommandError as e:
        handle_error(f"git rev-parse fixed ref {ref[:8]}", e, opts)