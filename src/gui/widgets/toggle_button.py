"""
ToggleButton Widget - Custom toggle button component
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import pyqtSignal


class ToggleButton(QPushButton):
    """Custom toggle button that's more visible than checkboxes"""

    toggled = pyqtSignal(bool)

    def __init__(self, text_on="ON", text_off="OFF", parent=None):
        super().__init__(parent)
        self.text_on = text_on
        self.text_off = text_off
        self._state = False
        self.clicked.connect(self.toggle)
        self.update_appearance()

    def toggle(self):
        self._state = not self._state
        self.update_appearance()
        self.toggled.emit(self._state)

    def setChecked(self, checked):
        if self._state != checked:
            self._state = checked
            self.update_appearance()

    def isChecked(self):
        return self._state

    def update_appearance(self):
        if self._state:
            self.setText(self.text_on)
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: 2px solid #45a049;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """
            )
        else:
            self.setText(self.text_off)
            self.setStyleSheet(
                """
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: 2px solid #da190b;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """
            )
