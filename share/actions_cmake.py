import os
from pathlib import Path

from share.format import figlet, align, fill, h4
from share.run import stream_command

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
       # raise f"Missing CMakeLists.txt in {source_dir}"
        return

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

    print(align(" CMake Configure Completed ", line=fill("- ")))


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

    print(align(" CMake Build Completed ", line=fill("- ")))
