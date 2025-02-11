from pathlib import Path

from share.format import *
from share.run import stream_command

# MARK: Git Fetch Projects
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _     ___    _      _      ___          _        _                 │
# │  / __(_) |_  | __|__| |_ __| |_   | _ \_ _ ___ (_)___ __| |_ ___           │
# │ | (_ | |  _| | _/ -_)  _/ _| ' \  |  _/ '_/ _ \| / -_) _|  _(_-<           │
# │  \___|_|\__| |_|\___|\__\__|_||_| |_| |_| \___// \___\__|\__/__/           │
# │                                              |__/                          │
# ╰────────────────────────────────────────────────────────────────────────────╯
def fetch_projects( projects:dict ):
    print(figlet("Git Fetch", {"font": "small"}))
    for project in projects.values():
        os.chdir( project.project_root )

        h3( project.name )
        print(f"  gitURL={project.gitUrl}")

        bare_git_path = project.project_root / "git"
        if not bare_git_path.exists():
            stream_command( f'git clone --bare "{project.gitUrl}" "{bare_git_path}"', dry=project.dry )
        else:
            stream_command( f'git --git-dir="{bare_git_path}" fetch --force origin *:*' , dry=project.dry )
            stream_command( f'git --git-dir="{bare_git_path}" log -1 --pretty=%B' , dry=project.dry )
            stream_command( f'git --git-dir="{bare_git_path}" worktree list' , dry=project.dry )
            stream_command( f'git --git-dir="{bare_git_path}" worktree prune' , dry=project.dry )

# MARK: Git Checkout
# ╭────────────────────────────────────────────────────────────────────────────╮
# │   ___ _ _      ___ _           _            _                              │
# │  / __(_) |_   / __| |_  ___ __| |_____ _  _| |_                            │
# │ | (_ | |  _| | (__| ' \/ -_) _| / / _ \ || |  _|                           │
# │  \___|_|\__|  \___|_||_\___\__|_\_\___/\_,_|\__|                           │
# ╰────────────────────────────────────────────────────────────────────────────╯
def git_checkout(config: dict):
    print(figlet("Git Checkout", {"font": "small"}))
    # print(f"  gitURL={config['gitUrl']}")
    if 'githash' in config:
        print(f"  gitHash={config['gitHash']}")

    # Create worktree is missing
    if not pathlib.Path(config["source_dir"]).exists():
        h4("Create WorkTree")
        cmd_chunks = [
            "git",
            f'--git-dir="{Path(config['project_root']) / 'git'}"',
            "worktree",
            "add",
            f'-d "{config['source_dir']}"',
        ]
        stream_command(" ".join(cmd_chunks), dry=config['dry'])
    else:
        h4("Update WorkTree")

    # Update worktree
    os.chdir(config["source_dir"])
    chunks = ['git', 'checkout', '--force']
    if 'gitHash' in config: chunks.append(f'-d {config['gitHash']}')
    stream_command(' '.join( chunks ), dry=config['dry'])
    stream_command("git log -1", dry=config['dry'])

    print(centre(" Git Fetch finished ", fill("- ")))


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

    os.chdir(build_dir)

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

    print(centre(" SCons build finished ", fill("- ")))


# MARK: CMake Prep
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║    ██████ ███    ███  █████  ██   ██ ███████     ██████  ██████  ███████ ██████        ║
# ║   ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██   ██ ██      ██   ██       ║
# ║   ██      ██ ████ ██ ███████ █████   █████       ██████  ██████  █████   ██████        ║
# ║   ██      ██  ██  ██ ██   ██ ██  ██  ██          ██      ██   ██ ██      ██            ║
# ║    ██████ ██      ██ ██   ██ ██   ██ ███████     ██      ██   ██ ███████ ██            ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜


def cmake_configure(config: dict):
    cmake = config["cmake"]

    source_dir = Path(config["source_dir"])
    os.chdir(source_dir)

    # requires CMakeLists.txt file existing in the current directory.
    if not (source_dir / "CMakeLists.txt").exists():
        raise f"Missing CMakeLists.txt in {source_dir}"

    # determine build directory
    if "build_dir" in cmake:
        build_dir = Path(cmake["build_dir"])
    else:
        build_dir = Path("build-cmake")

    if not build_dir.is_absolute():
        cmake["build_dir"] = build_dir = source_dir / build_dir

    toolchain_path = ''
    if 'toolchain' in cmake:
        toolchain_path = Path(cmake['toolchain'])
        if not toolchain_path.is_absolute():
            toolchain_path = config['root_dir'] / toolchain_path

    # Create Build Directory
    if not build_dir.is_dir():
        h4(f"Creating {build_dir}")
        os.mkdir(build_dir)

    os.chdir(build_dir)

    config_command = [
        "cmake",
        "--fresh" if cmake['fresh'] else None,
        "--log-level=VERBOSE" if not config["quiet"] else None,
        f'-S "{source_dir}"',
        f'-B "{build_dir}"',
        f'-G"{cmake['generator']}"'if 'generator' in cmake else None,
        f'--toolchain "{os.fspath(toolchain_path)}"' if toolchain_path else None
    ]

    if "config_vars" in cmake.keys():
        config_command += cmake["config_vars"]

    print(figlet("CMake Configure", {"font": "small"}))

    stream_command(" ".join(filter(None, config_command)), dry=config['dry'])

    print(centre(" CMake Configure Completed ", fill("- ")))


# MARK: CMake Build
# ╓────────────────────────────────────────────────────────────────────────────────────────╖
# ║  ██████ ███    ███  █████  ██   ██ ███████     ██████  ██    ██ ██ ██      ██████      ║
# ║ ██      ████  ████ ██   ██ ██  ██  ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║ ██      ██ ████ ██ ███████ █████   █████       ██████  ██    ██ ██ ██      ██   ██     ║
# ║ ██      ██  ██  ██ ██   ██ ██  ██  ██          ██   ██ ██    ██ ██ ██      ██   ██     ║
# ║  ██████ ██      ██ ██   ██ ██   ██ ███████     ██████   ██████  ██ ███████ ██████      ║
# ╙────────────────────────────────────────────────────────────────────────────────────────╜


def cmake_build(config: dict):
    jobs: int = config["jobs"]
    cmake: dict = config["cmake"]

    # requires CMakeLists.txt file existing in the current directory.
    if not (Path(cmake["build_dir"]) / "CMakeCache.txt").exists():
        print(f"Missing CMakeCache.txt in {cmake['build_dir']}")
        raise "Missing CMakeCache.txt"

    chunks = [
        "cmake",
        f'--build "{cmake['build_dir']}"',
        f"-j {jobs}" if jobs > 0 else None,
        "--verbose" if not config["quiet"] else None,
    ]

    if "build_vars" in cmake.keys():
        chunks += cmake["build_vars"]

    for target in cmake["targets"]:
        build_command: str = " ".join(filter(None, chunks))
        build_command += f" --target {target}"

        if "tool_vars" in cmake.keys():
            build_command += " " + " ".join(filter(None, cmake["tool_vars"]))

        print(figlet("CMake Build", {"font": "small"}))
        stream_command(build_command, dry=config["dry"])

    print(centre(" CMake Build Completed ", fill("- ")))
