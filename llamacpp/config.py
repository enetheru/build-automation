"""llama.cpp, fetched from https://github.com/ggml-org/llama.cpp (master).

Each host toolchain gets its own CMake cache. The build target is llama-server.
`cpu` is the stock configure.
`vulkan` adds -DGGML_VULKAN=ON, the switch from the x64-windows-vulkan preset
in the reference checkout. Every row passes -DGGML_STATIC=ON.
`cuda` adds -DGGML_CUDA=ON on the msvc rows. nvcc on Windows does not accept
clang-cl or MinGW as the host compiler. The cache is Ninja Multi-Config or
Visual Studio, and the only configuration type is Release. Visual Studio
rows include msvc-mp.cmake so cl.exe gets /MP. Ninja already runs one
compile per job, so those rows do not.

    python cli.py --list -p ^llamacpp$
    python cli.py -p ^llamacpp$ -t ^llvm$ -b ninja-multi.llvm.x86_64.windows.vulkan build

Android, Emscripten, and every row that is not x86_64 are left out. The
installed Vulkan SDK has one x64 import library. llvm, llvm-mingw, and
mingw64 hide that SDK from find_package, so their vulkan rows pass
Vulkan_LIBRARY, Vulkan_INCLUDE_DIR, and SPIRV-Headers_DIR. The source
worktree is {host}.main under this project. The cache directory is the
configuration name.
"""
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from share.snippets import show_stats, source_git
from src.compiler_cache import apply_cmake_compiler_cache
from src.config import (
    build_base, cmake_base, git_base, godot_arch, godot_platforms, project_base,
)
from src.expand_config import expand_cmake, expand_func, expand_host_env

# android and emscripten are cross targets.
_SKIP_TOOLCHAINS = {'android', 'emscripten'}

# Toolchain files that search libraries and headers only under their find root.
_VULKAN_HINT_TOOLCHAINS = {'llvm', 'llvm-mingw', 'mingw64'}

# nvcc's Windows host compiler is cl.exe. clang-cl reports an unsupported OS.
_CUDA_TOOLCHAINS = {'msvc'}

# cl.exe /MP. Included only for the Visual Studio generator.
_MSVC_MP = (Path(__file__).parent / 'msvc-mp.cmake').as_posix()

# Tests, examples, and the unified app are not the server binary.
_SLIM = [
    '-DLLAMA_BUILD_TESTS=OFF',
    '-DLLAMA_BUILD_EXAMPLES=OFF',
    '-DLLAMA_BUILD_APP=OFF',
]


def vulkan_hints() -> list[str]:
    """Paths FindVulkan and SPIRV-Headers miss under those toolchain files."""
    sdk = os.environ.get('VULKAN_SDK') or r'C:/VulkanSDK/1.4.350.0'
    root = Path(sdk).as_posix()
    return [
        f'-DVulkan_LIBRARY={root}/Lib/vulkan-1.lib',
        f'-DVulkan_INCLUDE_DIR={root}/Include',
        f'-DSPIRV-Headers_DIR={root}/Lib/cmake/SPIRV-Headers',
    ]


def cuda_flags() -> list[str]:
    """Point nvcc at the toolkit selected by CUDA_PATH."""
    root = os.environ.get('CUDA_PATH') or r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.4'
    compiler = (Path(root) / 'bin' / 'nvcc.exe').as_posix()
    if ' ' in compiler:
        compiler = f'"{compiler}"'
    return [
        '-DGGML_CUDA=ON',
        f'-DCMAKE_CUDA_COMPILER={compiler}',
    ]


