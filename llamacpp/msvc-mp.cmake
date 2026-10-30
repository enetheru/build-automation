# Visual Studio builds one file at a time inside a project unless cl.exe
# is given /MP. Ninja already schedules files itself, so this file is only
# included for the Visual Studio generator. One core is left free, matching
# AutoBuild's default job count.
if(MSVC AND CMAKE_CXX_COMPILER_ID STREQUAL "MSVC" AND NOT LLAMACPP_MSVC_MP)
    set(LLAMACPP_MSVC_MP ON)
    include(ProcessorCount)
    ProcessorCount(_mp_n)
    if(_mp_n EQUAL 0)
        set(_mp_n 1)
    elseif(_mp_n GREATER 1)
        math(EXPR _mp_n "${_mp_n} - 1")
    endif()
    # clang-cl rejects /MP. Limit it to C and CXX so nvcc does not see it.
    add_compile_options(
        $<$<COMPILE_LANGUAGE:C>:/MP${_mp_n}>
        $<$<COMPILE_LANGUAGE:CXX>:/MP${_mp_n}>
    )
endif()
