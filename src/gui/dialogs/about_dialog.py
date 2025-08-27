"""
About Dialog - Application information and credits
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea, QWidget
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
            'bg_color': '#f9f9f9',
            'text_color': '#333333',
            'header_color': '#4CAF50',
            'border_color': '#ddd',
            'version_color': '#666'
        }
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        bg_color = self.colors['bg_color']
        text_color = self.colors['text_color']
        header_color = self.colors['header_color']
        version_color = self.colors['version_color']
        border_color = self.colors['border_color']
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
        version_label = QLabel("Version 2.0.0 - Advanced USB/IP Management Tool")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet(f"font-size: 12px; color: {version_color}; margin-bottom: 15px;")
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
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        scroll_layout.addWidget(content_label)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Build the about content with theme-appropriate colors
        current_year = datetime.datetime.now().year
        about_content = f"""
<h3 style="color: {header_color}; margin-top: 0;">✨ Key Features:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>🔄 <b>Auto-Reconnect System</b> - Automatically reconnect dropped USB devices</li>
<li>🔃 <b>Auto-Refresh</b> - Keep device lists updated in real-time</li>
<li>🔒 <b>Secure State Management</b> - Encrypted storage of settings and device mappings</li>
<li>🖥️ <b>SSH Integration</b> - Seamless remote USB/IP daemon management</li>
<li>📊 <b>Device Mapping</b> - Smart correlation between remote and local devices</li>
<li>⚙️ <b>Advanced Settings</b> - Customizable intervals, grace periods, and more</li>
<li>🎯 <b>Per-Device Control</b> - Individual auto-reconnect settings per device</li>
<li>🚀 <b>Bulk Operations</b> - Attach/detach multiple devices with grace period handling</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🛠️ Technical Information:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>Built with <b>PyQt6</b> for modern, responsive UI</li>
<li><b>AES-256</b> encryption for secure data storage</li>
<li><b>USB/IP protocol</b> support for kernel-level USB forwarding</li>
<li><b>Cross-platform</b> compatible (Linux primary support)</li>
<li><b>Memory-safe</b> password handling with secure cleanup</li>
<li><b>Dark/Light mode</b> automatic theme detection and adaptation</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🔗 Source Code & Updates:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>GitHub Repository:</b> <a href="https://github.com/cyphercolt/usbip-gui-app" style="color: {link_color}; text-decoration: none;">github.com/cyphercolt/usbip-gui-app</a></li>
<li>🐛 <b>Report Issues:</b> Submit bug reports and feature requests</li>
<li>🔄 <b>Latest Updates:</b> Check for new releases and improvements</li>
<li>📖 <b>Documentation:</b> Setup guides and usage instructions</li>
<li>⭐ <b>Star the Project:</b> Show your support for continued development</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🏆 Project Highlights:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>🎯 <b>Production Ready:</b> Robust error handling and state management</li>
<li>🔐 <b>Security First:</b> Encrypted storage and secure password handling</li>
<li>🎨 <b>Modern UI:</b> Responsive design with dark/light mode support</li>
<li>🔧 <b>Extensible:</b> Clean architecture for future enhancements</li>
<li>📱 <b>User Friendly:</b> Intuitive interface with comprehensive help system</li>
</ul>

<div style="margin-top: 30px; padding: 15px; text-align: center; border-top: 2px solid {header_color}; color: {text_color};">
<p style="margin: 5px 0; font-style: italic;">🚀 {current_year} - Open Source USB/IP Management Solution</p>
<p style="margin: 5px 0; font-size: 11px; color: {version_color};">Empowering remote USB device access with enterprise-grade reliability</p>
<p style="margin: 5px 0; font-size: 10px; color: {version_color};">Free and open source software - Built by the community, for the community</p>
</div>
        """
        
        content_label.setText(about_content)
        content_label.setStyleSheet(f"""
            font-size: 12px; 
            background-color: {bg_color}; 
            color: {text_color};
            border: 1px solid {border_color}; 
            border-radius: 5px; 
            padding: 10px;
        """)
        
        layout.addWidget(scroll_area)

        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