def generate(opts: SimpleNamespace) -> SimpleNamespace:
    git_source = SimpleNamespace({**vars(git_base), **{
        'name': 'git',
        'url': 'https://github.com/ggml-org/llama.cpp.git',
        'ref': 'master',
    }})
    project = SimpleNamespace({**vars(project_base), **{
        'name': 'llamacpp',
        'sources': {'git': git_source},
        'buildtools': {
            'cmake': SimpleNamespace(**{
                **vars(cmake_base),
                'targets': ['llama-server'],
                # One configure, then cmake --build --config Release.
                # Debug and RelWithDebInfo are for developing llama.cpp.
                'generators': {
                    'msvc': 'Visual Studio 17 2022',
                    'ninja-multi': 'Ninja Multi-Config',
                },
                'config_types': {
                    'release': 'Release',
                },
            }),
        },
    }})
    # project_base keeps a view of the toolchain dict from before -t filters it.
    project.toolchains = opts.toolchains.values()

    build_start = SimpleNamespace({**vars(build_base), **{
        'verbs': ['source'],
        'script_parts': [source_git],
        'platform': 'win32',
        'arch': 'x86_64',
        # build_base leaves source_def empty. Fetch reads remote from it.
        'source_def': git_source,
    }})

    builds = expand_host_env(build_start, project)

    # generic_toolchain_expand records the pair on the toolchain.
    # expand_cmake and the mingw processor flag read build.arch.
    kept = []
    for build in builds:
        toolchain = build.toolchain
        if toolchain.name in _SKIP_TOOLCHAINS:
            continue
        if hasattr(toolchain, 'target_arch'):
            build.arch = toolchain.target_arch
            build.platform = toolchain.target_platform
        if build.arch != 'x86_64':
            continue
        kept.append(build)
    builds = kept

    builds = expand_func(builds, expand_cmake)

    # Each backend is its own configure. GGML_CCACHE stays off.
    # apply_cmake_compiler_cache is the launcher. LLAMA_BUILD_TOOLS stays on
    # because llama-server is built from tools/.
    split = []
    for build in builds:
        variants = [
            ('cpu', []),
            ('vulkan', ['-DGGML_VULKAN=ON']),
        ]
        if build.toolchain.name in _CUDA_TOOLCHAINS:
            variants.append(('cuda', cuda_flags()))
        for label, flags in variants:
            cfg = deepcopy(build)
            cfg.variant = label
            extra = list(flags)
            if label == 'vulkan' and build.toolchain.name in _VULKAN_HINT_TOOLCHAINS:
                extra.extend(vulkan_hints())
            cfg.buildtool.config_vars.extend(extra)
            cfg.buildtool.config_vars.extend(_SLIM)
            cfg.buildtool.config_vars.append('-DGGML_CCACHE=OFF')
            cfg.buildtool.config_vars.append('-DGGML_STATIC=ON')
            if cfg.buildtool.short_gen == 'msvc':
                cfg.buildtool.config_vars.append(f'-DCMAKE_PROJECT_INCLUDE={_MSVC_MP}')
            split.append(cfg)
    builds = split

    # llvm, llvm-mingw, and mingw64 attach the CMake toolchain file here.
    for build in builds:
        configure = getattr(build.toolchain, 'configure', None)
        if configure is not None:
            configure(build)

    for build in builds:
        apply_cmake_compiler_cache(build)
        toolchain = build.toolchain.name
        raw_platform = build.platform
        arch = godot_arch[build.arch]
        platform = godot_platforms[raw_platform]

        cmake = build.buildtool
        if getattr(cmake, 'configuration_types', None):
            tool_name = f'{cmake.name}-{cmake.short_gen}'
        else:
            tool_name = f'{cmake.name}-{cmake.short_type}-{cmake.short_gen}'
        name_parts = [
            build.host,
            tool_name,
            toolchain if toolchain != 'emscripten' else None,
            platform if raw_platform not in ('android', 'emscripten') else None,
            arch if arch != 'wasm32' else None,
            build.variant,
        ]
        build.name = '.'.join(filter(None, name_parts))
        build.source_dir = f'{build.host}.main'
        cmake.build_dir = build.name
        build.script_parts.append(show_stats)

    project.build_configs = {build.name: build for build in builds}
    return project
