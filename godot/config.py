import copy
from types import SimpleNamespace

from share.config import git_base, gopts
from share.expand_config import expand_host_env, expand_func, expand_sourcedefs, expand_toolchains, expand_buildtools, \
    short_host, expand_attr_list
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
# And all of the issues related show 3.1.64

# Platform Mapping from python 3.13 to what godot-cpp scons expects
godot_platforms = {
    'android':'android',
    'ios':'ios',
    'linux':'linux',
    'emscripten':'web',
    'darwin':'macos',
    'win32':'windows'
    # aix, cygwin, wasi, are unsupported
}

godot_arch = {
    'armv32': 'arm32',
    'armv7': 'arm32',
    'armeabi-v7a': 'arm32',
    'arm64':'arm64',
    'arm64-v8a':'arm64',
    'aarch64':'arm64',
    'x86_32':'x86_32',
    'i686':'x86_32',
    'x86':'x86_32',
    'x86_64':'x86_64',
    'wasm32':'wasm32'
}

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ) -> SimpleNamespace:
    from share.config import project_base, build_base, scons_base

    from share.snippets import source_git, show_stats

    sources:dict = {
        'origin': SimpleNamespace({**vars(git_base), **{
            'name':'origin',
            'url': "https://github.com/godotengine/godot.git/",
            'ref': 'master'
        }}),
        'ivor-tracy':SimpleNamespace({**vars(git_base), **{
            'name':'ivor-tracy',
            'remote':'ivorforce',
            'url':'https://github.com/Ivorforce/godot.git',
            'ref':'tracy',
            'configure':ivor_tracy_configure,
        }}),
        'enetheru-tracy':SimpleNamespace({**vars(git_base), **{
            'name':'enetheru-tracy',
            'remote':'enetheru',
            'url':'https://github.com/enetheru/godot.git',
            'ref':'4.4-tracy',
            'configure':enetheru_tracy_configure,
        }})
    }

    project = SimpleNamespace({**vars(project_base), **{
        'name': 'godot',
        'verbs': ['fetch'],
        'sources': sources,
        'path': opts.path / 'godot',
        'buildtools': {
            'scons': SimpleNamespace({**vars(scons_base), **{
                'expand':expand_scons,
                'configure':configure_scons,
            }}),
        }
    }})

    # Expand the source definitions.
    builds:list[SimpleNamespace] = expand_func(
        [build_base],
        expand_attr_list,
        'source_def',
        sources.values() )

    # Expand toolchains
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
        if all(
            (lambda f: (
                    (result := f(b)) or
                    (print(f"configure_func {f.__name__} returned falsy ({result})") or False)
            ))(f)
            for f in getattr(b, 'configure_funcs', [])
        )
    ]
    # builds = [
    #     b for b in builds
    #     if all( func(b) for func in getattr(b, 'configure_funcs', []) )
    # ]

    # Naming up to now.
    for build in builds:

        buildtool = build.buildtool
        toolchain = build.toolchain
        src_name = build.source_def.name

        name_parts = [
            short_host(),
            buildtool.name,
            toolchain.name,
            build.arch if build.platform not in ['emscripten'] else None,
            godot_platforms[build.platform] if build.platform not in ['android', 'emscripten'] else None,
            build.target,
            build.variant,
            src_name if src_name != 'origin' else None
        ]

        build.name = '.'.join(filter(None, name_parts))
        build.source_dir =  build.name

        build.script_parts += [show_stats]

    project.build_configs = {v.name: v for v in builds }
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
    build:dict = {}
    # start_script

    # MARK: Delete Translations
    #[=========================[ Delete Translations ]=========================]
    fmt.t3("Removing Translations")
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
    project:dict = {}
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
        fnf.add_note( f'Missing Folder {build_dir}' )
        raise fnf

    # requires SConstruct file existing in the current directory.
    if not (build_dir / "SConstruct").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"[red]Missing SConstruct in {build_dir}")
        raise fnf

