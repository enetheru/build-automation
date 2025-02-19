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

    scons: dict = config["scons"]
    jobs = config["jobs"]

    if "build_dir" in scons.keys():
        build_dir = Path(scons["build_dir"])
        if not build_dir.is_absolute():
            build_dir = Path(config["source_dir"]) / build_dir
    else:
        build_dir = Path(config["source_dir"])

    try:
        os.chdir(build_dir)
    except FileNotFoundError as e:
        print( f'Missing Folder {build_dir}' )
        return

    # requires SConstruct file existing in the current directory.
    if not (build_dir / "SConstruct").exists():
        print(f"[red]Missing SConstruct in {build_dir}")
        raise "Missing SConstruct"

    cmd_chunks = [
        "scons",
        f"-j {jobs}" if jobs > 0 else None,
        "verbose=yes" if config["quiet"] is False else None,
    ]
    if "build_vars" in scons.keys():
        cmd_chunks += scons["build_vars"]

    for target in scons["targets"]:
        h3(f"Building {target}")
        build_command: str = " ".join(filter(None, cmd_chunks))
        build_command += f" target={target}"
        print( build_command )

        stream_command(build_command, dry=config['dry'])

    print(align(" SCons build finished ", line=fill("- ")))