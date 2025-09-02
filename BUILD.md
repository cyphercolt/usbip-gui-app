# Building Executable Distribution

This guide shows how to compile the USB/IP GUI Application into a standalone Windows executable.

## Prerequisites

1. **Python Environment**: Ensure you're in your virtual environment
2. **All Dependencies**: Install all requirements first

```bash
# Activate your virtual environment
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install PyInstaller
pip install pyinstaller
```

## Build Options

### Option 1: One-File Executable (Recommended)
```bash
# Creates a single .exe file (slower startup, easier distribution)
pyinstaller --onefile --windowed --name "USB-IP-GUI" src/main.py
```

### Option 2: One-Directory Distribution
```bash
# Creates a folder with .exe and dependencies (faster startup)
pyinstaller --onedir --windowed --name "USB-IP-GUI" src/main.py
```

### Option 3: Advanced Build with Icon
```bash
# With custom icon (create icon.ico first)
pyinstaller --onefile --windowed --icon=icon.ico --name "USB-IP-GUI" src/main.py
```

## Build Script (Automated)

Use the provided build script for consistent builds:

```bash
# Run the build script
python build_exe.py
```

## Output Location

- **Executable**: `dist/USB-IP-GUI.exe`
- **Build files**: `build/` (can be deleted after build)
- **Spec file**: `USB-IP-GUI.spec` (can be customized)

## Distribution

The generated `.exe` file is standalone and can be:
- Run on any Windows machine without Python installed
- Shared as a single file (onefile build)
- Distributed with the folder (onedir build)

## Troubleshooting

### Common Issues:
1. **Import Errors**: Make sure all dependencies are in requirements.txt
2. **Path Issues**: PyInstaller may not find all files automatically
3. **Antivirus**: Some antivirus software flags PyInstaller executables

### Solutions:
- Use `--hidden-import` for missing modules
- Use `--add-data` for additional files
- Add exception to antivirus software

## Performance Notes

- **Onefile**: Slower startup (extracts to temp), easier distribution
- **Onedir**: Faster startup, larger distribution package
- **First run**: May be slow due to Windows security scanning
