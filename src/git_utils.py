#!/usr/bin/env python
"""Git utilities for source fetching and overrides."""
import os
import time
from pathlib import Path
from types import SimpleNamespace

from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)

from src import format as fmt
from src.ConsoleMultiplex import ConsoleMultiplex
from src.error import handle_error

import re

import git
from git import GitCommandError, Repo, RemoteProgress

console = ConsoleMultiplex()

# Substrings that indicate a *transient* network failure worth retrying.
# Matched case-insensitively against the GitCommandError text (stderr + message).
_TRANSIENT_GIT_ERRORS = (
    'http 408', 'http 500', 'http 502', 'http 503', 'http 504',
    'broken pipe', 'rpc failed', 'timed out', 'timeout',
    'connection reset', 'connection refused', 'could not resolve host',
    'early eof', 'unexpected disconnect', 'the remote end hung up',
)


def _is_transient_git_error(exc: GitCommandError) -> bool:
    """Return True if the GitCommandError looks like a transient network problem."""
    haystack = ' '.join(filter(None, [
        str(exc),
        getattr(exc, 'stderr', '') or '',
        getattr(exc, 'stdout', '') or '',
    ])).lower()
    return any(marker in haystack for marker in _TRANSIENT_GIT_ERRORS)


class _RichFetchProgress(RemoteProgress):
    """Bridge GitPython's RemoteProgress into a rich.progress.Progress display.

    Each git phase (Counting / Compressing / Writing / Receiving / Resolving /
    Finding sources / Checking out) becomes its own task in the shared
    `Progress` instance, so users see a stack of live progress bars.

    Non-progress stderr lines emitted by git (e.g. "From <url>",
    "* [new branch] …", warnings) are forwarded via `progress.console.log(...)`.
    """

    _OP_NAMES = {
        RemoteProgress.COUNTING:        'Counting objects',
        RemoteProgress.COMPRESSING:     'Compressing objects',
        RemoteProgress.WRITING:         'Writing objects',
        RemoteProgress.RECEIVING:       'Receiving objects',
        RemoteProgress.RESOLVING:       'Resolving deltas',
        RemoteProgress.FINDING_SOURCES: 'Finding sources',
        RemoteProgress.CHECKING_OUT:    'Checking out',
    }

    def __init__(self, progress: Progress, label: str = ''):
        super().__init__()
        self._progress = progress
        self._label = label
        # Maps a stage id -> Rich TaskID
        self._tasks: dict[int, int] = {}

    def _task_for(self, stage: int, max_count) -> int:
        task_id = self._tasks.get(stage)
        desc = self._OP_NAMES.get(stage, f'op[{stage}]')
        if self._label:
            desc = f'[cyan]{self._label}[/cyan] {desc}'
        if task_id is None:
            task_id = self._progress.add_task(
                description=desc,
                total=max_count if max_count else None,
            )
            self._tasks[stage] = task_id
        elif max_count and self._progress.tasks[task_id].total != max_count:
            self._progress.update(task_id, total=max_count)
        return task_id

    def update(self, op_code, cur_count, max_count=None, message=''):
        stage = op_code & RemoteProgress.OP_MASK
        task_id = self._task_for(stage, max_count)

        self._progress.update(
            task_id,
            completed=cur_count,
            total=max_count if max_count else None,
        )

        if op_code & RemoteProgress.END:
            total = self._progress.tasks[task_id].total
            if total is not None:
                self._progress.update(task_id, completed=total)

    def line_dropped(self, line: str) -> None:
        text = line.rstrip()
        if text:
            self._progress.console.log(text)


def _make_fetch_progress() -> Progress:
    """Build a Progress display tuned for git fetch phases, bound to our multiplex console."""
    return Progress(
        SpinnerColumn(),
        TextColumn('[progress.description]{task.description}'),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
        expand=True,
    )


