"""
Configuration settings and build definitions for the Godot project.
"""

import copy
import pathlib

from src.config import gopts, project_base, git_base, scons_base, godot_platforms, godot_arch
from src.expand_config import expand_func, short_host, expand_attr_list
from share.script_preamble import *

# MARK: Notes
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  _  _     _                                                                │
# │ | \| |___| |_ ___ ___                                                      │
# │ | .` / _ \  _/ -_|_-<                                                      │
# │ |_|\_\___/\__\___/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
# =======================[ Emscripten ]========================-
# latest version gives this error
# scons: *** [bin\.web_zip\godot.editor.worker.js] The system cannot find the file specified
# https://forum.godotengine.org/t/error-while-building-godot-4-3-web-template/86368

# Official Requirements:
# godotengine - 4.0+     | Emscripten 1.39.9
# godotengine - 4.2+     | Emscripten 3.1.39
# godotengine - master   | Emscripten 3.1.62

# But in the github action runner, it's 3.1.64
# And all the issues related show 3.1.64

# MARK: Notes

origin = SimpleNamespace({**vars(git_base), **{
    'name':'origin',
    'url': "https://github.com/godotengine/godot.git/",
    'ref': 'master'
}})

sources:dict = {
    'origin': origin,
    '4.5': SimpleNamespace({**vars(origin), **{
        'ref': '4.5'
    }}),
    '4.6': SimpleNamespace({**vars(origin), **{
        'ref': '4.6'
    }}),
    '4.7': SimpleNamespace({**vars(origin), **{
        'ref': '4.7'
    }}),
    'libtracy': SimpleNamespace({**vars(origin), **{
        'remote':'enetheru',
        'url': "https://github.com/enetheru/godot.git/",
        'ref': 'tracy-shared'
    }}),
}

project = SimpleNamespace({**vars(project_base), **{
    'name': 'godot',
    'verbs': ['fetch'],
    'sources': sources
}})

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    """
    Generate the project build configuration.
    :param opts:
    :return:
    """
    from src.config import build_base

    from share.snippets import show_stats

    setattr(project, 'path', opts.path / 'godot')       # type: ignore[attr-defined]
    setattr(project, 'buildtools', {             # type: ignore[attr-defined]
        'scons': SimpleNamespace({**vars(scons_base), **{
            'expand':expand_scons,
            'configure':configure_scons,
        }}),
    })

    # Expand the source definitions.
    builds:list[SimpleNamespace] = expand_func(
        [build_base],
        expand_attr_list,
        'source_def',
        sources.values() )

    # Expand toolchains (each toolchain expand sets arch × platform)
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'toolchain',
        gopts.toolchains.values() )

    # Expand build tools
    builds:list[SimpleNamespace] = expand_func(
        builds,
        expand_attr_list,
        'buildtool',
        project.buildtools.values() )

    builds = expand_func( builds, expand_variations )

    # Configure the builds.
    builds = [
        b for b in builds
        if all( f(b) for f in getattr(b, 'configure_funcs', []) )
    ]

    # Naming up to now.
    for build in builds:

        # buildtool = build.buildtool
        tc = build.toolchain

        name_parts = [
            short_host(),
            # buildtool.name, this is always "scons" for godot.
            tc.name,
            tc.target_arch if tc.target_platform not in ['emscripten'] else None,
            godot_platforms[tc.target_platform] if tc.target_platform not in ['android', 'emscripten'] else None,
            build.target,
            build.variant,
            # build.source_def.remote if build.source_def.remote != 'origin' else None,
            # build.source_def.ref
        ]

        build.name = '.'.join(filter(None, name_parts))
        build.source_dir =  build.name

        build.script_parts += [show_stats]

    project.build_configs = { v.name:v for v in builds }
    return project


# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

