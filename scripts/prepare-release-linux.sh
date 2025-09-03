#!/bin/bash

# Release preparation script for USB/IP GUI App Linux version
# This script creates a clean distribution package

set -e

RELEASE_DIR="USB-IP-GUI-Linux"
VERSION=$(date +"%Y.%m.%d")

echo "📦 Preparing Linux release package..."
echo "====================================="

# Check if executable exists
if [ ! -f "dist/USB-IP-GUI" ]; then
    echo "❌ Executable not found. Run ./build-linux.sh first."
    exit 1
fi

# Clean and create release directory
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# Copy the executable
echo "📋 Copying executable..."
cp dist/USB-IP-GUI "$RELEASE_DIR/"

# Copy documentation
echo "📋 Copying documentation..."
cp LINUX-INSTALL.md "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"
cp LICENSE "$RELEASE_DIR/" 2>/dev/null || echo "⚠️  LICENSE file not found"

# Create a simple launcher script
echo "📋 Creating launcher script..."
cat > "$RELEASE_DIR/run-usbip-gui.sh" << 'EOF'
#!/bin/bash

# USB/IP GUI App Launcher Script
# This script checks prerequisites and launches the application

echo "🚀 Starting USB/IP GUI App..."

# Check if usbip is installed
if ! command -v usbip &> /dev/null; then
    echo "❌ usbip is not installed!"
    echo "Please install it first:"
    echo "  Ubuntu/Debian: sudo apt install usbip"
    echo "  Fedora/RHEL:   sudo dnf install usbip"
    echo "  Arch Linux:    sudo pacman -S usbip"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Make sure the executable is executable
chmod +x "$SCRIPT_DIR/USB-IP-GUI"

# Launch the application
exec "$SCRIPT_DIR/USB-IP-GUI"
EOF

chmod +x "$RELEASE_DIR/run-usbip-gui.sh"

# Create version info
echo "📋 Creating version info..."
cat > "$RELEASE_DIR/VERSION" << EOF
USB/IP GUI App for Linux
Version: $VERSION
Build Date: $(date)
Architecture: $(uname -m)
Kernel: $(uname -r)

Built with:
- Python $(python3 --version | cut -d' ' -f2)
- PyInstaller $(pyinstaller --version)
- PyQt6
EOF

# Create archive
echo "📦 Creating release archive..."
tar -czf "${RELEASE_DIR}.tar.gz" "$RELEASE_DIR"

# Show results
echo ""
echo "✅ Release package created successfully!"
echo "📁 Package directory: $RELEASE_DIR/"
echo "📦 Archive file: ${RELEASE_DIR}.tar.gz"
echo ""
echo "📋 Package contents:"
ls -la "$RELEASE_DIR/"
echo ""
echo "📊 Archive size:"
ls -lh "${RELEASE_DIR}.tar.gz"
echo ""
echo "🚀 To distribute:"
echo "   1. Upload ${RELEASE_DIR}.tar.gz to releases"
echo "   2. Users extract: tar -xzf ${RELEASE_DIR}.tar.gz"
echo "   3. Users run: cd $RELEASE_DIR && ./run-usbip-gui.sh"
