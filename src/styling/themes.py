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
        "OLED Blue": "oled_blue",
        "Blue Theme": "blue",
        "Green Theme": "green",
        "Purple Theme": "purple",
        "Orange Theme": "orange",
        "Red Theme": "red",
        "Teal Theme": "teal",
        "Nord Theme": "nord",
        "High Contrast": "high_contrast",
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
        elif theme_key == "oled_blue":
            return self._get_oled_blue_theme_css()
        elif theme_key == "blue":
            return self._get_blue_theme_css()
        elif theme_key == "green":
            return self._get_green_theme_css()
        elif theme_key == "purple":
            return self._get_purple_theme_css()
        elif theme_key == "orange":
            return self._get_orange_theme_css()
        elif theme_key == "red":
            return self._get_red_theme_css()
        elif theme_key == "teal":
            return self._get_teal_theme_css()
        elif theme_key == "nord":
            return self._get_nord_theme_css()
        elif theme_key == "high_contrast":
            return self._get_high_contrast_theme_css()

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
        elif theme_key == "oled_blue":
            return self._get_oled_blue_colors()
        elif theme_key == "blue":
            return self._get_blue_colors()
        elif theme_key == "green":
            return self._get_green_colors()
        elif theme_key == "purple":
            return self._get_purple_colors()
        elif theme_key == "orange":
            return self._get_orange_colors()
        elif theme_key == "red":
            return self._get_red_colors()
        elif theme_key == "teal":
            return self._get_teal_colors()
        elif theme_key == "nord":
            return self._get_nord_colors()
        elif theme_key == "high_contrast":
            return self._get_high_contrast_colors()
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

    def _get_oled_blue_theme_css(self):
        """OLED dark theme with blue accents - pure black with blue highlights"""
        return """
            QMainWindow { background-color: #000000; color: #E3F2FD; }
            QWidget { background-color: #000000; color: #E3F2FD; }
            QDialog { background-color: #000000; color: #E3F2FD; }
            QTableWidget { background-color: #000000; color: #E3F2FD; gridline-color: #1565C0; }
            QTextEdit { background-color: #000000; color: #E3F2FD; border: 1px solid #1976D2; }
            QComboBox { background-color: #000000; color: #E3F2FD; border: 1px solid #1976D2; padding: 4px; }
            QPushButton { 
                background-color: #0D47A1; color: #E3F2FD; border: 1px solid #1976D2; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #1565C0; }
            QCheckBox { color: #E3F2FD; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #42A5F5; 
                background-color: #000000; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #64B5F6; 
                background-color: #1976D2;
            }
            QCheckBox::indicator:hover { border: 2px solid #90CAF9; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #BBDEFB; }
            QLabel { color: #E3F2FD; }
            QScrollArea { background-color: #000000; }
        """

    def _get_blue_theme_css(self):
        """Professional blue theme stylesheet"""
        return """
            QMainWindow { background-color: #1e3a5f; color: #ffffff; }
            QWidget { background-color: #1e3a5f; color: #ffffff; }
            QDialog { background-color: #1e3a5f; color: #ffffff; }
            QTableWidget { background-color: #2563eb; color: #ffffff; gridline-color: #3b82f6; }
            QTextEdit { background-color: #1d4ed8; color: #ffffff; border: 1px solid #3b82f6; }
            QComboBox { background-color: #1d4ed8; color: #ffffff; border: 1px solid #3b82f6; padding: 4px; }
            QPushButton { 
                background-color: #3b82f6; color: #ffffff; border: 1px solid #60a5fa; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #60a5fa; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #93c5fd; 
                background-color: #1d4ed8; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #60a5fa;
            }
            QCheckBox::indicator:hover { border: 2px solid #93c5fd; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #dbeafe; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #1e3a5f; }
        """

    def _get_green_theme_css(self):
        """Nature-inspired green theme stylesheet"""
        return """
            QMainWindow { background-color: #1a4d3a; color: #ffffff; }
            QWidget { background-color: #1a4d3a; color: #ffffff; }
            QDialog { background-color: #1a4d3a; color: #ffffff; }
            QTableWidget { background-color: #22c55e; color: #ffffff; gridline-color: #4ade80; }
            QTextEdit { background-color: #16a34a; color: #ffffff; border: 1px solid #4ade80; }
            QComboBox { background-color: #16a34a; color: #ffffff; border: 1px solid #4ade80; padding: 4px; }
            QPushButton { 
                background-color: #4ade80; color: #ffffff; border: 1px solid #86efac; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #86efac; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #bbf7d0; 
                background-color: #16a34a; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #86efac;
            }
            QCheckBox::indicator:hover { border: 2px solid #bbf7d0; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #dcfce7; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #1a4d3a; }
        """

    def _get_purple_theme_css(self):
        """Modern purple/violet theme stylesheet"""
        return """
            QMainWindow { background-color: #4c1d95; color: #ffffff; }
            QWidget { background-color: #4c1d95; color: #ffffff; }
            QDialog { background-color: #4c1d95; color: #ffffff; }
            QTableWidget { background-color: #8b5cf6; color: #ffffff; gridline-color: #a78bfa; }
            QTextEdit { background-color: #7c3aed; color: #ffffff; border: 1px solid #a78bfa; }
            QComboBox { background-color: #7c3aed; color: #ffffff; border: 1px solid #a78bfa; padding: 4px; }
            QPushButton { 
                background-color: #a78bfa; color: #ffffff; border: 1px solid #c4b5fd; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #c4b5fd; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #ddd6fe; 
                background-color: #7c3aed; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #c4b5fd;
            }
            QCheckBox::indicator:hover { border: 2px solid #ddd6fe; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #ede9fe; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #4c1d95; }
        """

    def _get_orange_theme_css(self):
        """Warm orange/amber theme stylesheet"""
        return """
            QMainWindow { background-color: #9a3412; color: #ffffff; }
            QWidget { background-color: #9a3412; color: #ffffff; }
            QDialog { background-color: #9a3412; color: #ffffff; }
            QTableWidget { background-color: #f97316; color: #ffffff; gridline-color: #fb923c; }
            QTextEdit { background-color: #ea580c; color: #ffffff; border: 1px solid #fb923c; }
            QComboBox { background-color: #ea580c; color: #ffffff; border: 1px solid #fb923c; padding: 4px; }
            QPushButton { 
                background-color: #fb923c; color: #ffffff; border: 1px solid #fdba74; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #fdba74; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #fed7aa; 
                background-color: #ea580c; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #fdba74;
            }
            QCheckBox::indicator:hover { border: 2px solid #fed7aa; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #ffedd5; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #9a3412; }
        """

    def _get_red_theme_css(self):
        """Bold red theme stylesheet"""
        return """
            QMainWindow { background-color: #991b1b; color: #ffffff; }
            QWidget { background-color: #991b1b; color: #ffffff; }
            QDialog { background-color: #991b1b; color: #ffffff; }
            QTableWidget { background-color: #ef4444; color: #ffffff; gridline-color: #f87171; }
            QTextEdit { background-color: #dc2626; color: #ffffff; border: 1px solid #f87171; }
            QComboBox { background-color: #dc2626; color: #ffffff; border: 1px solid #f87171; padding: 4px; }
            QPushButton { 
                background-color: #f87171; color: #ffffff; border: 1px solid #fca5a5; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #fca5a5; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #fecaca; 
                background-color: #dc2626; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #fca5a5;
            }
            QCheckBox::indicator:hover { border: 2px solid #fecaca; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #fee2e2; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #991b1b; }
        """

    def _get_teal_theme_css(self):
        """Calming teal/cyan theme stylesheet"""
        return """
            QMainWindow { background-color: #134e4a; color: #ffffff; }
            QWidget { background-color: #134e4a; color: #ffffff; }
            QDialog { background-color: #134e4a; color: #ffffff; }
            QTableWidget { background-color: #14b8a6; color: #ffffff; gridline-color: #5eead4; }
            QTextEdit { background-color: #0f766e; color: #ffffff; border: 1px solid #5eead4; }
            QComboBox { background-color: #0f766e; color: #ffffff; border: 1px solid #5eead4; padding: 4px; }
            QPushButton { 
                background-color: #5eead4; color: #0f766e; border: 1px solid #99f6e4; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #99f6e4; }
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #99f6e4; 
                background-color: #0f766e; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #ffffff; 
                background-color: #5eead4;
            }
            QCheckBox::indicator:hover { border: 2px solid #99f6e4; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #ccfbf1; }
            QLabel { color: #ffffff; }
            QScrollArea { background-color: #134e4a; }
        """

    def _get_nord_theme_css(self):
        """Popular Nordic color palette theme"""
        return """
            QMainWindow { background-color: #2E3440; color: #D8DEE9; }
            QWidget { background-color: #2E3440; color: #D8DEE9; }
            QDialog { background-color: #2E3440; color: #D8DEE9; }
            QTableWidget { background-color: #3B4252; color: #ECEFF4; gridline-color: #4C566A; }
            QTextEdit { background-color: #3B4252; color: #ECEFF4; border: 1px solid #4C566A; }
            QComboBox { background-color: #3B4252; color: #ECEFF4; border: 1px solid #4C566A; padding: 4px; }
            QPushButton { 
                background-color: #5E81AC; color: #ECEFF4; border: 1px solid #81A1C1; 
                padding: 6px 12px; min-height: 20px; 
            }
            QPushButton:hover { background-color: #81A1C1; }
            QCheckBox { color: #ECEFF4; }
            QCheckBox::indicator { 
                width: 16px; 
                height: 16px; 
                border: 2px solid #D8DEE9; 
                background-color: #3B4252; 
            }
            QCheckBox::indicator:checked { 
                border: 2px solid #88C0D0; 
                background-color: #88C0D0;
            }
            QCheckBox::indicator:hover { border: 2px solid #88C0D0; }
            QCheckBox::indicator:unchecked:hover { border: 2px solid #E5E9F0; }
            QLabel { color: #D8DEE9; }
            QScrollArea { background-color: #2E3440; }
        """

    def _get_high_contrast_theme_css(self):
        """Accessibility-focused high contrast theme"""
        return """
            QMainWindow { background-color: #000000; color: #FFFFFF; }
            QWidget { background-color: #000000; color: #FFFFFF; }
            QDialog { background-color: #000000; color: #FFFFFF; }
            QTableWidget { background-color: #000000; color: #FFFFFF; gridline-color: #FFFFFF; }
            QTextEdit { background-color: #000000; color: #FFFFFF; border: 2px solid #FFFFFF; }
            QComboBox { background-color: #000000; color: #FFFFFF; border: 2px solid #FFFFFF; padding: 4px; }
            QPushButton { 
                background-color: #FFFFFF; color: #000000; border: 2px solid #FFFFFF; 
                padding: 6px 12px; min-height: 20px; font-weight: bold;
            }
            QPushButton:hover { background-color: #FFFF00; color: #000000; border: 2px solid #FFFF00; }
            QCheckBox { color: #FFFFFF; font-weight: bold; }
            QCheckBox::indicator { 
                width: 18px; 
                height: 18px; 
                border: 3px solid #FFFFFF; 
                background-color: #000000; 
            }
            QCheckBox::indicator:checked { 
                border: 3px solid #FFFFFF; 
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:hover { border: 3px solid #FFFF00; }
            QCheckBox::indicator:unchecked:hover { border: 3px solid #FFFF00; }
            QLabel { color: #FFFFFF; font-weight: bold; }
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

    def _get_oled_blue_colors(self):
        """OLED blue theme dialog colors"""
        return {
            "bg_color": "#000000",
            "text_color": "#E3F2FD",
            "header_color": "#64B5F6",
            "border_color": "#1976D2",
            "version_color": "#90CAF9",
            "tip_bg_color": "#000051",
            "tip_border_color": "#42A5F5",
        }

    def _get_blue_colors(self):
        """Blue theme dialog colors"""
        return {
            "bg_color": "#1e3a5f",
            "text_color": "#ffffff",
            "header_color": "#60a5fa",
            "border_color": "#3b82f6",
            "version_color": "#93c5fd",
            "tip_bg_color": "#1d4ed8",
            "tip_border_color": "#60a5fa",
        }

    def _get_green_colors(self):
        """Green theme dialog colors"""
        return {
            "bg_color": "#1a4d3a",
            "text_color": "#ffffff",
            "header_color": "#86efac",
            "border_color": "#4ade80",
            "version_color": "#bbf7d0",
            "tip_bg_color": "#16a34a",
            "tip_border_color": "#86efac",
        }

    def _get_purple_colors(self):
        """Purple theme dialog colors"""
        return {
            "bg_color": "#4c1d95",
            "text_color": "#ffffff",
            "header_color": "#c4b5fd",
            "border_color": "#a78bfa",
            "version_color": "#ddd6fe",
            "tip_bg_color": "#7c3aed",
            "tip_border_color": "#c4b5fd",
        }

    def _get_orange_colors(self):
        """Orange theme dialog colors"""
        return {
            "bg_color": "#9a3412",
            "text_color": "#ffffff",
            "header_color": "#fdba74",
            "border_color": "#fb923c",
            "version_color": "#fed7aa",
            "tip_bg_color": "#ea580c",
            "tip_border_color": "#fdba74",
        }

    def _get_red_colors(self):
        """Red theme dialog colors"""
        return {
            "bg_color": "#991b1b",
            "text_color": "#ffffff",
            "header_color": "#fca5a5",
            "border_color": "#f87171",
            "version_color": "#fecaca",
            "tip_bg_color": "#dc2626",
            "tip_border_color": "#fca5a5",
        }

    def _get_teal_colors(self):
        """Teal theme dialog colors"""
        return {
            "bg_color": "#134e4a",
            "text_color": "#ffffff",
            "header_color": "#5eead4",
            "border_color": "#5eead4",
            "version_color": "#99f6e4",
            "tip_bg_color": "#0f766e",
            "tip_border_color": "#5eead4",
        }

    def _get_nord_colors(self):
        """Nord theme dialog colors"""
        return {
            "bg_color": "#2E3440",
            "text_color": "#ECEFF4",
            "header_color": "#88C0D0",
            "border_color": "#5E81AC",
            "version_color": "#D8DEE9",
            "tip_bg_color": "#3B4252",
            "tip_border_color": "#88C0D0",
        }

    def _get_high_contrast_colors(self):
        """High contrast theme dialog colors"""
        return {
            "bg_color": "#000000",
            "text_color": "#FFFFFF",
            "header_color": "#FFFFFF",
            "border_color": "#FFFFFF",
            "version_color": "#FFFFFF",
            "tip_bg_color": "#000000",
            "tip_border_color": "#FFFFFF",
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
