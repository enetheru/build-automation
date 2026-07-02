#!/usr/bin/env python
"""Git utilities for source fetching and overrides."""
from types import SimpleNamespace
from src import format as fmt
from src.error import handle_error


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
