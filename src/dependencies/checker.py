import subprocess
import sys


def check_dependencies():
    required_packages = ["usbip", "pyqt6"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("Missing dependencies detected:")
        for package in missing_packages:
            print(f"- {package}")
        install_missing_packages(missing_packages)
    else:
        print("All dependencies are satisfied.")


def install_missing_packages(packages):
    print("Attempting to install missing packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("Missing packages installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install packages: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_dependencies()
