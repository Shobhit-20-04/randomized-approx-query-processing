cmake_minimum_required(VERSION 3.15)
project(AdaLogSketch LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Compiler optimization and SIMD flags
if(MSVC)
    add_compile_options(/O2 /arch:AVX2 /W4)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
else()
    add_compile_options(-O3 -mavx2 -Wall -Wextra)
    if(WIN32)
        set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -static -static-libgcc -static-libstdc++")
        set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static -static-libgcc -static-libstdc++")
    endif()
endif()

# Header include paths
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp/hashing
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp/core
    ${CMAKE_CURRENT_SOURCE_DIR}/core
)

# AdaLog-Core Shared Library
add_library(adalog_core SHARED
    src/cpp/core/adalog_core.cpp
)

# AdaLog-Core Standalone Benchmark Executable
add_executable(bench_core
    src/cpp/core/bench_core.cpp
)

# Output directories
set_target_properties(adalog_core PROPERTIES
    OUTPUT_NAME "adalog_core"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build"
)

set_target_properties(bench_core PROPERTIES
    OUTPUT_NAME "bench_core"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build"
)
