@echo off
echo 🔨 USB/IP GUI Application - Build Script for Windows
echo ================================================

echo.
echo 📦 Installing PyInstaller (if needed)...
pip install pyinstaller

echo.
echo 🧹 Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del "*.spec"

echo.
echo 🚀 Building executable...
pyinstaller --onefile --windowed --name "USB-IP-GUI" --clean --noconfirm src/main.py

echo.
if exist "dist\USB-IP-GUI.exe" (
    echo ✅ Build successful!
    echo 📁 Executable created: dist\USB-IP-GUI.exe
    echo.
    echo You can now run: dist\USB-IP-GUI.exe
) else (
    echo ❌ Build failed - executable not found
)

echo.
echo Press any key to exit...
pause >nul
