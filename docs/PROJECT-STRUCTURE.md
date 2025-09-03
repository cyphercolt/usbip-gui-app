# USB/IP GUI App - Project Structure

## 📁 Directory Structure

```
├── 📄 README.md                 # Main project documentation
├── 📄 LICENSE                   # Project license
├── 📄 requirements.txt          # Python dependencies
├── 📁 src/                      # Source code
├── 📁 docs/                     # Documentation files
├── 📁 scripts/                  # Build and utility scripts
├── 📁 build-configs/            # PyInstaller configuration files
├── 📁 tests/                    # Test files and debug utilities
├── 📁 .github/workflows/        # CI/CD automation
├── 📁 build/                    # Build artifacts (ignored)
├── 📁 dist/                     # Distribution files (ignored)
└── 📁 venv/                     # Python virtual environment (ignored)
```

## 📖 Documentation

- **README.md** - Main project overview and quick start
- **docs/** - Detailed documentation:
  - Installation guides for different platforms
  - Security information
  - Platform-specific implementation details
  - CI/CD setup instructions

## 🛠️ Scripts

- **scripts/build-linux.sh** - Build Linux executable
- **scripts/prepare-release-linux.sh** - Create Linux release package
- **scripts/setup_usbip.sh** - Set up USB/IP on Linux
- **scripts/launch*.sh/.bat/.ps1** - Various launcher scripts

## ⚙️ Build Configuration

- **build-configs/USB-IP-GUI.spec** - Windows PyInstaller config
- **build-configs/USB-IP-GUI-linux.spec** - Linux PyInstaller config
- **build-configs/build_exe.py** - Alternative build script

## 🧪 Testing

- **tests/** - Test files and debugging utilities
- **src/** - Main application source code

## 🤖 Automation

- **.github/workflows/** - GitHub Actions CI/CD pipelines
  - Automated builds for Windows and Linux
  - Release creation and publishing
  - Code quality checks

## 🚀 Quick Start

1. **Clone and setup:**
   ```bash
   git clone https://github.com/cyphercolt/usbip-gui-app
   cd usbip-gui-app
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Run from source:**
   ```bash
   python src/main.py
   ```

3. **Build executable:**
   ```bash
   ./scripts/build-linux.sh  # Linux
   # or use GitHub Actions for automated builds
   ```