# MARK: Mingw32
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  __  __ _                  _______                                         │
# │ |  \/  (_)_ _  __ ___ __ _|__ /_  )                                        │
# │ | |\/| | | ' \/ _` \ V  V /|_ \/ /                                         │
# │ |_|  |_|_|_||_\__, |\_/\_/|___/___|                                        │
# │               |___/                                                        │
# ╰────────────────────────────────────────────────────────────────────────────╯
# When mignw32 attempts to compile files that include the *translations.gen.h
# files it spits out this error
#
#   cc1plus.exe: out of memory allocating 536875007 bytes
#
# I personally see it manifest specifically when:
#   [ 72%] Compiling editor/editor_translation.cpp ...
# A quick and dirty way to solve this for now is to just delete the translations.
# The default language is english.

def delete_translations():
    """
    Delete translation files to avoid memory issues.
    """
    build:dict = {}
    # start_script

    # MARK: Delete Translations
    #[=========================[ Delete Translations ]=========================]
    console.rule("Removing Translations")
    fmt.h( ' '.join(os.listdir(build['source_path'] / 'doc/translations/') ) )
    for file in Path(build['source_path'] / 'doc/translations/').glob('*.po'):
        os.remove( file )


# MARK: SCons Script
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___  ___               ___         _      _                               │
# │ / __|/ __|___ _ _  ___ / __| __ _ _(_)_ __| |_                             │
# │ \__ \ (__/ _ \ ' \(_-< \__ \/ _| '_| | '_ \  _|                            │
# │ |___/\___\___/_||_/__/ |___/\__|_| |_| .__/\__|                            │
# │                                      |_|                                   │
# ╰────────────────────────────────────────────────────────────────────────────╯
def check_scons():
    """
    Check if SCons can be run.
    """
    build:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: SCons Check
    #[=============================[ SCons Check ]=============================]
    ## FIXME scons clean also needs the platform set
    scons = buildtool

    # Figure out the build path
    if "build_dir" in scons.keys():
        scons['build_dir'] = project['path'] / build['source_dir'] / scons['build_dir']
    else:
        scons['build_dir'] = project['path'] / build['source_dir']

    build_dir = Path(scons['build_dir'])

    try: os.chdir(build_dir)
    except FileNotFoundError as fnf:
        fnf.add_note( f'\nMissing Folder {build_dir}' )
        fnf.add_note( f'\nProbably need to source the build first.' )
        raise fnf

    # requires SConstruct file existing in the current directory.
    if not (build_dir / "SConstruct").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"[red]Missing SConstruct in {build_dir}")
        raise fnf

