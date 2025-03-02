from share.script_preamble import *

# MARK: SCons Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║ ███████  ██████  ██████  ███    ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ██      ██    ██ ████   ██ ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████ ██      ██    ██ ██ ██  ██ ███████     ██████  ██    ██ ██ ██      ██   ██     ║
# ║      ██ ██      ██    ██ ██  ██ ██      ██     ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████  ██████  ██████  ██   ████ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def scons_build(config: dict):
    t2("SCons Build")
    s1("SCons Build")

    opts:dict       = config['opts']
    project:dict    = config['project']
    build:dict      = config['build']
    scons: dict     = build["scons"]

    try: os.chdir( scons['build_path'] )
    except FileNotFoundError as fnf:
        fnf.add_note( f'Missing Folder {scons['build_path']}' )
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

    for target in scons["targets"]:
        h(f"Building {target}")
        build_command: str = " ".join(filter(None, cmd_chunks + [f"target={target}"]))

        # I found that if i dont clean the repository then files are unfortunately wrong.
        stream_command('scons --clean -s', dry=opts['dry'])

        stream_command(build_command, dry=opts['dry'])

    send()