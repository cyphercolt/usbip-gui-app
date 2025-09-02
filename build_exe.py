#!/usr/bin/env python3
"""
Build script to create executable distribution of USB/IP GUI Application
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr}")
        return False

def clean_build_artifacts():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build artifacts...")
    
    paths_to_clean = ['build', 'dist', '*.spec']
    for path in paths_to_clean:
        if path.endswith('.spec'):
            # Clean spec files
            for spec_file in Path('.').glob('*.spec'):
                print(f"   Removing {spec_file}")
                spec_file.unlink()
        else:
            # Clean directories
            if os.path.exists(path):
                print(f"   Removing {path}/")
                shutil.rmtree(path)
    
    print("✅ Build artifacts cleaned")

def install_pyinstaller():
    """Install PyInstaller if not already installed"""
    try:
        import PyInstaller
        print("✅ PyInstaller already installed")
        return True
    except ImportError:
        print("📦 Installing PyInstaller...")
        return run_command([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                          "Installing PyInstaller")

def build_executable():
    """Build the executable using PyInstaller"""
    print("🚀 Building USB/IP GUI Application executable...")
    
    # Use virtual environment python if available
    venv_python = Path(".venv/Scripts/python.exe")
    if venv_python.exists():
        python_cmd = str(venv_python)
        print(f"   Using virtual environment: {python_cmd}")
        pyinstaller_cmd = [python_cmd, "-m", "PyInstaller"]
    else:
        python_cmd = sys.executable
        print(f"   Using system Python: {python_cmd}")
        pyinstaller_cmd = ["pyinstaller"]
    
    # PyInstaller command
    cmd = pyinstaller_cmd + [
        "--onefile",           # Single executable file
        "--windowed",          # No console window
        "--name", "USB-IP-GUI", # Executable name
        "--clean",             # Clean cache
        "--noconfirm",         # Overwrite without asking
        "src/main.py"          # Main application file
    ]
    
    # Add hidden imports for potential missing modules
    hidden_imports = [
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui", 
        "PyQt6.QtWidgets",
        "cryptography.fernet",
        "cryptography",
        "paramiko"
    ]
    
    for module in hidden_imports:
        cmd.extend(["--hidden-import", module])
    
    return run_command(cmd, "Building executable")

def verify_build():
    """Verify the build was successful"""
    exe_path = Path("dist/USB-IP-GUI.exe")
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ Build successful!")
        print(f"   Executable: {exe_path}")
        print(f"   Size: {size_mb:.1f} MB")
        
        # List all files in dist directory
        print(f"\n📁 Contents of dist/ directory:")
        try:
            import os
            for item in os.listdir("dist"):
                item_path = Path("dist") / item
                if item_path.is_file():
                    item_size_mb = item_path.stat().st_size / (1024 * 1024)
                    print(f"   {item} ({item_size_mb:.1f} MB)")
                else:
                    print(f"   {item}/ (directory)")
        except Exception as e:
            print(f"   Could not list directory contents: {e}")
        
        return True
    else:
        print("❌ Build failed - executable not found")
        return False

def main():
    """Main build process"""
    print("🔨 USB/IP GUI Application - Build Script")
    print("=" * 50)
    
    # Step 1: Clean previous builds
    clean_build_artifacts()
    
    # Step 2: Install PyInstaller
    if not install_pyinstaller():
        print("❌ Failed to install PyInstaller")
        return 1
    
    # Step 3: Build executable
    if not build_executable():
        print("❌ Build failed")
        return 1
    
    # Step 4: Verify build
    if not verify_build():
        return 1
    
    print("\n🎉 Build completed successfully!")
    print("📁 Executable location: dist/USB-IP-GUI.exe")
    print("📋 You can now distribute the .exe file")
    
    return 0

if __name__ == "__main__":
    exit(main())