def build_scons():
    """
    Execute the SCons build process.
    """
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    build:dict = {}
    buildtool:dict = {}
    # start_script

    # MARK: SCons Build
    #[=================================[ Build ]=================================]
    scons:dict = buildtool

    if config['ok'] and 'build' in build['verbs'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')

        with Timer(name='build') as timer, fmt.Section('Scons Build'):
            try: os.chdir( scons['build_dir'] )
            except FileNotFoundError as fnf:
                fnf.add_note( f'Missing Folder {scons['build_dir']}' )
                raise fnf

            # use a cache if paths exist
            if pathlib.Path(scons['cache_path']).exists():
                scons['build_vars'].append(f'cache_path={Path( scons["cache_path"] ).as_posix()}')
                scons['build_vars'].append(f'cache_limit={scons["cache_limit"]}')

            jobs = opts["jobs"]
            cmd_chunks = [
                "--clean -s" if 'clean' in opts['build_actions'] else None,
                "scons",
                f"-j {jobs}" if jobs > 0 else None,
                "verbose=yes" if opts["verbose"] else None,
            ]
            if "build_vars" in scons.keys():
                cmd_chunks += scons["build_vars"]

            build_command: str = " ".join(filter(None, cmd_chunks))

            # FIXME  I found that if i dont clean the repository then files are unfortunately wrong.
            #  However if I am working on something then this is an unnecessary step most of the time.
            #  [REASON] This is because the clean command depends on the other options
            stream_command(build_command, dry=opts['dry'])

        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()

def clean_scons():
    """
    Clean the SCons build artifacts.
    """
    console = rich.console.Console()
    config:dict = {}
    opts:dict = {}
    build:dict = {}
    stats:dict = {}
    # start_script

    from subprocess import CalledProcessError

    #[=================================[ Clean ]=================================]
    if config['ok'] and 'clean' in opts['build_actions']:
        console.set_window_title(f'Clean - {build['name']}')

        with Timer(name='clean', push=False) as timer, fmt.Section("SCons Clean"):
            try:
                proc = stream_command( "scons --clean -s" , dry=opts['dry'])
                # Change status depending on the truthiness of returnvalue
                # where False is Success and True is Failure.
                timer.status = TaskStatus.FAILED if proc.returncode else TaskStatus.COMPLETED
            except CalledProcessError as e:
                # FIXME should this be more generic and handled elsewhere?
                print( '[red]subprocess error')
                print( f'[red]{e}' )
                timer.status = TaskStatus.FAILED
        stats['clean'] = timer.get_dict()
        config['ok'] = timer.ok()

# MARK: ToolChains
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ _____         _  ___ _         _                                           │
# │|_   _|__  ___| |/ __| |_  __ _(_)_ _  ___                                  │
# │  | |/ _ \/ _ \ | (__| ' \/ _` | | ' \(_-<                                  │
# │  |_|\___/\___/_|\___|_||_\__,_|_|_||_/__/                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def configure_toolchain(config:SimpleNamespace) -> list[SimpleNamespace]:
    """
    Configure the toolchain settings.
    :param config:
    :return:
    """
    if config.toolchain.name == 'android':
        tc = config.toolchain
        ndk_version = '28.1.13356709'
        setattr(tc, 'packages', {
            'platform-tools':'',
            "build-tools":"35.0.0",
            "platforms":"android-35",
            "cmdline-tools":"latest",
            "cmake":"3.10.2.4988404",
            'ndk':ndk_version,
        })
        setattr(tc, 'ndk_path', f'{tc.sdk_path}\\ndk\\{ndk_version}')
        setattr(tc, 'api_level', '35')

    return [config]

# MARK: BuildTools
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___      _ _    _ _____         _                                         │
# │ | _ )_  _(_) |__| |_   _|__  ___| |___                                     │
# │ | _ \ || | | / _` | | |/ _ \/ _ \ (_-<                                     │
# │ |___/\_,_|_|_\__,_| |_|\___/\___/_/__/                                     │
# ╰────────────────────────────────────────────────────────────────────────────╯

# MARK: Scons
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ___                                                                       │
# │ / __| __ ___ _ _  ___                                                      │
# │ \__ \/ _/ _ \ ' \(_-<                                                      │
# │ |___/\__\___/_||_/__/                                                      │
# ╰────────────────────────────────────────────────────────────────────────────╯
def expand_scons( config:SimpleNamespace ) -> list[SimpleNamespace]:
    """
    Expand SCons configuration into multiple targets.
    :param config:
    :return:
    """
    # Split the compile up into individual targets
    configs_out = []
    for target in ["template_release", "template_debug", "editor"]:
        cfg = copy.deepcopy(config)
        setattr(cfg, 'target', target)

        scons = cfg.buildtool
        scons.target = target
        scons.build_vars.append(f'target={target}')

        configs_out.append( cfg )

    return configs_out

def configure_scons( config:SimpleNamespace ) -> bool:
    """
    Configure SCons build variables.
    :param config:
    :return:
    """
    config.verbs += ['build', 'clean']
    config.script_parts +=  [check_scons, clean_scons, build_scons]

    tc = config.toolchain
    scons = config.buildtool
    scons.build_dir = ''

    # == Build Cache ==
    match tc.host:
        case 'Windows':
            setattr(scons, 'cache_path', Path("D:/godot/scons_cache"))
            setattr(scons, 'cache_limit', 100)
        case 'Darwin':
            setattr(scons, 'cache_path', Path("/Volumes/Cache/godot/scons_cache"))
            setattr(scons, 'cache_limit', 100)

    # == Default Options ==
    scons.build_vars += [
        "verbose=yes",
        "compiledb=yes",
        "debug_symbols=yes",
        "separate_debug_symbols=yes",
        f"platform={godot_platforms[tc.target_platform]}",
        f"arch={godot_arch[tc.target_arch]}",
    ]

    match godot_platforms[tc.target_platform]:
        case 'windows':
            scons.build_vars.append('winrt=no')
            scons.build_vars.append('accesskit=no')
            scons.build_vars.append('d3d12=no')
            scons.build_vars.append('angle=no')
        case 'macos':
            scons.build_vars.append('accesskit=no')
            scons.build_vars.append('angle=no')
            scons.build_vars.append('generate_bundle=yes')
        case 'ios':
            # TODO consider supporting simulator builds
            scons.build_vars.append('generate_bundled=yes')
            if tc.host_arch != tc.target_arch:
                return False

    match tc.name:
        case 'msvc' | 'appleclang':
            pass
        case 'emscripten':
            # emscripten builds appear to be broken
            return False
        case 'android':
            ndk_version = '28.1.13356709'
            setattr(tc, 'packages', {
                'platform-tools':'',
                "build-tools":"35.0.0",
                "platforms":"android-35",
                "cmdline-tools":"latest",
                "cmake":"3.10.2.4988404",
                'ndk':ndk_version,
            })
            setattr(tc, 'ndk_path', f'{tc.sdk_path}\\ndk\\{ndk_version}')
            setattr(tc, 'api_level', '35')
        case "llvm":
            if config.arch != 'x86_64': return False
            scons.build_vars.append("use_llvm=yes")

        case "llvm-mingw":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")
            scons.build_vars.append(f"mingw_prefix={tc.sysroot.as_posix()}")
            if config.arch == 'armv7':
                # ERROR: In file included from thirdparty\misc\r128.c:2:
                # thirdparty\misc/r128.h:674:11: error: call to undeclared function '_arm_umull';
                # ISO C99 and later do not support implicit function declarations
                # [-Wimplicit-function-declaration]
                #   674 |    return _arm_umull(a, b);
                #       |           ^
                # 1 error generated.
                return False

        case "mingw64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append(f"mingw_prefix={tc.sysroot.as_posix()}")

        case "msys2-clang64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")

        case "msys2-ucrt64" | "msys2-mingw32" | "msys2-mingw64":
            scons.build_vars.append("use_mingw=yes")

        case _:
            return False

    return True

