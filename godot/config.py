import copy
from types import SimpleNamespace

from share.expand_config import expand_host_env, expand_func
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

project_base:dict = {
    'name':'godot',
    'verbs':['fetch'],
    'gitdef':{
        'url':"https://github.com/godotengine/godot.git/",
        'ref':'master'
    }
}

# MARK: Generate
# ╭────────────────────────────────────────────────────────────────────────────╮
# │  ██████  ███████ ███    ██ ███████ ██████   █████  ████████ ███████        │
# │ ██       ██      ████   ██ ██      ██   ██ ██   ██    ██    ██             │
# │ ██   ███ █████   ██ ██  ██ █████   ██████  ███████    ██    █████          │
# │ ██    ██ ██      ██  ██ ██ ██      ██   ██ ██   ██    ██    ██             │
# │  ██████  ███████ ██   ████ ███████ ██   ██ ██   ██    ██    ███████        │
# ╰────────────────────────────────────────────────────────────────────────────╯

def generate( opts:SimpleNamespace ) -> dict:
    from share.snippets import source_git, show_stats

    project_base.update({
        'path': opts.path / project_base['name'],
        "build_configs": {}
    })
    project = SimpleNamespace(**project_base)


    config_base = SimpleNamespace(**{
        'name':[],
        'variant':'null',
        'source_dir':[],
        'verbs':['source'],
        'script_parts':[source_git, check_scons],
        "scons": {
            "targets": ["template_release", "template_debug", "editor"],
            "build_vars":["compiledb=yes"]
        }
    })

    configs = expand_host_env( config_base, opts )
    for cfg in configs:
        cfg.name = [cfg.host, cfg.toolchain.name, cfg.arch]
        cfg.source_dir = [cfg.host, cfg.toolchain.name]
        cfg.scons['build_vars'].append(f'platform={godot_platforms[cfg.platform]}')
        cfg.scons['build_vars'].append(f'arch={godot_arch[cfg.arch]}')

    configs = expand_func( configs, expand_variations )

    configs = filter( None, [config_toolchains(cfg) for cfg in configs] )

    for cfg in configs:
        cfg.verbs += ['build','clean']

        cfg.script_parts += [ build_scons, clean_scons, show_stats ]

        if isinstance(cfg.name, list): cfg.name = '.'.join(cfg.name)
        if isinstance(cfg.source_dir, list): cfg.source_dir = '.'.join(cfg.source_dir)
        project.build_configs[cfg.name] = cfg

    return {project.name:project}

# MARK: Scripts
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║                 ███████  ██████ ██████  ██ ██████  ████████ ███████                    ║
# ║                 ██      ██      ██   ██ ██ ██   ██    ██    ██                         ║
# ║                 ███████ ██      ██████  ██ ██████     ██    ███████                    ║
# ║                      ██ ██      ██   ██ ██ ██         ██         ██                    ║
# ║                 ███████  ██████ ██   ██ ██ ██         ██    ███████                    ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜

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
    # start_script

    #[=============================[ SCons Check ]=============================]
    scons = build['scons']

    # Figure out the build path
    if "build_dir" in scons.keys():
        scons['build_path'] = project['path'] / build['source_dir'] / scons['build_dir']
    else:
        scons['build_path'] = project['path'] / build['source_dir']

    build_path = Path(scons['build_path'])

    try: os.chdir(build_path)
    except FileNotFoundError as fnf:
        fnf.add_note( f'Missing Folder {build_path}' )
        raise fnf

    # requires SConstruct file existing in the current directory.
    if not (build_path / "SConstruct").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"[red]Missing SConstruct in {build_path}")
        raise fnf

def clean_scons():
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    build:dict = {}
    # start_script
    from subprocess import CalledProcessError

    #[=================================[ Clean ]=================================]
    if config['ok'] and 'clean' in build['verbs'] and 'clean' in opts['build_actions']:
        console.set_window_title(f'Clean - {build['name']}')
        print(h2("SCons Clean"))

        with Timer(name='clean', push=False) as timer:
            try:
                proc = stream_command( "scons --clean" , dry=opts['dry'])
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

def build_scons():
    console = rich.console.Console()
    config:dict = {}
    stats:dict = {}
    opts:dict = {}
    project:dict = {}
    build:dict = {}
    # start_script

    #[=================================[ Build ]=================================]
    from share.actions_scons import scons_build
    scons:dict = build['scons']

    if config['ok'] and 'build' in build['verbs'] and 'build' in opts['build_actions']:
        console.set_window_title(f'Build - {build['name']}')

        profile_name = scons.get('build_profile', None)
        if profile_name:
            profile_path = project['path'] / f'build_profiles/{profile_name}.py'
            scons['build_vars'].append(f'build_profile="{profile_path.as_posix()}"')

        with Timer(name='build') as timer:
            scons_build( config )
        stats['build'] = timer.get_dict()
        config['ok'] = timer.ok()

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
    cfg.scons["build_vars"].append("precision=double")
    return True
variations['double'] = config_double

# MARK: dev_build
def config_dev( cfg:SimpleNamespace ) -> bool:
    if cfg.arch not in ['x86_64', 'arm64']: return False
    cfg.scons['build_vars'].append('dev_build=yes')
    cfg.scons['build_vars'].append('separate_debug_symbols=yes')
    return True

variations['dev_build'] = config_dev

def config_minim( cfg:SimpleNamespace ) -> bool:
    cfg.scons['build_profile'] = 'minimum'
    cfg.scons['build_vars'].append('extra_suffix=min')
    return True

variations['minimum'] = config_minim

def tracy_script():
    # start_script

    #[=================================[ Tracy ]=================================]
    # TODO implement the necessary details to fetch the submodules
    print( "TODO implement the necessary details to fetch the submodules" )
    exit(1)

def config_tracy( cfg:SimpleNamespace ) -> bool:
    cfg.verbs.append( 'tracy' )
    setattr(cfg, 'tracy_script', tracy_script )

    setattr(cfg, 'gitdef', {
        'remote':'enetheru',
        'url':'https://github.com/enetheru/godot.git',
        'ref':'4.4-tracy'
    })
    cfg.source_dir.append( 'tracy' )
    cfg.scons['build_vars'].append('extra_suffix=tracy')
    return True

variations['tracy'] = config_tracy

def config_tracy_dbg( cfg:SimpleNamespace ) -> bool:
    cfg.verbs.append( 'tracy' )
    setattr(cfg, 'tracy_script', tracy_script )

    setattr(cfg, 'gitdef', {
        'remote':'enetheru',
        'url':'https://github.com/enetheru/godot.git',
        'ref':'4.4-tracy'
    })
    cfg.source_dir.append( 'tracy' )
    cfg.scons['build_vars'].append('debug_symbols=yes')
    cfg.scons['build_vars'].append('separate_debug_symbols=yes')
    cfg.scons['build_vars'].append('extra_suffix=tracy.dbg')
    return True

variations['tracy_debug'] = config_tracy_dbg

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

        case "mingw64" | "msys2-ucrt64" | "msys2-mingw64" | "msys2-mingw32":
            cfg.scons["build_vars"].append("use_mingw=yes")

        case 'appleclang':
            cfg.scons['build_vars'].append('generate_bundle=yes')

    return cfg

def expand_variations( config:SimpleNamespace ) -> list:
    configs_out:list = []
    for variant, config_func in variations.items():
        cfg = copy.deepcopy(config)

        setattr(cfg, 'variant', variant)
        cfg.name.append( variant )

        if config_func( cfg ): # Only keep variants who's configuration step succeeds.
            configs_out.append( cfg )

    return configs_out


