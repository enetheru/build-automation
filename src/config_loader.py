#!/usr/bin/env python
"""Configuration loading and module importing helpers."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from src import format as fmt
from src.config import gopts
from src.error import handle_error
from src.utils import setattrdefault


# MARK: Import Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _      ___           __ _                         │
# │ |_ _|_ __  _ __  ___ _ _| |_   / __|___ _ _  / _(_)__ _ ___                │
# │  | || '  \| '_ \/ _ \ '_|  _| | (__/ _ \ ' \|  _| / _` (_-<                │
# │ |___|_|_|_| .__/\___/_|  \__|  \___\___/_||_|_| |_\__, /__/                │
# ╰───────────┤_├─────────────────────────────────────┤___/────────────────────╯
def import_module(opts: SimpleNamespace, file: Path):
    """
    Imports a Python module from a specified file, sets additional attributes
    provided in `opts.sources`, and executes the module in the current namespace.

    This function dynamically loads a module given its file path, uses the
    importlib utilities for loading and execution, and integrates optional
    attributes into the module namespace. If any errors occur during module
    execution, they are handled through a custom error handler.

    :param opts: Namespace object containing additional options and attributes
        to inject into the module after loading. The `opts.sources` attribute
        should be a dictionary where keys represent attribute names, and values
        represent the values to set in the module.
    :type opts: SimpleNamespace
    :param file: Path to the file representing the module to be imported. The
        file must exist and follow standard Python module structure.
    :type file: Path
    :return: Imported and executed module if successful, otherwise None.
    :rtype: ModuleType or None
    """
    spec = importlib.util.spec_from_file_location(
        name=os.path.basename(file.parent),
        location=file)
    if spec is None:
        return None
    module = importlib.util.module_from_spec(spec)
    if module is None:
        return None

    for attr, value in opts.sources.items():
        setattr(module, attr, value)

    try:
        if spec.loader is not None:
            spec.loader.exec_module(module)
    except Exception as e:
        handle_error(f"exec_module {spec.name}", e, opts)
        return None
    return module


# MARK: Import Toolchains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                     _     _____         _    _         _              │
# │ |_ _|_ __  _ __  ___ _ _| |_  |_   _|__  ___| |__| |_  __ _(_)_ _  ___     │
# │  | || '  \| '_ \/ _ \ '_|  _|   | |/ _ \/ _ \ / _| ' \/ _` | | ' \(_-<     │
# │ |___|_|_|_| .__/\___/_|  \__|   |_|\___/\___/_\__|_||_\__,_|_|_||_/__/     │
# ╰───────────┤_├──────────────────────────────────────────────────────────────╯
def import_toolchains(opts: SimpleNamespace):
    """Import toolchain modules from */toolchains.py and populate the toolchains dict.

    Args:
        opts: Global options namespace to populate with toolchain configurations.
    """
    toolchain_glob = f"*/toolchains.py"
    fmt.h(f"file glob: {toolchain_glob}")

    # Import toolchain modules.
    fmt.hu()
    for file in opts.path.glob(toolchain_glob):
        if opts.verbose: fmt.h(file)

        toolchain_module = import_module(opts, file)
        if not toolchain_module:
            continue

        # generate the project configurations
        try:
            opts.toolchains |= toolchain_module.generate(opts)
        except Exception as e:
            handle_error(f"toolchain_module.generate({file.name})", e, opts)
            continue
    fmt.hd()

    # Filter the results with the toolchain-regex
    opts.toolchains = {k: v for k, v in opts.toolchains.items() if fmt.re.search(opts.toolchain_regex, k)}

    # Fetch all the verbs from the toolchain for displaying help
    for toolchain in opts.toolchains.values():
        opts.toolchain_verbs += [v for v in toolchain.verbs if v not in opts.toolchain_verbs]


def import_projects(opts: SimpleNamespace) -> dict:
    """Import project configurations from */config.py and return the filtered project dictionary.

    Args:
        opts: Global options namespace used to filter and store project configurations.
    Returns:
        The filtered projects dictionary from the param:opts namespace.
    """
    # dbghelp = '[default]( add --debug for more )'
    project_glob = "*/config.py"
    fmt.h(f"file glob: {project_glob}")

    # Import project_config files.
    projects = opts.projects
    for config_file in opts.path.glob(project_glob):
        parent_name = os.path.basename(config_file.parent)
        # Skip directories that are in use
        if parent_name in ['src', 'share', 'toolchains', 'test']:
            continue
        if opts.verbose:
            fmt.hu(config_file)

        project_module = import_module(opts, config_file)
        if not project_module:
            continue

        opts.modules[parent_name] = project_module

    # Filter the results with the project-regex
    opts.modules = {k: v for k, v in opts.modules.items()
                    if fmt.re.search(opts.project_regex, k)}

    fmt.h("Generating Build Configurations")
    for k,v in opts.modules.items():
        if opts.verbose:
            fmt.hu(f"{k}")
        # update module sources with overrides
        v.sources = {**getattr(v, 'sources', {}), **opts.sources}

        # generate the project configurations
        try: project : SimpleNamespace = v.generate( opts )
        except Exception as e:
            handle_error(f"project_module.generate({k})", e, opts)
            continue
        setattr(project, 'name', k) # type: ignore[attr-defined]
        projects[k] = project

    # Verify required project attributes
    # filter the build configurations
    for project in projects.values():
        # All project configs must have a valid gitdef with a URL
        sources : dict = getattr(project, 'sources') # type: ignore[attr-defined]
        if len(sources) == 0:
            msg = f"{project.name} is missing a source definition"
            if gopts.debug: raise Exception(msg)
            fmt.hu(f"[red]{msg}")

        # match --filter <regex>
        builds: dict = project.build_configs
        project.build_configs = {k: v for k, v in builds.items()
            if fmt.re.search( opts.build_regex, v.name )}

    # Filter projects with zero valid build configurations
    projects = {v.name: v for v in projects.values() if len(v.build_configs)}

    # Update project and build fields with information from param:opts
    for project in projects.values():
        project_path:Path = opts.path / project.name
        setattr(project, "path", project_path)
        project.sourcedir = project.path / 'git'

        # collect project verbs for list display
        setattrdefault(project, 'verbs', ['fetch'])
        opts.project_verbs += [verb for verb in project.verbs
                               if verb not in opts.project_verbs]

        # Update all the build configurations
        for build in project.build_configs.values():
            setattr(build, 'project', project)
            setattr(build, 'script_path', project.path / f"{build.name}.py")

            # collect build verbs for list display
            opts.build_verbs += [verb for verb in getattr(build, 'verbs', [])
                                 if verb not in opts.build_verbs]

            # build.source_path is the expected full path to the source of the code
            # if no existing source_dir is set, we will use the build name.
            source_path = project_path / cast(Path, getattr(build, 'source_dir', build.name))
            setattr(build, 'source_path', source_path)

    return projects
