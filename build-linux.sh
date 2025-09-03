#!/bin/bash

# Build script for creating Linux executable of USB/IP GUI App
# This script packages the application using PyInstaller

set -e  # Exit on any error

echo "🏗️  Building USB/IP GUI App for Linux..."
echo "=========================================="

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Consider running: source venv/bin/activate"
    echo ""
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/

# Create the executable
echo "📦 Creating executable with PyInstaller..."
pyinstaller USB-IP-GUI-linux.spec --clean

# Check if build was successful
if [ -f "dist/USB-IP-GUI" ]; then
    echo ""
    echo "✅ Build successful!"
    echo "📁 Executable location: dist/USB-IP-GUI"
    echo ""
    echo "📋 File info:"
    ls -lh dist/USB-IP-GUI
    echo ""
    echo "🔧 To run the executable:"
    echo "   ./dist/USB-IP-GUI"
    echo ""
    echo "📝 Notes:"
    echo "   • Make sure 'usbip' is installed on the target system"
    echo "   • The executable needs sudo privileges for USB operations"
    echo "   • You can copy the entire 'dist' folder to other Linux systems"
else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi
