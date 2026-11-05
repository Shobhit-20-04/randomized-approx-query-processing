#!/usr/bin/env bash
# Build script for AdaLog-Sketch Native C++ Core Engine on Linux/macOS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

mkdir -p "${ROOT_DIR}/core"

echo "Building AdaLog-Core Shared Library (Linux)..."
g++ -std=c++17 -O3 -mavx2 -shared -fPIC \
    -I"${ROOT_DIR}/src/cpp/core" \
    -I"${ROOT_DIR}/src/cpp/hashing" \
    -I"${ROOT_DIR}/core" \
    -o "${ROOT_DIR}/core/libadalog_core.so" \
    "${ROOT_DIR}/src/cpp/core/adalog_core.cpp"

echo "Building AdaLog-Core Benchmark Binary (Linux)..."
g++ -std=c++17 -O3 -mavx2 \
    -I"${ROOT_DIR}/src/cpp/core" \
    -I"${ROOT_DIR}/src/cpp/hashing" \
    -I"${ROOT_DIR}/core" \
    -o "${ROOT_DIR}/core/bench_core" \
    "${ROOT_DIR}/core/bench_core.cpp"

echo "Build successful: ${ROOT_DIR}/core/libadalog_core.so and bench_core"
