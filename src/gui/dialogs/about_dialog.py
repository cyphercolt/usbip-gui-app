"""
About Dialog - Application information and credits
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QScrollArea,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import datetime


class AboutDialog(QDialog):
    """About dialog showing application information"""

    def __init__(self, parent=None, theme_colors=None):
        super().__init__(parent)
        self.setWindowTitle("About USBIP GUI")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)

        # Get theme colors or use defaults
        if theme_colors:
            self.colors = theme_colors
        else:
            self.colors = self._get_default_colors()

        self._setup_ui()

    def _get_default_colors(self):
        """Default color scheme"""
        return {
            "bg_color": "#f9f9f9",
            "text_color": "#333333",
            "header_color": "#4CAF50",
            "border_color": "#ddd",
            "version_color": "#666",
        }

    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        bg_color = self.colors["bg_color"]
        text_color = self.colors["text_color"]
        header_color = self.colors["header_color"]
        version_color = self.colors["version_color"]
        border_color = self.colors["border_color"]
        title_color = header_color
        link_color = "#64B5F6" if bg_color == "#000000" else "#2196F3"

        # Title
        title_label = QLabel("🔌 USBIP GUI Application")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {title_color}; margin: 10px;")
        layout.addWidget(title_label)

        # Version and description
        version_label = QLabel(
            "Version 2.4.3 - USB/IP Management with Enhanced User Experience & Colorful Themes"
        )
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(
            f"font-size: 12px; color: {version_color}; margin-bottom: 15px;"
        )
        layout.addWidget(version_label)

        # Content area with scroll
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        content_label = QLabel()
        content_label.setWordWrap(True)
        content_label.setOpenExternalLinks(True)
        content_label.setTextFormat(Qt.TextFormat.RichText)
        content_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        scroll_layout.addWidget(content_label)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)

        # Build the about content with theme-appropriate colors
        current_year = datetime.datetime.now().year
        about_content = f"""
<h3 style="color: {header_color}; margin-top: 0;">✨ Key Features:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>🧠 <b>Smart IP Memory</b> - Remembers last selected IP on application restart for seamless workflow</li>
<li>🔄 <b>Smart Auto-Reconnect System</b> - Intelligent device reconnection with Windows auto-bind fixes</li>
<li>🔐 <b>Enhanced SSH Management</b> - Fixed disconnect behavior and improved daemon control commands</li>
<li>🔃 <b>Enhanced Auto-Refresh</b> - Preserves settings and device states during updates with proper SSH handling</li>
<li>🛠️ <b>Fixed Auto-Bind for Windows</b> - Proper OS-specific commands with success validation</li>
<li>⚙️ <b>Complete Linux Service Support</b> - Enable/disable systemctl commands for usbipd service management</li>
<li>🎨 <b>Complete Theme System</b> - 13 beautiful themes (System, Light, Dark, OLED, OLED Blue, Blue, Green, Purple, Orange, Red, Teal, Nord, High Contrast) with full persistence</li>
<li>🖥️ <b>Seamless SSH Integration</b> - Remote USB/IP daemon management with proper disconnect handling</li>
<li>📊 <b>Intelligent Device Mapping</b> - Smart correlation between remote and local devices</li>
<li>⚙️ <b>Comprehensive Settings</b> - Customizable intervals, grace periods, and theming with persistence</li>
<li>🎯 <b>Per-Device Control</b> - Individual auto-reconnect settings with visual indicators</li>
<li>🚀 <b>Robust Bulk Operations</b> - Multi-device operations with grace period handling</li>
<li>🛡️ <b>Enhanced Reliability</b> - Qt signal blocking prevents unwanted operations</li>
<li>🐧 <b>Linux Service Management</b> - Comprehensive USB/IP daemon control with real-time status</li>
<li>🔧 <b>Cross-Platform Service Support</b> - Windows usbipd and Linux usbipd management</li>
<li>🏗️ <b>CI/CD Pipeline</b> - Automated builds, testing, and releases for both platforms</li>
</ul>




<div style="margin-top: 30px; padding: 15px; text-align: center; border-top: 2px solid {header_color}; color: {text_color};">
<p style="margin: 5px 0; font-style: italic;">🚀 {current_year} - Enhanced USB/IP Management Solution</p>
<p style="margin: 5px 0; font-size: 10px; color: {version_color};">Free and open source software - Continuously improved with user feedback</p>
</div>
        """

        content_label.setText(about_content)
        content_label.setStyleSheet(
            f"""
            font-size: 12px; 
            background-color: {bg_color}; 
            color: {text_color};
            border: 1px solid {border_color}; 
            border-radius: 5px; 
            padding: 10px;
        """
        )

        layout.addWidget(scroll_area)

        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
