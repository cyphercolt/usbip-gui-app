import sys
from PyQt6.QtWidgets import QApplication, QInputDialog, QMessageBox, QLineEdit
from gui.window import MainWindow
from dependencies.checker import check_dependencies
import subprocess

def validate_sudo_password():
    """Validate sudo password before creating the main window"""
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        password, ok = QInputDialog.getText(
            None,
            "Sudo Password Required",
            f"This application requires sudo access to manage USB devices.\nEnter your sudo password (attempt {attempts + 1}/{max_attempts}):" if attempts > 0 else "This application requires sudo access to manage USB devices.\nEnter your sudo password:",
            QLineEdit.EchoMode.Password
        )
        
        if not ok:  # User cancelled
            QMessageBox.critical(None, "Error", "Sudo password is required for this application to function properly.")
            return None, app
            
        if not password.strip():  # Empty password
            attempts += 1
            if attempts < max_attempts:
                QMessageBox.warning(None, "Invalid Password", "Password cannot be empty. Please try again.")
                continue
            else:
                QMessageBox.critical(None, "Error", "No valid sudo password provided. Application will exit.")
                return None, app
        
        # Test the password by running a simple sudo command
        if test_sudo_password(password):
            return password, app
        else:
            attempts += 1
            if attempts < max_attempts:
                QMessageBox.warning(None, "Invalid Password", "Incorrect sudo password. Please try again.")
            else:
                QMessageBox.critical(None, "Error", "Invalid sudo password after multiple attempts. Application will exit.")
                return None, app
    
    return None, app

def test_sudo_password(password):
    """Test if the provided sudo password is correct"""
    try:
        proc = subprocess.run(
            ['sudo', '-S', 'true'],  # Simple command that just returns true
            input=password + '\n',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False
        )
        return proc.returncode == 0
    except Exception:
        return False

def main():
    # Check for required dependencies
    #if not check_dependencies():
    #    print("Missing dependencies. Please install them and try again.")
    #    sys.exit(1)

    # Validate sudo password first, before creating the main window
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