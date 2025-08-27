"""
Help Dialog - Quick start guide and instructions
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QScrollArea, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class HelpDialog(QDialog):
    """Help dialog showing quick start instructions"""
    
    def __init__(self, parent=None, theme_colors=None, auto_reconnect_status=None, auto_refresh_status=None):
        super().__init__(parent)
        self.setWindowTitle("Help - Quick Start Guide")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        
        # Get theme colors or use defaults
        if theme_colors:
            self.colors = theme_colors
        else:
            self.colors = self._get_default_colors()
        
        # Auto feature status
        self.auto_reconnect_status = auto_reconnect_status or {
            'enabled': False,
            'interval': 30
        }
        self.auto_refresh_status = auto_refresh_status or {
            'enabled': False,
            'interval': 60
        }
        
        self._setup_ui()
    
    def _get_default_colors(self):
        """Default color scheme"""
        return {
            'bg_color': '#f9f9f9',
            'text_color': '#333333',
            'header_color': '#4CAF50',
            'border_color': '#ddd',
            'tip_bg_color': '#e8f5e8',
            'tip_border_color': '#4CAF50'
        }
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        bg_color = self.colors['bg_color']
        text_color = self.colors['text_color']
        header_color = self.colors['header_color']
        border_color = self.colors['border_color']
        tip_bg_color = self.colors['tip_bg_color']
        tip_border_color = self.colors['tip_border_color']

        # Title
        title_label = QLabel("🚀 USBIP GUI - Quick Start Guide")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {header_color}; margin: 10px;")
        layout.addWidget(title_label)

        # Instructions content with scroll
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        instructions_label = QLabel()
        instructions_label.setWordWrap(True)
        instructions_label.setTextFormat(Qt.TextFormat.RichText)
        instructions_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        instructions_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        scroll_layout.addWidget(instructions_label)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        # Build the help content with theme-appropriate colors
        auto_reconnect_status = 'Currently enabled' if self.auto_reconnect_status['enabled'] else 'Currently disabled'
        auto_refresh_status = 'Currently enabled' if self.auto_refresh_status['enabled'] else 'Currently disabled'
        
        help_content = f"""
<h3 style="color: {header_color}; margin-top: 0;">📋 Basic Setup:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>Add an IP / Hostname</b> - Enter your remote server's address</li>
<li><b>Use SSH Devices</b> - Start connection to remote USB/IP daemon</li>
<li><b>IPD Reset</b> - Refreshes the USBIP Daemon on the remote if needed</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">✨ Auto-Reconnect & Auto-Refresh Features:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>Auto-reconnect:</b> {auto_reconnect_status} (checks every {self.auto_reconnect_status['interval']} seconds)</li>
<li><b>Auto-refresh:</b> {auto_refresh_status} (refreshes every {self.auto_refresh_status['interval']} seconds)</li>
<li><b>Per-Device Control:</b> Use 'Auto' column to enable auto-reconnect for specific devices</li>
<li><b>Works for both:</b> ATTACH (local) and BIND (remote) operations</li>
<li><b>Customization:</b> Use 'Settings' button to configure timing and features</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🎯 Device Management:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>Local Devices Table:</b> Shows USB devices attached to your local machine</li>
<li><b>SSH Devices Table:</b> Shows USB devices available on the remote server</li>
<li><b>Toggle Buttons:</b> ATTACH/DETACH devices or BIND/UNBIND remote devices</li>
<li><b>Bulk Operations:</b> Use "Attach All" / "Detach All" for multiple devices</li>
<li><b>Smart Mapping:</b> System automatically correlates remote devices with local ports</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">⚙️ Advanced Features:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>Encrypted Storage:</b> All settings and device mappings are securely stored</li>
<li><b>Grace Period:</b> Auto-reconnect pauses temporarily after bulk operations</li>
<li><b>Console Output:</b> Real-time feedback on all operations and status</li>
<li><b>Persistent State:</b> Device states and settings survive application restarts</li>
</ul>

<p style="margin-top: 25px; padding: 10px; background-color: {tip_bg_color}; border-radius: 5px; border-left: 4px solid {tip_border_color}; color: {text_color};">
<b>💡 Tip:</b> For detailed technical information and source code, click the <b>About</b> button to access the GitHub repository link.
</p>
        """
        
        instructions_label.setText(help_content)
        instructions_label.setStyleSheet(f"""
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
