#!/bin/bash

# USBIP GUI Application - System Setup Script
# This script sets up the required kernel modules for USBIP

echo "🔧 USBIP System Setup Script"
echo "============================"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ Please run this script as a regular user (it will use sudo when needed)"
   exit 1
fi

# Check if usbip is installed
if ! command -v usbip &> /dev/null; then
    echo "📦 Installing USBIP package..."
    sudo apt update
    sudo apt install -y usbip
else
    echo "✅ USBIP package already installed"
fi

# Load kernel modules
echo "🔌 Loading USBIP kernel modules..."
sudo modprobe vhci_hcd
sudo modprobe usbip_host

# Check if modules loaded successfully
if lsmod | grep -q "vhci_hcd" && lsmod | grep -q "usbip_host"; then
    echo "✅ Kernel modules loaded successfully"
else
    echo "❌ Failed to load kernel modules. Please check your kernel configuration."
    exit 1
fi

# Create modules-load configuration
echo "⚙️ Configuring modules to load on boot..."
sudo mkdir -p /etc/modules-load.d/

if [[ ! -f /etc/modules-load.d/usbip.conf ]]; then
    echo "vhci_hcd" | sudo tee /etc/modules-load.d/usbip.conf
    echo "usbip_host" | sudo tee -a /etc/modules-load.d/usbip.conf
    echo "✅ Created /etc/modules-load.d/usbip.conf"
else
    echo "✅ /etc/modules-load.d/usbip.conf already exists"
fi

# Check if usbipd service is available (for server setup)
if systemctl list-unit-files | grep -q "usbipd"; then
    echo "🚀 Enabling usbipd service for device sharing..."
    sudo systemctl enable usbipd
    sudo systemctl start usbipd
    echo "✅ usbipd service started and enabled"
else
    echo "ℹ️  usbipd service not found (install usbip-daemon if you want to share devices)"
fi

echo ""
echo "🎉 USBIP setup complete!"
echo ""
echo "Next steps:"
echo "1. Install Python dependencies: pip install -r requirements.txt"
echo "2. Run the application: python3 src/main.py"
echo ""
echo "🎮 Ready for your gaming theater setup! 🎮"
