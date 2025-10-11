# Build Automation

## Overview
I found myself repeating things, so I scripted it. I may have gone overboard

This tool is a python based build automation framework, designed specifically to handle the explosion in variation
that comes from projects that contain configurable features, cross platform support, multiple toolchains, etc.

it grew out of my desire to build a cmake solution for godot-cpp, and verify that the build flags match the existing
tools.


## Requirements

- **Python**: Version 3.8 or higher.
- **Python Libraries**:
    - `rich` for console output formatting.
    - `pyfiglet` for ASCII art titles.
    - `gitpython` for Git operations.
    - `pathlib` for path handling.
- **Operating Systems**: Tested on Windows, macOS, and linux.
- **External Tools**:
    - Git (`git`) for source repository management.
    - SCons and/or CMake for build execution.
    - Android SDK (with `sdkmanager`) for Android builds.
    - Emscripten SDK for WebAssembly builds.
    - Toolchain-specific dependencies (e.g., Visual Studio for MSVC, LLVM for Clang).

## Usage

Run the build system using `build.py`:

```bash
python build.py [options] [actions]
```

### Command-Line Options

- `--debug`: Enable debug mode for detailed error output.
- `--dry`: Perform a dry run without executing commands.
- `-q, --quiet`: Suppress console output.
- `-v, --verbose`: Show detailed configuration output.
- `--list`: List available toolchains, projects, and build configurations, then exit.
- `--show`: Show detailed configuration, then exit.
- `-j, --jobs <n>`: Set the number of parallel jobs (default: CPU count - 1).
- `-t, --toolchain-regex <regex>`: Filter toolchains by name (e.g., `msvc`, `llvm`).
- `-p, --project-regex <regex>`: Filter projects by name (e.g., `godot-cpp`).
- `-b, --build-regex <regex>`: Filter build configurations by name.
- `--giturl <url>`: Override the Git repository URL.
- `--gitref <ref>`: Override the Git reference (e.g., commit hash, branch).
- `actions`: Additional actions to perform (e.g., `fetch`, `build`, `test`).

### Examples

- List all available configurations:
  ```bash
  python build.py --list
  ```

- Build all configurations for the `godot-cpp` project:
  ```bash
  python build.py build
  ```

- Build only MSVC-based configurations in debug mode:
  ```bash
  python build.py --toolchain-regex msvc --build-regex debug build
  ```

- Perform a dry run for Android builds:
  ```bash
  python build.py --dry --build-regex android build
  ```
  
## python regex examples

- Include and exclude:
- ```regex
  ^.*(?=(words|to|include))(?!.*(?:exclude|these|things)).*
  ```

## Adding a New Project

1. Create a `config.py` file in a project directory (e.g., `myproject/config.py`).
2. Implement a `generate` function that returns a dictionary of project configurations, similar to the `godot-cpp` example in `config.py`.
    - Define the project name, Git repository details (`gitdef`), and build configurations (`build_configs`).
    - Use expansion functions (e.g., `expand_scons`, `expand_cmake`) to generate build variants.
3. Ensure the project directory is in the same parent directory as `build.py` for automatic detection via globbing (`*/config.py`).
4. Run `python build.py --list` to verify the project is detected.

## Adding a New Toolchain

1. In `toolchains.py`, add a new toolchain function (e.g., `my_toolchain()`) that returns a `SimpleNamespace` with:
    - `name`: Toolchain identifier (e.g., `mytoolchain`).
    - `desc`: Description of the toolchain.
    - `arch`: Supported architectures (e.g., `['x86_64', 'arm64']`).
    - `platform`: Supported platforms (e.g., `['win32', 'darwin']`).
    - Optional: `shell`, `env`, `cmake`, `verbs`, `update`, or `script_parts` for custom behavior.
2. Add the toolchain to the appropriate platform list (e.g., `windows_toolchains` or `darwin_toolchains`).
3. Update `config.py` to support the new toolchain in `expand_toolchains` or related functions, if necessary.