# def config_tracy_dbg( cfg:SimpleNamespace ) -> bool:
#     cfg.source_dir.append( 'tracy' )
#     cfg.scons['build_vars'].append('debug_symbols=yes')
#     cfg.scons['build_vars'].append('separate_debug_symbols=yes')
#     cfg.scons['build_vars'].append('extra_suffix=tracy.dbg')
#     return True

# MARK: Variant Config
# ╭────────────────────────────────────────────────────────────────────────────╮
# │ __   __        _          _      ___           __ _                        │
# │ \ \ / /_ _ _ _(_)__ _ _ _| |_   / __|___ _ _  / _(_)__ _                   │
# │  \ V / _` | '_| / _` | ' \  _| | (__/ _ \ ' \|  _| / _` |                  │
# │   \_/\__,_|_| |_\__,_|_||_\__|  \___\___/_||_|_| |_\__, |                  │
# │                                                    |___/                   │
# ╰────────────────────────────────────────────────────────────────────────────╯

def config_double( cfg:SimpleNamespace ) -> bool:
    """
    Configure build for double precision.
    :param cfg:
    :return:
    """
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.buildtool.build_vars.append("precision=double")
    return True


def config_dev( cfg:SimpleNamespace ) -> bool:
    """
    Configure build for development.
    :param cfg:
    :return:
    """
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.buildtool.build_vars.append('dev_build=yes')
    cfg.buildtool.build_vars.append('separate_debug_symbols=yes')
    return True


