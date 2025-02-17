Options
=======

## git sha example
put this at the top of the profile to get the short sha.

```python
import git

repo = git.Repo(search_parent_directories=True)
sha = repo.head.object.hexsha
short_sha = repo.git.rev_parse(sha, short=4)
```


## easy options generator
[generator](https://godot-build-options-generator.github.io)


## Additional Modules

	module_godot_tracy_enabled        = "yes"   # (yes|no)


## Target build options

	platform                      = ""        # Target platform
	p                             = ""        # Alias for platform (...)
	target                        = "editor"  # Compilation target ("editor", "template_release", "template_debug")
	                                          #     (editor | template_debug) enables debug_features
	arch                          = "auto"    # CPU architecture ("auto" ... )
	dev_build                     = "no"      # Developer build with dev-only debugging code (DEV_ENABLED)
	                                          #     enables debug_symbols
	optimize                      = "auto"    # Optimization level (by default inferred from 'target' and 'dev_build')
	                                          #     ("auto", "none", "custom", "debug", "speed", "speed_trace", "size")
	debug_symbols                 = "no"      # Build with debugging symbols
	separate_debug_symbols        = "no"      # Extract debugging symbols to a separate file
	debug_paths_relative          = "no"      # Make file paths in debug symbols relative (if supported)
	lto                           = "none"    # Link-time optimization (production builds) ("none", "auto", "thin", "full")))
	production                    = "no"      # Set defaults to build Godot for use in production
	                                          #     use_static_cpp = "yes", debug_symbols = "no", lto = "auto"
	threads                       = "yes"     # Enable threading support


## Components

	deprecated                    = "yes"     # Enable compatibility code for deprecated and removed features
	precision                     = "single"  # Set the floating-point precision level", "single", ("single", "double")
	minizip                       = "yes"     # Enable ZIP archive support using minizip
	brotli                        = "yes"     # Enable Brotli for decompresson and WOFF2 fonts support
	xaudio2                       = "no"      # Enable the XAudio2 audio driver
	vulkan                        = "yes"     # Enable the vulkan rendering driver
	opengl3                       = "yes"     # Enable the OpenGL/GLES3 rendering driver
	d3d12                         = "no"      # Enable the Direct3D 12 rendering driver
	openxr                        = "yes"     # Enable the OpenXR driver
	use_volk                      = "yes"     # Use the volk library to load the Vulkan loader dynamically
	disable_exceptions            = "yes"     # Force disabling exception handling code
	custom_modules                = ""        # A list of comma-separated directory paths containing custom modules to build
	custom_modules_recursive      = "yes"     # Detect custom modules recursively for each specified path


## Advanced options

	dev_mode                      = "no"      # Alias for dev options: verbose=yes warnings=extra werror=yes tests=yes
	tests                         = "no"      # Build the unit tests
	fast_unsafe                   = "no"      # Enable unsafe options for faster rebuilds
	ninja                         = "no"      # Use the ninja backend for faster rebuilds
	compiledb                     = "no"      # Generate compilation DB (`compile_commands.json`) for external tools
	verbose                       = "no"      # Enable verbose output for the compilation
	progress                      = "yes"     # Show a progress indicator during compilation
	warnings                      = "all"     # Level of compilation warnings ("extra", "all", "moderate", "no")
	werror                        = "no"      # Treat compiler warnings as errors
	extra_suffix                  = ""        # Custom extra suffix added to the base filename of all generated binary files
	object_prefix                 = ""        # Custom prefix added to the base filename of all generated object files
	vsproj                        = "no"      # Generate a Visual Studio solution
	vsproj_name                   = "godot"   # Name of the Visual Studio solution
	import_env_vars               = ""        # A comma-separated list of environment variables to copy from the outer environment
	disable_3d                    = "no"      # Disable 3D nodes for a smaller executable
	disable_advanced_gui          = "no"      # Disable advanced GUI nodes and behaviors
	build_profile                 = ""        # Path to a file containing a feature build profile
	modules_enabled_by_default    = "yes"     # If no, disable all modules except ones explicitly enabled
	no_editor_splash              = "yes"     # Don't use the custom splash screen for the editor
	system_certs_path             = ""        # Use this path as TLS certificates default for editor and Linux/BSD export templates (for package maintainers)
	use_precise_math_checks       = "no"      # Math checks use very precise epsilon (debug option)
	scu_build                     = "no"      # Use single compilation unit build
	scu_limit                     = "0"       # Max includes per SCU file when using scu_build (determines RAM use)
	engine_update_check           = "yes"     # Enable engine update checks in the Project Manager
	steamapi                      = "no"      # Enable minimal SteamAPI integration for usage time tracking (editor only)


## Thirdparty libraries

	builtin_brotli                = "yes"
	builtin_certs                 = "yes"
	builtin_clipper2              = "yes"
	builtin_embree                = "yes"
	builtin_enet                  = "yes"
	builtin_freetype              = "yes"
	builtin_msdfgen               = "yes"
	builtin_glslang               = "yes"
	builtin_graphite              = "yes"
	builtin_harfbuzz              = "yes"
	builtin_icu4c                 = "yes"
	builtin_libogg                = "yes"
	builtin_libpng                = "yes"
	builtin_libtheora             = "yes"
	builtin_libvorbis             = "yes"
	builtin_libwebp               = "yes"
	builtin_wslay                 = "yes"
	builtin_mbedtls               = "yes"
	builtin_miniupnpc             = "yes"
	builtin_openxr                = "yes"
	builtin_pcre2                 = "yes"
	builtin_pcre2_with_jit        = "yes"
	builtin_recastnavigation      = "yes"
	builtin_rvo2_2d               = "yes"
	builtin_rvo2_3d               = "yes"
	builtin_squish                = "yes"
	builtin_xatlas                = "yes"
	builtin_zlib                  = "yes"
	builtin_zstd                  = "yes"


### Brotli
[github](https://github.com/google/brotli)

Brotli is a generic-purpose lossless compression algorithm that compresses data using a combination of a modern
variant of the LZ77 algorithm, Huffman coding and 2nd order context modeling, with a compression ratio comparable to
the best currently available general-purpose compression methods. It is similar in speed with deflate but offers more
dense compression.

### Clipper2 library
[github](https://github.com/AngusJohnson/Clipper2)

The Clipper2 library performs intersection, union, difference and XOR boolean operations on both simple and complex polygons. It also performs polygon offsetting.

## Compilation environment setup
`CXX`, `CC`, and `LINK` directly set the equivalent `env` values (which may still
be overridden for a specific platform), the lowercase ones are appended

	CXX                           = ""        # C++ compiler binary
	CC                            = ""        # C compiler binary
	LINK                          = ""        # Linker binary
	cppdefines                    = ""        # Custom defines for the pre-processor
	ccflags                       = ""        # Custom flags for both the C and C++ compilers
	cxxflags                      = ""        # Custom flags for the C++ compiler
	cflags                        = ""        # Custom flags for the C compiler
	linkflags                     = ""        # Custom flags for the linker
	asflags                       = ""        # Custom flags for the assembler
	arflags                       = ""        # Custom flags for the archive tool
	rcflags                       = ""        # Custom flags for Windows resource compiler

## Modules

	module_astcenc_enabled            = "yes"   # (yes|no)
	module_basis_universal_enabled    = "yes"   # (yes|no)
	module_bmp_enabled                = "yes"   # (yes|no)
	module_camera_enabled             = "yes"   # (yes|no)
	module_csg_enabled                = "yes"   # (yes|no)
	module_cvtt_enabled               = "yes"   # (yes|no)
	module_dds_enabled                = "yes"   # (yes|no)
	module_enet_enabled               = "yes"   # (yes|no)
	module_etcpak_enabled             = "yes"   # (yes|no)
	module_fbx_enabled                = "yes"   # (yes|no)
	module_freetype_enabled           = "yes"   # (yes|no)
	module_gdscript_enabled           = "yes"   # (yes|no)
	module_glslang_enabled            = "yes"   # (yes|no)
	module_gltf_enabled               = "yes"   # (yes|no)
	module_gridmap_enabled            = "yes"   # (yes|no)
	module_hdr_enabled                = "yes"   # (yes|no)
	module_interactive_music_enabl    = "yes"   # (yes|no)
	module_jpg_enabled                = "yes"   # (yes|no)
	module_jsonrpc_enabled            = "yes"   # (yes|no)
	module_ktx_enabled                = "yes"   # (yes|no)
	module_lightmapper_rd_enabled     = "yes"   # (yes|no)
	module_mbedtls_enabled            = "yes"   # (yes|no)
	module_meshoptimizer_enabled      = "yes"   # (yes|no)
	module_minimp3_enabled            = "yes"   # (yes|no)
	module_mobile_vr_enabled          = "yes"   # (yes|no)
	module_mono_enabled               = "yes"   # (yes|no)
	module_msdfgen_enabled            = "yes"   # (yes|no)
	module_multiplayer_enabled        = "yes"   # (yes|no)
	module_navigation_enabled         = "yes"   # (yes|no)
	module_noise_enabled              = "yes"   # (yes|no)
	module_ogg_enabled                = "yes"   # (yes|no)
	module_openxr_enabled             = "yes"   # (yes|no)
	module_raycast_enabled            = "yes"   # (yes|no)
	module_regex_enabled              = "yes"   # (yes|no)
	module_squish_enabled             = "yes"   # (yes|no)
	module_svg_enabled                = "yes"   # (yes|no)
	module_text_server_adv_enabled    = "yes"   # (yes|no)
	module_text_server_fb_enabled     = "yes"   # (yes|no)
	module_tga_enabled                = "yes"   # (yes|no)
	module_theora_enabled             = "yes"   # (yes|no)
	module_tinyexr_enabled            = "yes"   # (yes|no)
	module_upnp_enabled               = "yes"   # (yes|no)
	module_vhacd_enabled              = "yes"   # (yes|no)
	module_vorbis_enabled             = "yes"   # (yes|no)
	module_webp_enabled               = "yes"   # (yes|no)
	module_webrtc_enabled             = "yes"   # (yes|no)
	module_websocket_enabled          = "yes"   # (yes|no)
	module_webxr_enabled              = "yes"   # (yes|no)
	module_xatlas_unwrap_enabled      = "yes"   # (yes|no)
	module_zip_enabled                = "yes"   # (yes|no)


## Linux / BSD options

	linker                        = "default" # Linker program ("default", "bfd", "gold", "lld", "mold")
	use_llvm                      = "no"      # Use the LLVM compiler
	use_static_cpp                = "yes"     # Link libgcc and libstdc++ statically for better portability
	use_coverage                  = "no"      # Test Godot coverage
	use_ubsan                     = "no"      # Use LLVM/GCC compiler undefined behavior sanitizer (UBSAN)
	use_asan                      = "no"      # Use LLVM/GCC compiler address sanitizer (ASAN)
	use_lsan                      = "no"      # Use LLVM/GCC compiler leak sanitizer (LSAN)
	use_tsan                      = "no"      # Use LLVM/GCC compiler thread sanitizer (TSAN)
	use_msan                      = "no"      # Use LLVM compiler memory sanitizer (MSAN)
	use_sowrap                    = "yes"     # Dynamically load system libraries
	alsa                          = "yes"     # Use ALSA
	pulseaudio                    = "yes"     # Use PulseAudio
	dbus                          = "yes"     # Use D-Bus to handle screensaver and portal desktop settings
	speechd                       = "yes"     # Use Speech Dispatcher for Text-to-Speech support
	fontconfig                    = "yes"     # Use fontconfig for system fonts support
	udev                          = "yes"     # Use udev for gamepad connection callbacks
	x11                           = "yes"     # Enable X11 display
	wayland                       = "yes"     # Enable Wayland display
	libdecor                      = "yes"     # Enable libdecor support
	touch                         = "yes"     # Enable touch events
	execinfo                      = "no"      # Use libexecinfo on systems where glibc is not available


## Windows Options
Targeted Windows version: 7 (and later), minimum supported version
XP support dropped after EOL due to missing API for IPv6 and other issues
Vista support dropped after EOL due to GH-10243

	mingw_prefix          = ""            # MinGW prefix

	target_win_version    = "0x0601"      # Targeted Windows version, >= 0x0601 (Windows 7)
	windows_subsystem     = "gui"         # Windows subsystem ("gui", "console")
	msvc_version          = ""            # MSVC version to use. Ignored if VCINSTALLDIR is set in shell env
	use_mingw             = "no"          # Use the Mingw compiler, even if MSVC is installed
	use_llvm              = "yes"         # Use the LLVM compiler
	use_static_cpp        = "yes"         # Link MinGW/MSVC C++ runtime libraries statically
	use_asan              = "no"          # Use address sanitizer (ASAN)
	debug_crt             = "no"          # Compile with MSVC's debug CRT (/MDd)
	incremental_link      = "no"          # Use MSVC incremental linking. May increase or decrease build times
	silence_msvc          = "yes"         # Silence MSVC's cl/link stdout bloat, redirecting any errors to stderr
	angle_libs            = ""            # Path to the ANGLE static libraries

# Direct3D 12 support.
	mesa_libs             = ""            # Path to the MESA/NIR static libraries (required for D3D12)
	agility_sdk_path      = ""            # Path to the Agility SDK distribution (optional for D3D12)
	agility_sdk_multiarch = "no"          # Whether the Agility SDK DLLs will be stored in arch-specific subdirectories
	pix_path              = ""            # Path to the PIX runtime distribution (optional for D3D12)


## My Additional llvm options

	use_coverage          = "no"          # Test Godot coverage
	use_ubsan             = "no"          # Use LLVM/GCC compiler undefined behavior sanitizer (UBSAN)
	use_asan              = "no"          # Use LLVM/GCC compiler address sanitizer

