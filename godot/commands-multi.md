# Build Commands
Build commands for the different toolchains represented in this folder.

Build Dir: `build/<project>/<[os-][env-]branch-target>`

## Default builds for w64, macos, linux
- Targets: `editor`, `template_release=tr`, `template_debug=td` 
- Build Dir: `build/godot/<[os-][env-]branch-target>`
- Command: `scons verbose=yes debug_symbols=yes separate_debug_symbols=yes compiledb=yes target=<target>`

## macos
  
## Target build options
```python
target                      = "editor"  # Compilation target ("editor", "template_release", "template_debug")
                                        #     (editor | template_debug) enables debug_features
debug_symbols               = "no"      # Build with debugging symbols
separate_debug_symbols      = "no"      # Extract debugging symbols to a separate file
compiledb                   = "no"      # Generate compilation DB (`compile_commands.json`) for external tools
use_mingw                   = "no"      # Use the Mingw compiler, even if MSVC is installed
use_llvm                    = "yes"     # Use the LLVM compiler
```

## Compilation environment setup
`CXX`, `CC`, and `LINK` directly set the equivalent `env` values (which may still
be overridden for a specific platform), the lowercase ones are appended
```python
CXX                         = ""        # C++ compiler binary
CC                          = ""        # C compiler binary
LINK                        = ""        # Linker binary
```

## template_release
Build Dir: `build/godot/<os-env-branch-target>`


## Emscripten
```powershell
C:\emsdk\emsdk.ps1 construct_env
scons platform=web target=editor verbose=yes
```
