import sys
from PyQt6.QtWidgets import QApplication
from gui.window import MainWindow
from dependencies.checker import check_dependencies

def main():
    # Check for required dependencies
    #if not check_dependencies():
    #    print("Missing dependencies. Please install them and try again.")
    #    sys.exit(1)

    # Initialize the application
    app = QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Execute the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()