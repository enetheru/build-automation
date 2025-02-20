from pathlib import Path

from share.format import *
from share.run import stream_command

# MARK: SCons Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║ ███████  ██████  ██████  ███    ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ██      ██    ██ ████   ██ ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████ ██      ██    ██ ██ ██  ██ ███████     ██████  ██    ██ ██ ██      ██   ██     ║
# ║      ██ ██      ██    ██ ██  ██ ██      ██     ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ███████  ██████  ██████  ██   ████ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜
def scons_build(config: dict):
    print(figlet("SCons Build", {"font": "small"}))

    opts:dict = config['opts']
    jobs = opts["jobs"]

    build:dict = config['build']
    scons: dict = build["scons"]


    if "build_dir" in scons.keys():
        build_path = Path(build["source_path"]) / scons['build_dir']
    else:
        build_path = Path(build["source_path"])

    try:
        os.chdir(build_path)
    except FileNotFoundError as e:
        print( f'Missing Folder {build_path}' )
        return

    # requires SConstruct file existing in the current directory.
    if not (build_path / "SConstruct").exists():
        fnf = FileNotFoundError()
        fnf.add_note(f"[red]Missing SConstruct in {build_path}")
        raise fnf

    cmd_chunks = [
        "scons",
        f"-j {jobs}" if jobs > 0 else None,
        "verbose=yes" if opts["quiet"] is False else None,
    ]
    if "build_vars" in scons.keys():
        cmd_chunks += scons["build_vars"]

    for target in scons["targets"]:
        h3(f"Building {target}")
        build_command: str = " ".join(filter(None, cmd_chunks))
        build_command += f" target={target}"
        print( build_command )

        stream_command(build_command, dry=opts['dry'])

    print(align(" SCons build finished ", line=fill("- ")))