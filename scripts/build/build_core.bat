@echo off
REM Build script for AdaLog-Sketch Native C++ Core Engine on Windows
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%..\.."

if not exist "%ROOT_DIR%\core" mkdir "%ROOT_DIR%\core"

where g++ >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Warning: g++ not found in PATH, using precompiled core\adalog_core.dll
    exit /b 0
)

echo Building AdaLog-Core Shared Library (Windows DLL)...
g++ -std=c++17 -O3 -mavx2 -shared -static -static-libgcc -static-libstdc++ ^
    -I"%ROOT_DIR%\src\cpp\core" ^
    -I"%ROOT_DIR%\src\cpp\hashing" ^
    -I"%ROOT_DIR%\core" ^
    -o "%ROOT_DIR%\core\adalog_core.dll" ^
    "%ROOT_DIR%\core\adalog_core.cpp"

if %ERRORLEVEL% NEQ 0 (
    echo Warning: Compilation failed, falling back to precompiled core\adalog_core.dll
    exit /b 0
)

echo Building AdaLog-Core Benchmark Binary (Windows EXE)...
g++ -std=c++17 -O3 -mavx2 -static -static-libgcc -static-libstdc++ ^
    -I"%ROOT_DIR%\src\cpp\core" ^
    -I"%ROOT_DIR%\src\cpp\hashing" ^
    -I"%ROOT_DIR%\core" ^
    -o "%ROOT_DIR%\core\bench_core.exe" ^
    "%ROOT_DIR%\core\bench_core.cpp"

if %ERRORLEVEL% NEQ 0 (
    echo Warning: bench_core compilation failed
)

echo Build successful or precompiled binary active.
endlocal
exit /b 0