def config_minim( cfg:SimpleNamespace ) -> bool:
    """
    Configure a minimum build profile.
    :param cfg:
    :return:
    """
    cfg.buildtool.build_profile = 'minimum'
    cfg.buildtool.build_vars.append('extra_suffix=min')
    return True


def config_tracy( cfg:SimpleNamespace ) -> bool:
    """
    Configure build with Tracy profiler.
    :param cfg:
    :return:
    """
    # tracy was introduced in master within the 4.6 dev cycle.
    valid_branches = ['master', '4.6', '4.7']
    if not cfg.source_def.ref in valid_branches: return False
    scons = cfg.buildtool

    # Enable the tracy profiler.
    scons.build_vars.append("profiler=tracy")

    # profiler_path: Path to the Profiler framework. Only tracy and perfetto are supported at the moment.
    scons.build_vars.append("profiler_path=C:/git/wolfpld/tracy")

    # profiler_sample_callstack: Profile random samples application-wide using a callstack based sampler. (yes|no)
    if cfg.target != 'template_release':
        scons.build_vars.append("profiler_sample_callstack=yes")

    # profiler_track_memory: Profile memory allocations, if the profiler supports it. (yes|no)
    scons.build_vars.append("profiler_track_memory=yes")

    cfg.buildtool.build_vars.append('extra_suffix=tracy')

    # if cfg.target == 'template_release':
    #     cfg.script_parts += [tracy_script]
    return True


def tracy_script():
    """
    Environment setup for Tracy profiler.
    """
    # start_script
    # MARK: Tracy
    #[=================================[ Tracy ]=================================]
    os.environ["TRACY_NO_DBGHELP_INIT_LOAD"] = "1"

def libtracy_config( cfg:SimpleNamespace ) -> bool:
    """

    :param cfg:
    :return:
    """
    if cfg.source_def.ref != 'tracy-shared':
        return False
    cfg.buildtool.build_vars += [
        'extra_suffix=tracy',
        "profiler=tracy",
        # "profiler_sample_callstack=yes",
        # "profiler_track_memory=yes",
        'tracy_as_shared=yes',
    ]
    tc = cfg.toolchain
    match tc.host:
        case 'Windows':
            cfg.buildtool.build_vars.append("profiler_path=C:/git/wolfpld/tracy")
        case 'Darwin':
            cfg.buildtool.build_vars.append("profiler_path=/Users/enetheru/src/tracy")
    return True


variations = {
    'default': lambda cfg: True,
    'double': config_double,
    'dev_build': config_dev,
    'minimum': config_minim,
    'tracy': config_tracy,
    'libtracy': libtracy_config
}


# MARK: Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _                                                       │
# │  / __|___ _ _  / _(_)__ _ ___                                              │
# │ | (__/ _ \ ' \|  _| / _` (_-<                                              │
# │  \___\___/_||_|_| |_\__, /__/                                              │
# │                     |___/                                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def config_toolchains( cfg:SimpleNamespace ) -> SimpleNamespace:
    """
    Apply toolchain-specific configurations.
    :param cfg:
    :return:
    """
    match cfg.toolchain.name:
        case "llvm":
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "llvm-mingw" | "msys2-clang64":
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.scons["build_vars"].append("use_llvm=yes")

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64":
            cfg.scons["build_vars"].append("use_mingw=yes")

        case 'msys2-mingw32':
            cfg.scons["build_vars"].append("use_mingw=yes")
            cfg.script_parts.append( delete_translations )

        case 'appleclang':
            cfg.scons['build_vars'].append('generate_bundle=yes')

    return cfg

def expand_variations( config:SimpleNamespace ) -> list:
    """
    Expand build configuration into variants.
    :param config:
    :return:
    """
    configs_out:list = []
    for label, config_func in variations.items():
        cfg = copy.deepcopy(config)

        setattr(cfg, 'variant', label)

        if config_func( cfg ): # Only keep variants who's configuration step succeeds.
            configs_out.append( cfg )

    return configs_out


