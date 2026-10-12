"""Choose configuration types and CMake targets inside one build script.

A build script is one CMake cache. Debug, Release, and RelWithDebInfo on a
multi-config generator are arguments of that cache, as is each CMake target.
The lists on the buildtool are the full coverage set. A regex narrows the
run. An empty pattern or '.*' keeps every entry.
"""
import re


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _names(obj, key) -> list:
    value = _get(obj, key)
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _matches(pattern: str, *names: str) -> bool:
    if not pattern or pattern == '.*':
        return True
    return any(name and re.search(pattern, name) for name in names)


def chosen_config_types(buildtool, pattern: str) -> list[str]:
    """CMake configuration names to build, in recorded order.

    Matches the short key (debug, release, reldeb) or the CMake name
    (Debug, Release, RelWithDebInfo).
    """
    names = _names(buildtool, 'configuration_types')
    keys = _names(buildtool, 'config_keys')
    if not names:
        one = _get(buildtool, 'config_type')
        if not one:
            return []
        names = [one]
        keys = [_get(buildtool, 'short_type') or one]
    chosen = []
    for index, name in enumerate(names):
        key = keys[index] if index < len(keys) else ''
        if _matches(pattern, key, name):
            chosen.append(name)
    return chosen


def chosen_targets(buildtool, pattern: str) -> list[str]:
    """CMake targets to build, in recorded order."""
    names = _names(buildtool, 'build_targets')
    if not names:
        names = _names(buildtool, 'target')
    return [name for name in names if _matches(pattern, name)]


def row_selected(build, config_pattern: str, target_pattern: str) -> bool:
    """False when this cache has nothing left to build under the patterns.

    Single-config generators are one cache per type, so a type that does not
    match drops the row. A multi-config row stays when at least one of its
    types matches. Non-CMake builds are left alone.
    """
    tool = _get(build, 'buildtool')
    if _get(tool, 'name') != 'cmake':
        return True
    has_configs = bool(_names(tool, 'configuration_types') or _get(tool, 'config_type'))
    has_targets = bool(_names(tool, 'build_targets') or _get(tool, 'target'))
    if has_configs and not chosen_config_types(tool, config_pattern):
        return False
    if has_targets and not chosen_targets(tool, target_pattern):
        return False
    return True


def _unique(values) -> list[str]:
    seen = []
    for value in values:
        if value is None or value == '':
            continue
        text = str(value)
        if text not in seen:
            seen.append(text)
    return seen


def collect_options(builds) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Switches and lists offered by these configurations.

    A switch is a two-way variant whose off state is `plain` (shout, and
    anything like it). Everything else with more than one value, plus config
    and target even when only one value is present, is a list.
    """
    arches, platforms, generators = [], [], []
    configs, targets, variants, versions = [], [], [], []
    for build in builds:
        tool = _get(build, 'buildtool')
        toolchain = _get(build, 'toolchain')
        source = _get(build, 'source_def')
        arches.append(_get(build, 'arch') or _get(toolchain, 'target_arch'))
        platforms.append(_get(build, 'platform') or _get(toolchain, 'target_platform'))
        variants.append(_get(build, 'variant'))
        versions.append(_get(source, 'ref') if source is not None else None)
        if tool is None:
            targets.append(_get(build, 'target'))
            continue
        generators.append(_get(tool, 'short_gen') or _get(tool, 'generator'))
        keys = _names(tool, 'config_keys')
        if not keys:
            short = _get(tool, 'short_type')
            keys = [short] if short else []
        configs.extend(keys)
        named = _names(tool, 'build_targets') or _names(tool, 'target')
        if named:
            targets.extend(named)
        else:
            targets.append(_get(build, 'target'))

    switches = []
    lists = []
    variant_values = _unique(variants)
    if 'plain' in variant_values and len(variant_values) > 1:
        switches.extend(value for value in variant_values if value != 'plain')
    elif len(variant_values) > 1:
        lists.append(('variant', variant_values))

    def add(name, values, keep_single=False):
        vals = _unique(values)
        if len(vals) > 1 or (keep_single and vals):
            lists.append((name, vals))

    add('arch', arches)
    add('platform', platforms)
    add('generator', generators)
    add('config', configs, keep_single=True)
    add('target', targets, keep_single=True)
    add('version', versions)
    return switches, lists


def configuration_folder(project_name: str, build) -> str:
    """Project-relative folder for one configuration.

    Hello leaves source_dir as '.' and puts the cache name in build_dir.
    godot-cpp builds in a directory under the checkout, so both parts show.
    Godot sets build_dir to '' and builds in the checkout itself.
    """
    tool = _get(build, 'buildtool')
    build_dir = _get(tool, 'build_dir') if tool is not None else None
    source = _get(build, 'source_dir')
    source = '' if source is None else str(source).replace('\\', '/')
    build_dir = '' if build_dir is None else str(build_dir).replace('\\', '/')

    if build_dir and source not in ('', '.') and not build_dir.startswith(source + '/'):
        folder = f'{source}/{build_dir}'
    elif build_dir:
        folder = build_dir
    elif source not in ('', '.'):
        folder = source
    else:
        folder = str(_get(build, 'name') or '')

    prefix = project_name + '/'
    if folder.startswith(prefix):
        return folder
    return prefix + folder
