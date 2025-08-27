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
<li><b>Use 'Manage IPs'</b> - Safely add IP addresses without connecting to them</li>
<li><b>Select an IP</b> - Choose from dropdown (pings automatically with latency display)</li>
<li><b>Click 'Refresh'</b> - Load devices when ready</li>
<li><b>Use SSH Devices</b> - Start connection to remote USB/IP daemon</li>
<li><b>IPD Reset</b> - Refreshes the USBIP Daemon on the remote if needed</li>
<li><b>Settings</b> - Access debug mode, console preferences, and configuration options</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">� Gaming & Performance Features:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>🏓 Real-time Ping Monitoring:</b> Live latency display with automatic updates</li>
<li><b>⏱️ Timeout Protection:</b> 15-second timeouts prevent hanging on bad IPs</li>
<li><b>💬 Console Modes:</b> Toggle verbose console in settings for detailed output</li>
<li><b>🔍 Debug Mode:</b> Enable in settings for advanced troubleshooting tools</li>
<li><b>📝 Smart Messages:</b> See device names instead of technical bus IDs</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">�🎯 Ping Status Indicator Colors:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>🟢 Green - Excellent (≤50ms):</b> Perfect for gaming and real-time applications</li>
<li><b>🟡 Light Green - Good (51-100ms):</b> Great for most games and applications</li>
<li><b>🟡 Yellow - Fair (101-150ms):</b> OK for casual gaming, noticeable in fast-paced games</li>
<li><b>🟠 Orange - High (151-300ms):</b> Poor for gaming, frustrating for real-time tasks</li>
<li><b>🔴 Red - Very High (>300ms):</b> Unplayable for most games, severe lag</li>
<li><b>🔴 Red - Connection Issues:</b> Offline, timeout, or connection failed</li>
<li><b>🔵 Blue - Checking:</b> Currently testing connection</li>
<li><b>⚫ Gray - Unknown:</b> No IP selected or initial state</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🎨 Theme & Interface:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li><b>4 Beautiful Themes:</b> System (adaptive), Light, Dark, and OLED (pure black)</li>
<li><b>Persistent Settings:</b> Your theme choice and preferences are automatically saved</li>
<li><b>Smart Refresh:</b> Interface updates preserve all your settings and device states</li>
<li><b>Themed Dialogs:</b> All windows and prompts respect your selected theme</li>
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
<li><b>Enhanced Security:</b> AES-256 encryption with all settings and device mappings securely stored</li>
<li><b>Smart Grace Period:</b> Auto-reconnect intelligently pauses after bulk operations</li>
<li><b>Real-time Console:</b> Comprehensive feedback on all operations and status updates</li>
<li><b>Robust State Management:</b> Device states and settings survive application restarts and theme changes</li>
<li><b>Signal Protection:</b> Enhanced Qt handling prevents unwanted operations during refresh</li>
<li><b>Unified Storage:</b> Consistent encrypted file format ensures reliable data handling</li>
</ul>

<h3 style="color: {header_color}; margin-top: 20px;">🔧 Recent Improvements:</h3>
<ul style="margin-left: 20px; line-height: 1.6; color: {text_color};">
<li>✅ <b>Gaming-Focused Ping System:</b> Real-time latency monitoring with color-coded performance indicators</li>
<li>✅ <b>Enhanced Console System:</b> Verbose mode for debugging, simple mode for clean output</li>
<li>✅ <b>Safe IP Management:</b> Dedicated dialog prevents app hangs on bad IPs</li>
<li>✅ <b>Timeout Protection:</b> Universal 15-second timeouts prevent hanging</li>
<li>✅ <b>Debug Mode System:</b> Hidden developer tools accessible through settings</li>
<li>✅ <b>Smart Device Messages:</b> User-friendly device names improve readability</li>
<li>✅ <b>Fixed Auto-Refresh Issues:</b> No more unwanted device operations during refresh</li>
<li>✅ <b>Enhanced State Persistence:</b> Auto-reconnect settings survive all changes</li>
<li>✅ <b>Complete Theme Support:</b> All dialogs and prompts respect selected theme</li>
<li>✅ <b>Improved Reliability:</b> Comprehensive error prevention and signal blocking</li>
</ul>

<p style="margin-top: 25px; padding: 10px; background-color: {tip_bg_color}; border-radius: 5px; border-left: 4px solid {tip_border_color}; color: {text_color};">
<b>💡 Tip:</b> For detailed technical information, recent updates, and source code, click the <b>About</b> button to access comprehensive project details and the GitHub repository.
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
