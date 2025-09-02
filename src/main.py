import sys
import platform
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QStandardPaths
from gui.window import MainWindow
from gui.dialogs.sudo_dialog import SudoPasswordDialog, ThemedMessageBox
from dependencies.checker import check_dependencies
from styling.themes import ThemeManager
from utils.admin_utils import check_and_elevate
import subprocess
import os

def get_subprocess_creation_flags():
    """Get appropriate creation flags for subprocess on Windows to hide console windows"""
    if platform.system() == 'Windows':
        return subprocess.CREATE_NO_WINDOW
    return 0

def get_saved_theme():
    """Get the saved theme setting without requiring full window initialization"""
    try:
        # Try to load theme from the auto_reconnect.enc file
        from security.crypto import FileEncryption
        
        # Create a temporary crypto instance to read the file
        file_crypto = FileEncryption()
        data = file_crypto.load_encrypted_file("auto_reconnect.enc")
        return data.get('theme_setting', 'System Theme')
    except Exception:
        # If anything fails, default to system theme
        return 'System Theme'

def apply_theme_to_app(app, theme_name):
    """Apply theme to the application early, before main window creation"""
    try:
        theme_manager = ThemeManager()
        theme_manager.set_theme(theme_name)
        stylesheet = theme_manager.get_stylesheet(theme_name)
        if stylesheet:
            app.setStyleSheet(stylesheet)
    except Exception:
        # If theme application fails, continue with default
        pass

def validate_sudo_password():
    """Validate sudo password before creating the main window"""
    app = QApplication.instance()  # Use the existing app instance
    
    # Skip sudo validation on Windows since SSH operations will use SSH password
    # and local operations don't need sudo
    if platform.system() == "Windows":
        return "dummy_password", app
    
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        # Create custom themed sudo password dialog
        message = (f"This application requires sudo access to manage USB devices.\n"
                  f"Enter your sudo password (attempt {attempts + 1}/{max_attempts}):" 
                  if attempts > 0 else 
                  "This application requires sudo access to manage USB devices.\n"
                  "Enter your sudo password:")
        
        dialog = SudoPasswordDialog("Sudo Password Required", message)
        
        if dialog.exec() != SudoPasswordDialog.DialogCode.Accepted:
            # User cancelled
            error_dialog = ThemedMessageBox(
                "Error", 
                "Sudo password is required for this application to function properly.",
                "error"
            )
            error_dialog.exec()
            return None, app
        
        password = dialog.get_password()
        
        if not password.strip():  # Empty password
            attempts += 1
            if attempts < max_attempts:
                warning_dialog = ThemedMessageBox(
                    "Invalid Password", 
                    "Password cannot be empty. Please try again.",
                    "warning"
                )
                warning_dialog.exec()
                continue
            else:
                error_dialog = ThemedMessageBox(
                    "Error", 
                    "No valid sudo password provided. Application will exit.",
                    "error"
                )
                error_dialog.exec()
                return None, app
        
        # Test the password by running a simple sudo command
        if test_sudo_password(password):
            return password, app
        else:
            attempts += 1
            if attempts < max_attempts:
                warning_dialog = ThemedMessageBox(
                    "Invalid Password", 
                    "Incorrect sudo password. Please try again.",
                    "warning"
                )
                warning_dialog.exec()
            else:
                error_dialog = ThemedMessageBox(
                    "Error", 
                    "Invalid sudo password after multiple attempts. Application will exit.",
                    "error"
                )
                error_dialog.exec()
                return None, app
    
    return None, app

def test_sudo_password(password):
    """Test if the provided sudo password is correct"""
    # On Windows, always return True since sudo is not needed
    if platform.system() == "Windows":
        return True
        
    try:
        proc = subprocess.run(
            ['sudo', '-S', 'true'],  # Simple command that just returns true
            input=password + '\n',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
            creationflags=get_subprocess_creation_flags()
        )
        return proc.returncode == 0
    except Exception:
        return False

def main():
    # Check for required dependencies
    #if not check_dependencies():
    #    print("Missing dependencies. Please install them and try again.")
    #    sys.exit(1)

    # Check and elevate to admin privileges on Windows if needed
    if platform.system() == "Windows":
        check_and_elevate()

    # Create the QApplication first
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    # Load and apply the saved theme before showing any dialogs
    saved_theme = get_saved_theme()
    apply_theme_to_app(app, saved_theme)

    # Validate sudo password with themed dialogs
    sudo_password, app = validate_sudo_password()
    
    if sudo_password is None:
        # Exit if no valid sudo password was provided
        sys.exit(1)

    # Create and show the main window with the validated password
    window = MainWindow(sudo_password)
    window.show()

    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()