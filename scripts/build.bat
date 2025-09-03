@echo off
echo 🔨 USB/IP GUI Application - Build Script for Windows
echo ================================================

REM Get the directory of this script and the project root
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

REM Change to project root
cd /d "%PROJECT_ROOT%"

echo.
echo 📁 Project root: %PROJECT_ROOT%
echo 📦 Installing PyInstaller (if needed)...
pip install pyinstaller

echo.
echo 🧹 Cleaning previous builds...
if exist build-configs\build rmdir /s /q build-configs\build
if exist build-configs\dist rmdir /s /q build-configs\dist

echo.
echo 🚀 Building executable...
cd build-configs
pyinstaller USB-IP-GUI.spec --clean
cd ..

echo.
if exist "build-configs\dist\USB-IP-GUI.exe" (
    echo ✅ Build successful!
    echo 📁 Executable created: build-configs\dist\USB-IP-GUI.exe
    echo.
    echo You can now run: build-configs\dist\USB-IP-GUI.exe
) else (
    echo ❌ Build failed - executable not found
)

echo.
echo Press any key to exit...
pause >nul
