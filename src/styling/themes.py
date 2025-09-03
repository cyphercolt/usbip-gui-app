"""
Theme management for USBIP GUI Application
Handles all styling and theme-related functionality
"""

from PyQt6.QtGui import QPalette


class ThemeManager:
    """Manages application themes and styling"""

    THEMES = {
        "System Theme": "system",
        "Light Theme": "light",
        "Dark Theme": "dark",
        "OLED Dark": "oled",
    }

    def __init__(self):
        self.current_theme = "System Theme"

    def set_theme(self, theme_name):
        """Set the current theme"""
        if theme_name in self.THEMES:
            self.current_theme = theme_name

    def get_stylesheet(self, theme_name=None):
        """Get the stylesheet for the specified theme"""
        if theme_name is None:
            theme_name = self.current_theme

        theme_key = self.THEMES.get(theme_name, "system")

        if theme_key == "system":
            return ""  # Use system default
        elif theme_key == "light":
            return self._get_light_theme_css()
        elif theme_key == "dark":
            return self._get_dark_theme_css()
        elif theme_key == "oled":
            return self._get_oled_theme_css()

        return ""

    def get_dialog_colors(self, theme_name=None, palette=None):
        """Get theme-appropriate colors for dialogs"""
        if theme_name is None:
            theme_name = self.current_theme

        theme_key = self.THEMES.get(theme_name, "system")

        if theme_key == "light":
            return self._get_light_colors()
        elif theme_key == "dark":
            return self._get_dark_colors()
        elif theme_key == "oled":
            return self._get_oled_colors()
        else:  # System theme
            return self._get_system_colors(palette)

    def _get_light_theme_css(self):
        """Light theme stylesheet"""
        return """
            QMainWindow { background-color: #ffffff; color: #000000; }
            QWidget { background-color: #ffffff; color: #000000; }
            QDialog { background-color: #ffffff; color: #000000; }
            QTableWidget { background-color: #ffffff; color: #000000; gridline-color: #cccccc; }
            QTextEdit { background-color: #ffffff; color: #000000; border: 1px solid #cccccc; }
            QComboBox { background-color: #ffffff; color: #000000; border: 1px solid #cccccc; padding: 4px; }
            QPushButton { 
                background-color: #f0f0f0; color: #000000; border: 1px solid #cccccc; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #e0e0e0; }
            QCheckBox { color: #000000; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #666666; background-color: #ffffff; }
            QCheckBox::indicator:checked { background-color: #4CAF50; border: 1px solid #4CAF50; }
            QCheckBox::indicator:hover { border: 2px solid #4CAF50; }
            QLabel { color: #000000; }
            QScrollArea { background-color: #ffffff; }
        """

    def _get_dark_theme_css(self):
        """Dark theme stylesheet"""
        return """
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QWidget { background-color: #2b2b2b; color: #ffffff; }
            QDialog { background-color: #2b2b2b; color: #ffffff; }
            QTableWidget { background-color: #3c3c3c; color: #ffffff; gridline-color: #555555; }
            QTextEdit { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; }
            QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555555; padding: 4px; }
            QPushButton { 
                background-color: #404040; color: #ffffff; border: 1px solid #555555; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #505050; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #888888; 
                background-color: #3c3c3c; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover { border: 2px solid #66BB6A; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #aaaaaa; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #2b2b2b; }
        """

    def _get_oled_theme_css(self):
        """OLED dark theme stylesheet with pure black backgrounds"""
        return """
            QMainWindow { background-color: #000000; color: #ffffff; }
            QWidget { background-color: #000000; color: #ffffff; }
            QDialog { background-color: #000000; color: #ffffff; }
            QTableWidget { background-color: #111111; color: #ffffff; gridline-color: #333333; }
            QTextEdit { background-color: #000000; color: #ffffff; border: 1px solid #333333; }
            QComboBox { background-color: #111111; color: #ffffff; border: 1px solid #333333; padding: 4px; }
            QPushButton { 
                background-color: #222222; color: #ffffff; border: 1px solid #333333; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #333333; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #bbbbbb; 
                background-color: #111111; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover { border: 2px solid #66BB6A; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #dddddd; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #000000; }
        """

    def _get_light_colors(self):
        """Light theme dialog colors"""
        return {
            "bg_color": "#ffffff",
            "text_color": "#333333",
            "header_color": "#4CAF50",
            "border_color": "#ddd",
            "version_color": "#666",
            "tip_bg_color": "#e8f5e8",
            "tip_border_color": "#4CAF50",
        }

    def _get_dark_colors(self):
        """Dark theme dialog colors"""
        return {
            "bg_color": "#2b2b2b",
            "text_color": "#ffffff",
            "header_color": "#4CAF50",
            "border_color": "#555",
            "version_color": "#ccc",
            "tip_bg_color": "#1e3a1e",
            "tip_border_color": "#4CAF50",
        }

    def _get_oled_colors(self):
        """OLED dark theme dialog colors"""
        return {
            "bg_color": "#000000",
            "text_color": "#ffffff",
            "header_color": "#4CAF50",
            "border_color": "#333",
            "version_color": "#ccc",
            "tip_bg_color": "#001100",
            "tip_border_color": "#4CAF50",
        }

    def _get_system_colors(self, palette):
        """System theme dialog colors based on system palette"""
        if palette is None:
            # Fallback to light theme if no palette provided
            return self._get_light_colors()

        is_dark_mode = palette.color(QPalette.ColorRole.Window).lightness() < 128

        if is_dark_mode:
            return self._get_dark_colors()
        else:
            return {
                "bg_color": "#f9f9f9",
                "text_color": "#333333",
                "header_color": "#4CAF50",
                "border_color": "#ddd",
                "version_color": "#666",
                "tip_bg_color": "#e8f5e8",
                "tip_border_color": "#4CAF50",
            }

    @classmethod
    def get_available_themes(cls):
        """Get list of available theme names"""
        return list(cls.THEMES.keys())