def build_scons():
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    project:dict = {}
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

            # Use a project wide build cache
            scons_cache = project['path'] / 'scons_cache'
            scons['build_vars'].append(f'cache_path={scons_cache.as_posix()}')
            scons['build_vars'].append('cache_limit=48')

            jobs = opts["jobs"]
            cmd_chunks = [
                "scons",
                f"-j {jobs}" if jobs > 0 else None,
                "verbose=yes" if opts["verbose"] else None,
            ]
            if "build_vars" in scons.keys():
                cmd_chunks += scons["build_vars"]

            build_command: str = " ".join(filter(None, cmd_chunks))

            # FIXME  I found that if i dont clean the repository then files are unfortunately wrong.
            # However if I am working on something then this isna n
            # unnecessary step most of the time.
            stream_command('scons --clean -s ', dry=opts['dry'])
            stream_command(build_command, dry=opts['dry'])

        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()

def clean_scons():
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
    if config.toolchain.name != 'android':
        return [config]
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
    config.verbs += ['build', 'clean']
    config.script_parts +=  [check_scons, clean_scons, build_scons]

    platform = godot_platforms[config.platform]
    arch = godot_arch[config.arch]

    # config.buildtool = copy.deepcopy(config.buildtool)
    scons = config.buildtool
    scons.build_dir = ''
    scons.build_vars += [
        "compiledb=yes",
        f"platform={platform}",
        f"arch={arch}",
        # "build_profile=build_profile.json",
    ]

    match config.toolchain.name:
        case 'msvc' | 'android' | 'emscripten' | 'appleclang':
            pass
        case "llvm":
            if config.arch != 'x86_64': return False
            scons.build_vars.append("use_llvm=yes")

        case "llvm-mingw":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")
            scons.build_vars.append(f"mingw_prefix={config.toolchain.sysroot.as_posix()}")

        case "mingw64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append(f"mingw_prefix={config.toolchain.sysroot.as_posix()}")

        case "msys2-clang64":
            scons.build_vars.append("use_mingw=yes")
            scons.build_vars.append("use_llvm=yes")

        case "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            scons.build_vars.append("use_mingw=yes")

        case _:
            return False

    return True


def ivor_tracy_configure( cfg:SimpleNamespace ) -> bool:
    scons = cfg.buildtool
    # profiler_path: Path to the Profiler framework. Only tracy and perfetto are supported at the moment.
    scons.build_vars.append("profiler_path=C:/git/wolfpld/tracy")

    # profiler_sample_callstack: Profile random samples application-wide using a callstack based sampler. (yes|no)
    # scons.build_vars.append("profiler_sample_callstack=yes")
    return True


def enetheru_tracy_configure( cfg:SimpleNamespace ) -> bool:
    cfg.buildtool.build_vars.append('extra_suffix=tracy')
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
variations = { 'default' :lambda cfg:True }

# MARK: double
def config_double( cfg:SimpleNamespace ) -> bool:
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.buildtool.build_vars.append("precision=double")
    return True
variations['double'] = config_double

# MARK: dev_build
def config_dev( cfg:SimpleNamespace ) -> bool:
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.buildtool.build_vars.append('dev_build=yes')
    cfg.buildtool.build_vars.append('separate_debug_symbols=yes')
    return True

variations['dev_build'] = config_dev

def config_minim( cfg:SimpleNamespace ) -> bool:
    cfg.buildtool.build_profile = 'minimum'
    cfg.buildtool.build_vars.append('extra_suffix=min')
    return True

variations['minimum'] = config_minim

# MARK: Configs
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___           __ _                                                       │
# │  / __|___ _ _  / _(_)__ _ ___                                              │
# │ | (__/ _ \ ' \|  _| / _` (_-<                                              │
# │  \___\___/_||_|_| |_\__, /__/                                              │
# │                     |___/                                                  │
# ╰────────────────────────────────────────────────────────────────────────────╯

def config_toolchains( cfg:SimpleNamespace ) -> SimpleNamespace:
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
    configs_out:list = []
    for label, config_func in variations.items():
        cfg = copy.deepcopy(config)

        setattr(cfg, 'variant', label)

        if config_func( cfg ): # Only keep variants who's configuration step succeeds.
            configs_out.append( cfg )

    return configs_out


