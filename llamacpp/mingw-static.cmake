# Windows-GNU.cmake sets CMAKE_FIND_LIBRARY_SUFFIXES to ".dll.a;.a;.lib"
# during project(). This file is CMAKE_PROJECT_INCLUDE, so it runs after
# that. A static archive is preferred when one exists. .dll.a and .lib
# stay in the list because vulkan-1.lib has no static archive.
if(MINGW)
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".a;.dll.a;.lib")
endif()

# Static libcrypto calls inflate/deflate. FindOpenSSL adds ZLIB on UNIX
# only, so the Windows link stops on those symbols. -lz has to follow
# libcrypto.a, which is cpp-httplib's interface, not CMAKE_EXE_LINKER_FLAGS.
function(_llamacpp_static_zlib)
    if(NOT MINGW OR NOT TARGET cpp-httplib)
        return()
    endif()
    find_package(ZLIB)
    if(ZLIB_FOUND)
        target_link_libraries(cpp-httplib PUBLIC ZLIB::ZLIB)
    endif()
endfunction()
cmake_language(DEFER DIRECTORY "${CMAKE_SOURCE_DIR}" CALL _llamacpp_static_zlib)
