@echo off
REM Windows Batch Script to Build Executable
REM Double-click this file to create the Windows executable

echo.
echo ===============================================
echo  Excel Product Extractor - Build Executable
echo ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Python found, building executable...
echo.

REM Run the build script
python build_executable.py

echo.
echo Build process completed!
pause