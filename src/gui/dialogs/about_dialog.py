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
<li>🔄 <b>Smart Auto-Reconnect System</b> - Intelligent device reconnection with failure handling</li>
<li>🔃 <b>Enhanced Auto-Refresh</b> - Preserves settings and device states during updates</li>
<li>🎨 <b>Complete Theme System</b> - 4 beautiful themes (System, Light, Dark, OLED) with full persistence</li>
<li>🔒 <b>Advanced Security</b> - AES-256 encryption with military-grade memory protection</li>
<li>🖥️ <b>Seamless SSH Integration</b> - Secure remote USB/IP daemon management</li>
<li>📊 <b>Intelligent Device Mapping</b> - Smart correlation between remote and local devices</li>
<li>⚙️ <b>Comprehensive Settings</b> - Customizable intervals, grace periods, and theming</li>
<li>🎯 <b>Per-Device Control</b> - Individual auto-reconnect settings with visual indicators</li>
<li>🚀 <b>Robust Bulk Operations</b> - Multi-device operations with grace period handling</li>
<li>🛡️ <b>Enhanced Reliability</b> - Qt signal blocking prevents unwanted operations</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🛠️ Technical Excellence:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>Built with <b>PyQt6</b> for modern, responsive UI with enhanced signal handling</li>
<li><b>AES-256</b> encryption with dynamic salt generation for secure data storage</li>
<li><b>USB/IP protocol</b> support for kernel-level USB forwarding</li>
<li><b>Cross-platform</b> compatible (Linux primary support)</li>
<li><b>Memory-safe</b> password handling with advanced obfuscation and secure cleanup</li>
<li><b>Complete Theming</b> - 4 themes with persistent settings and themed dialogs</li>
<li><b>Unified Storage</b> - Consistent encrypted file format with atomic operations</li>
<li><b>Smart Refresh Logic</b> - UI updates preserve user settings and device states</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🔧 Recent Major Improvements:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>✅ <b>Signal Blocking</b> - Fixed auto-refresh causing unwanted device operations</li>
<li>✅ <b>State Persistence</b> - Auto-reconnect settings survive all UI updates and theme changes</li>
<li>✅ <b>Theme Consistency</b> - All dialogs and components respect selected theme</li>
<li>✅ <b>Unified Storage</b> - Eliminated duplicate storage methods for consistent data handling</li>
<li>✅ <b>Enhanced Reliability</b> - Comprehensive error prevention and robust state management</li>
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
<li>🎯 <b>Production Ready:</b> Comprehensive error handling and intelligent state management</li>
<li>🔐 <b>Security First:</b> Military-grade encryption and secure password handling</li>
<li>🎨 <b>Beautiful UI:</b> 4 stunning themes with complete theming system</li>
<li>🔧 <b>Robust Architecture:</b> Enhanced Qt signal handling and unified storage system</li>
<li>📱 <b>User Friendly:</b> Intuitive interface with comprehensive help and smart refresh</li>
<li>🛡️ <b>Reliability Focused:</b> Signal blocking and state preservation for stable operation</li>
</ul>

<div style="margin-top: 30px; padding: 15px; text-align: center; border-top: 2px solid {header_color}; color: {text_color};">
<p style="margin: 5px 0; font-style: italic;">🚀 {current_year} - Enhanced USB/IP Management Solution</p>
<p style="margin: 5px 0; font-size: 11px; color: {version_color};">Enterprise-grade reliability with comprehensive fixes and improvements</p>
<p style="margin: 5px 0; font-size: 10px; color: {version_color};">Free and open source software - Continuously improved with user feedback</p>
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