def _git_fetch_with_retry(repo: Repo, remote_name: str, refspec, opts,
                          max_attempts: int = 4,
                          initial_delay: float = 3.0,
                          backoff: float = 2.0):
    """Run a fetch with a live Rich progress display and retry on transient errors.

    If `refspec` is None or empty, the remote's *configured* fetch refspec is
    used — this is the desired default so that branches land under
    refs/remotes/<name>/* rather than clobbering refs/*.
    """
    remote = repo.remote(remote_name)
    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            with _make_fetch_progress() as progress:
                label = remote_name if attempt == 1 else f'{remote_name} (retry {attempt - 1})'
                bridge = _RichFetchProgress(progress, label=label)
                fetch_kwargs = dict(progress=bridge, tags=True, force=True, verbose=True)
                # Only pass refspec if the caller supplied one; otherwise use
                # the remote's configured refspec (much better default).
                if refspec:
                    fetch_kwargs['refspec'] = refspec
                return remote.fetch(**fetch_kwargs)
        except GitCommandError as e:
            if not _is_transient_git_error(e):
                raise
            if attempt >= max_attempts:
                fmt.hu(f"[red]git fetch failed after {attempt} attempts[/red]")
                raise
            fmt.hu(
                f"[yellow]transient git error (attempt {attempt}/{max_attempts}): "
                f"{str(e).splitlines()[0]}[/yellow]"
            )
            fmt.hu(f"retrying in {delay:.1f}s ...")
            try:
                time.sleep(delay)
            except KeyboardInterrupt:
                raise
            delay *= backoff
    return None


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
        if sha_re.match(gitdef.ref) and resolve_local_ref(repo, gitdef.ref):
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
        ref = f"refs/heads/{gitdef.ref}" if gitdef.remote == 'origin' else f"refs/remotes/{gitdef.remote}/{gitdef.ref}"
        local_hash = resolve_local_ref(repo, ref)
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
            # Passing refspec=None means "use the remote's configured
            # fetch refspec" — which we ensured is
            # +refs/heads/*:refs/remotes/<remote>/* for every remote.
            fmt.hu(f'git fetch --progress --tags --force {remote}')
            try:
                if remote == "origin":
                    refspec = f"+refs/heads/*:refs/heads/*"
                else:
                    refspec = None
                _git_fetch_with_retry(repo, remote, refspec, opts)
            except GitCommandError as e:
                handle_error(f"git fetch {remote}", e, opts)

            # fetch_args = ['--verbose', '--progress', '--tags', '--force', remote, '*:*']
            # _git_fetch_with_retry(repo, remote, ref, opts)
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
def add_remote(repo: Repo, gitdef, opts):
    """Create a remote and configure it to fetch branches into refs/remotes/<name>/*.

    Without an explicit fetch refspec, `git fetch <remote>` on a freshly-added
    remote is a no-op (nothing is mapped locally). We add the standard branch
    refspec so that:
        - `git fetch <name>`         populates refs/remotes/<name>/<branch>
        - `resolve_local_ref(repo, f"{name}/{branch}")` succeeds
    """
    fmt.h('adding remote:')
    if opts.verbose:
        fmt.hu(gitdef.remote)
        fmt.hu(gitdef.url)

    remote = repo.create_remote(gitdef.remote, gitdef.url)

    # Configure the standard branch-tracking refspec.
    # For a bare repo, refs/remotes/<name>/* is still a perfectly valid
    # storage location — it's just a ref namespace.
    with remote.config_writer as cw:
        cw.set('fetch', f'+refs/heads/*:refs/remotes/{gitdef.remote}/*')
        # Also grab tags automatically (equivalent to `git remote add --tags`)
        cw.set('tagopt', '--tags')


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
def resolve_local_ref(repo:Repo, ref: str):
    try:
        # --verify is reliable for both full and abbreviated hashes
        local_hash = repo.git.rev_parse(ref)
        return local_hash
    except GitCommandError:
        # handle_error(f"git rev-parse {ref[:8]}", e, opts)
        return None
