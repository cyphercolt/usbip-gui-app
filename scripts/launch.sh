#!/bin/bash

# USBIP GUI Application - Launch and Setup Script
# This script ensures dependencies are met and launches the application

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to the project root directory
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 USBIP GUI Launcher${NC}"
echo "======================"

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed.${NC}"
    exit 1
fi

# Check for venv module
if ! python3 -c "import venv" &> /dev/null; then
    echo -e "${RED}❌ Error: python3-venv module is not installed.${NC}"
    echo "Please install it (e.g., sudo apt install python3-venv on Ubuntu/Debian)"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error: Failed to create virtual environment.${NC}"
        exit 1
    fi
fi

# Activate the virtual environment
source venv/bin/activate

# Install/Update dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}🔍 Checking/Installing Python dependencies...${NC}"
    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install -r requirements.txt --quiet
else
    echo -e "${RED}⚠️  Warning: requirements.txt not found. Skipping dependency installation.${NC}"
fi

# Check if usbip is installed
if ! command -v usbip &> /dev/null; then
    echo -e "${RED}⚠️  Warning: usbip command not found.${NC}"
    echo "It is recommended to run 'scripts/setup_usbip.sh' to install system dependencies."
    echo ""
    read -p "Continue anyway? (y/N) " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Add project root to PYTHONPATH to ensure imports work correctly
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH}"

# Launch the Python script
echo -e "${GREEN}🎮 Launching USB-IP GUI...${NC}"
python3 src/main.py
