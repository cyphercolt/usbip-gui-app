import json
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox, QInputDialog, QTextEdit, QCheckBox, QLineEdit,
                             QSplitter, QHeaderView, QSpinBox, QGroupBox, QFormLayout,
                             QScrollArea, QDialogButtonBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPalette, QMovie
import subprocess
from functools import partial
import paramiko
import time
from security.crypto import FileEncryption, MemoryProtection
from security.validator import SecurityValidator, SecureCommandBuilder
from security.rate_limiter import ConnectionSecurity
from styling.themes import ThemeManager
from gui.widgets.toggle_button import ToggleButton
from gui.dialogs.about_dialog import AboutDialog
from gui.dialogs.help_dialog import HelpDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.ip_management_dialog import IPManagementDialog
from gui.controllers.auto_reconnect_controller import AutoReconnectController
from gui.controllers.device_management_controller import DeviceManagementController
from gui.controllers.ssh_management_controller import SSHManagementController
from gui.controllers.data_persistence_controller import DataPersistenceController

IPS_FILE = "ips.enc"
STATE_FILE = "usbip_state.enc" 
SSH_STATE_FILE = "ssh_state.enc"
AUTO_RECONNECT_FILE = "auto_reconnect.enc"
DEVICE_MAPPING_FILE = "device_mapping.enc"


class MainWindow(QMainWindow):
    def __init__(self, sudo_password):
        super().__init__()
        
        # Initialize encryption
        self.file_crypto = FileEncryption()
        self.memory_crypto = MemoryProtection()
        self.connection_security = ConnectionSecurity()
        
        self.setWindowTitle("USBIP GUI Application")
        self.setGeometry(100, 100, 1000, 900)  # Increased height from 600 to 900 to accommodate larger console and device tables

        # Store the validated sudo password securely
        self._obfuscated_sudo_password = self.memory_crypto.obfuscate_string(sudo_password)
        # Clear the plain text password parameter
        sudo_password = "0" * len(sudo_password)

        self.ssh_client = None  # SSH client reference

        # Initialize controllers early (before UI setup that references them)
        self.device_management_controller = DeviceManagementController(self)
        self.ssh_management_controller = SSHManagementController(self)
        self.data_persistence_controller = DataPersistenceController(self)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # IP input section with ping status indicator
        ip_section = QHBoxLayout()
        ip_section.addWidget(QLabel("IP Address/Hostname:"))
        
        # Ping status indicator
        self.ping_status_widget = QWidget()
        ping_status_layout = QHBoxLayout()
        ping_status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ping_status_indicator = QLabel("●")
        self.ping_status_indicator.setStyleSheet("color: gray; font-size: 14px; font-weight: bold;")
        self.ping_status_label = QLabel("Unknown")
        self.ping_status_label.setStyleSheet("color: gray; font-size: 12px;")
        
        ping_status_layout.addWidget(self.ping_status_indicator)
        ping_status_layout.addWidget(self.ping_status_label)
        ping_status_layout.addStretch()
        self.ping_status_widget.setLayout(ping_status_layout)
        
        ip_section.addWidget(self.ping_status_widget)
        ip_section.addStretch()
        self.layout.addLayout(ip_section)

        self.ip_input = QComboBox()
        self.layout.addWidget(self.ip_input)
        self.ip_input.currentIndexChanged.connect(self.on_ip_changed)

        btn_layout = QHBoxLayout()
        
        self.manage_ips_button = QPushButton("Manage IPs")
        self.manage_ips_button.clicked.connect(self.show_ip_management)
        self.manage_ips_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        btn_layout.addWidget(self.manage_ips_button)

        self.ping_button = QPushButton("Ping")
        self.ping_button.clicked.connect(self.ping_ip)
        btn_layout.addWidget(self.ping_button)
        
        # Add test ping colors button for demonstration
        self.test_colors_button = QPushButton("Test Colors")
        self.test_colors_button.clicked.connect(self.test_ping_colors)
        self.test_colors_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        self.test_colors_button.setToolTip("Cycle through different ping latency colors for testing")
        self.test_colors_button.setVisible(False)  # Hidden by default, shown in debug mode
        btn_layout.addWidget(self.test_colors_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all_tables)
        btn_layout.addWidget(self.refresh_button)

        self.ssh_button = QPushButton("SSH Devices")
        self.ssh_button.clicked.connect(self.ssh_management_controller.prompt_ssh_credentials)
        btn_layout.addWidget(self.ssh_button)

        self.ssh_disco_button = QPushButton("SSH Disco")
        self.ssh_disco_button.clicked.connect(self.ssh_management_controller.disconnect_ssh)
        self.ssh_disco_button.setVisible(False)
        btn_layout.addWidget(self.ssh_disco_button)

        self.ipd_reset_button = QPushButton("IPD Reset")
        self.ipd_reset_button.clicked.connect(self.reset_usbipd)
        self.ipd_reset_button.setVisible(False)
        btn_layout.addWidget(self.ipd_reset_button)

        # Auto-reconnect controls
        self.auto_reconnect_enabled = True
        self.auto_reconnect_grace_period = False  # Flag to pause auto-reconnect temporarily

        # Console verbosity settings
        self.verbose_console = False  # Default to simple console mode
        self.console_messages = []  # Store all messages (both simple and verbose)
        self.simple_messages = []   # Store only simple messages for non-verbose mode
        
        # Debug mode settings
        self.debug_mode = False  # Default to disabled

        # Auto-reconnect settings button
        self.auto_settings_button = QPushButton("Settings")
        self.auto_settings_button.clicked.connect(self.show_auto_reconnect_settings)
        btn_layout.addWidget(self.auto_settings_button)

        # Initialize ping status timer for periodic updates
        self.ping_status_timer = QTimer()
        self.ping_status_timer.timeout.connect(self.auto_ping_status)
        self.ping_status_timer.setInterval(30000)  # Ping every 30 seconds
        # Timer will start when an IP is selected

        self.layout.addLayout(btn_layout)

        # --- Resizable splitter with two tables ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Local table widget
        local_widget = QWidget()
        local_layout = QVBoxLayout()
        local_layout.addWidget(QLabel("Local Devices"))
        
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(4)
        self.device_table.setHorizontalHeaderLabels(["Device", "Description", "Action", "Auto"])
        
        # Make tables sortable
        self.device_table.setSortingEnabled(True)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Make columns resizable
        
        local_layout.addWidget(self.device_table)
        
        # Attach All / Detach All buttons under local table
        self.attach_all_button = QPushButton("Attach All")
        self.attach_all_button.clicked.connect(self.attach_all_devices)
        self.detach_all_button = QPushButton("Detach All")
        self.detach_all_button.clicked.connect(self.detach_all_devices)
        btns_widget = QWidget()
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        btns_layout.addWidget(self.attach_all_button)
        btns_layout.addWidget(self.detach_all_button)
        btns_widget.setLayout(btns_layout)
        local_layout.addWidget(btns_widget)
        local_widget.setLayout(local_layout)
        
        # Remote SSH table widget
        remote_widget = QWidget()
        remote_layout = QVBoxLayout()
        remote_layout.addWidget(QLabel("Remote SSH Devices"))
        
        self.remote_table = QTableWidget()
        self.remote_table.setColumnCount(4)
        self.remote_table.setHorizontalHeaderLabels(["Device", "Description", "Action", "Auto"])
        
        # Make remote table sortable too
        self.remote_table.setSortingEnabled(True)
        self.remote_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Make columns resizable
        
        remote_layout.addWidget(self.remote_table)
        
        # Unbind All button under remote table
        self.unbind_all_button = QPushButton("Unbind All")
        self.unbind_all_button.clicked.connect(self.unbind_all_devices)
        self.unbind_all_button.setVisible(False)  # Initially hidden
        remote_btns_widget = QWidget()
        remote_btns_layout = QHBoxLayout()
        remote_btns_layout.addStretch()
        remote_btns_layout.addWidget(self.unbind_all_button)
        remote_btns_widget.setLayout(remote_btns_layout)
        remote_layout.addWidget(remote_btns_widget)
        remote_widget.setLayout(remote_layout)
        
        # Add both widgets to splitter
        splitter.addWidget(local_widget)
        splitter.addWidget(remote_widget)
        splitter.setSizes([400, 400])  # Equal initial sizes
        
        self.layout.addWidget(splitter)

        # Console section
        console_layout = QVBoxLayout()
        console_layout.addWidget(QLabel("Console Output:"))
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(320)  # Increased from 260 to 320 to accommodate all welcome text
        console_layout.addWidget(self.console)
        
        # Clear button at bottom left of console
        console_bottom_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_console)
        console_bottom_layout.addWidget(self.clear_button)
        console_bottom_layout.addStretch()
        console_layout.addLayout(console_bottom_layout)
        
        self.layout.addLayout(console_layout)

        # About, Help, and Exit buttons at bottom right
        exit_layout = QHBoxLayout()
        exit_layout.addStretch()
        
        # About button
        self.about_button = QPushButton("About")
        self.about_button.clicked.connect(self.show_about_dialog)
        self.about_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: 2px solid #1976D2;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        exit_layout.addWidget(self.about_button)
        
        # Help button
        self.help_button = QPushButton("Help")
        self.help_button.clicked.connect(self.show_help_dialog)
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 2px solid #45a049;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        exit_layout.addWidget(self.help_button)
        
        # Exit button
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        exit_layout.addWidget(self.exit_button)
        self.layout.addLayout(exit_layout)

        self.load_ips()
        # Don't auto-load devices on startup to prevent hanging
        # User can click Refresh to load devices when ready
        
        # Trigger initial ping if an IP is already selected
        self.check_initial_ping()
        
        # Initialize auto-reconnect system
        self.auto_reconnect_interval = 30  # seconds
        self.auto_reconnect_max_attempts = 5
        self.grace_period_duration = 60  # seconds
        self.auto_reconnect_attempts = {}  # Track attempts per device
        
        # Initialize auto-refresh system
        self.auto_refresh_enabled = False
        self.auto_refresh_interval = 60  # seconds
        
        # Show welcome message with color guide
        self.show_welcome_message()
        
        # Initialize theme system
        self.theme_manager = ThemeManager()
        self.theme_setting = "System Theme"  # Default: "System Theme", "Light Theme", "Dark Theme", "OLED Dark"
        
        # Initialize timers before loading settings
        # Auto-reconnect timer
        self.auto_reconnect_timer = QTimer()
        
        # Initialize auto-reconnect controller
        self.auto_reconnect_controller = AutoReconnectController(self)
        self.auto_reconnect_timer.timeout.connect(self.auto_reconnect_controller.check_auto_reconnect)
        
        # Auto-refresh timer
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.device_management_controller.auto_refresh_devices)
        
        # Grace period timer for manual operations
        self.grace_period_timer = QTimer()
        self.grace_period_timer.setSingleShot(True)  # One-time timer
        self.grace_period_timer.timeout.connect(self.end_grace_period)
        
        # Load settings and start timers
        self.load_auto_reconnect_settings()
        
        # Start auto-reconnect timer
        self.auto_reconnect_timer.start(self.auto_reconnect_interval * 1000)  # Convert to milliseconds
        
        # Clear console after initial loading and show clean welcome message
        self.console.clear()
        self.show_welcome_message()

    def show_welcome_message(self):
        """Show helpful instructions in the console on startup"""
        self.append_simple_message("🚀 Welcome to USBIP GUI Application!")
        self.append_simple_message("")
        self.append_simple_message("Quick Start Instructions:")
        self.append_simple_message("• Use 'Manage IPs' to safely add IP addresses")
        self.append_simple_message("• Select an IP from dropdown (pings automatically)")
        self.append_simple_message("• Click 'Refresh' to load devices when ready")
        self.append_simple_message("• Use 'SSH Devices' to start connection")
        self.append_simple_message("")
        self.append_simple_message("💡 TIP: Check 'Help' for ping status colors and detailed guides")
        self.append_simple_message("")
        self.append_simple_message("✨ Auto-Reconnect & Auto-Refresh Features:")
        self.append_simple_message(f"• Auto-reconnect {'enabled' if self.auto_reconnect_enabled else 'disabled'} every {self.auto_reconnect_interval} seconds")
        self.append_simple_message("• Use 'Auto' column to enable per-device auto-reconnect")
        self.append_simple_message("• Use 'Settings' to customize timing and enable/disable features")
        self.append_simple_message("")
        self.append_simple_message("Ready for device management!")
        self.append_simple_message("=" * 50)
        self.append_simple_message("")

    def create_table_item_with_tooltip(self, text):
        """Create a QTableWidgetItem with tooltip for long text"""
        item = QTableWidgetItem(text)
        item.setToolTip(text)  # Set full text as tooltip
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make non-editable
        return item

    def attach_all_devices(self):
        """Attach all detached devices (delegate to controller)"""
        self.device_management_controller.attach_all_devices()

    def detach_all_devices(self):
        """Detach all attached devices (delegate to controller)"""
        self.device_management_controller.detach_all_devices()

    def unbind_all_devices(self):
        """Unbind all bound devices on the remote SSH server (delegate to controller)"""
        self.device_management_controller.unbind_all_devices()

    def on_ip_changed(self):
        """Handle IP address change - ping immediately but don't auto-load devices"""
        # Clear device table when IP changes to prevent confusion
        self.device_table.setRowCount(0)
        
        # Reset ping status when IP changes
        ip = self.ip_input.currentText()
        if ip:
            self.update_ping_status("unknown")
            # Ping immediately when IP changes
            if SecurityValidator.validate_ip_or_hostname(ip):
                self.ping_current_ip()
                self.ping_status_timer.start()
            else:
                self.ping_status_timer.stop()
        else:
            self.update_ping_status("unknown")
            self.ping_status_timer.stop()
        
        # Show message that devices need to be loaded manually
        if ip:
            self.append_simple_message(f"📋 IP changed to {ip}. Click 'Refresh' to load devices safely.")
    
    def check_initial_ping(self):
        """Check if we should ping immediately on startup"""
        ip = self.ip_input.currentText()
        if ip and SecurityValidator.validate_ip_or_hostname(ip):
            # Ping immediately on startup if we have a valid IP
            self.ping_current_ip()
            self.ping_status_timer.start()
    
    def ping_current_ip(self):
        """Ping the currently selected IP (used for immediate pings)"""
        ip = self.ip_input.currentText()
        if not ip:
            return
        
        # Validate IP before using in command
        if not SecurityValidator.validate_ip_or_hostname(ip):
            return
        
        # Update status to pinging
        self.update_ping_status("pinging")
            
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            self.append_verbose_message(f"$ ping -c 1 -W 5 {ip}\n{output}\n")
            
            if result.returncode == 0:
                # Extract latency from ping output
                latency = self.extract_ping_latency(result.stdout)
                if latency:
                    self.append_simple_message(f"✅ Ping to {ip} successful ({latency}ms)")
                    self.update_ping_status("success", latency, ip)
                else:
                    self.append_simple_message(f"✅ Ping to {ip} successful")
                    self.update_ping_status("success", None, ip)
            else:
                self.append_simple_message(f"❌ Ping to {ip} failed")
                self.update_ping_status("failed")
        except subprocess.TimeoutExpired:
            self.append_simple_message(f"⏱️ Ping to {ip} timed out")
            self.append_verbose_message(f"Ping to {ip} timed out.\n")
            self.update_ping_status("timeout")
        except Exception as e:
            self.append_simple_message(f"❌ Error pinging {ip}: Connection failed")
            self.update_ping_status("failed")
            self.append_verbose_message(f"Error pinging {ip}: {str(e)}\n")

    def test_ping_colors(self):
        """Test different ping latency colors by cycling through simulated values"""
        ip = self.ip_input.currentText()
        if not ip:
            ip = "demo.example.com"
        
        # Initialize or get current test state
        if not hasattr(self, '_color_test_state'):
            self._color_test_state = 0
        
        test_scenarios = [
            # (latency, description, status)
            ("15.2", "Excellent - Perfect for gaming", "success"),
            ("75.8", "Good - Great for most games", "success"), 
            ("125.4", "Fair - OK for casual gaming", "success"),
            ("220.7", "High - Poor for gaming", "success"),
            ("450.3", "Very High - Unplayable", "success"),
            (None, "Failed - No connection", "failed"),
            (None, "Timeout - Connection timeout", "timeout"),
            (None, "Checking - Testing connection", "pinging"),
            (None, "Unknown - No status", "unknown")
        ]
        
        scenario = test_scenarios[self._color_test_state]
        latency, description, status = scenario
        
        # Update ping status with test scenario
        self.update_ping_status(status, latency, ip)
        
        # Show message in console
        if latency:
            self.append_simple_message(f"🎨 Test: {description} ({latency}ms)")
        else:
            self.append_simple_message(f"🎨 Test: {description}")
        
        # Advance to next test state
        self._color_test_state = (self._color_test_state + 1) % len(test_scenarios)
        
        # Show helpful info about current colors
        if self._color_test_state == 0:
            self.append_simple_message("🔄 Color test cycle complete! Click 'Test Colors' again to repeat.")

    def apply_debug_mode(self):
        """Apply debug mode settings - show/hide debug tools"""
        # Show/hide test colors button based on debug mode
        self.test_colors_button.setVisible(self.debug_mode)
        
        # Future debug tools can be added here
        # Example: self.debug_panel.setVisible(self.debug_mode)

    def auto_ping_status(self):
        """Automatically ping the current IP to update status (silent mode)"""
        ip = self.ip_input.currentText()
        if not ip or not SecurityValidator.validate_ip_or_hostname(ip):
            return
            
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", ip],  # Shorter timeout for auto-ping
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5  # Shorter process timeout
            )
            
            if result.returncode == 0:
                # Extract latency from ping output
                latency = self.extract_ping_latency(result.stdout)
                self.update_ping_status("success", latency, ip)
            else:
                self.update_ping_status("failed")
        except (subprocess.TimeoutExpired, Exception):
            self.update_ping_status("timeout")

    def load_devices(self):
        """Load and display USB/IP devices from remote server (delegate to controller)"""
        self.device_management_controller.load_devices()

    def detach_local_device(self, port, desc, state):
        """Detach a local device by port (delegate to controller)"""
        self.device_management_controller.detach_local_device(port, desc, state)

    def toggle_attach(self, ip, busid, desc, state, start_grace_period=True):
        """Toggle device attach/detach (delegate to device controller)"""
        return self.device_management_controller.toggle_attach(ip, busid, desc, state, start_grace_period)

    def parse_usbip_list(self, output):
        """Parse usbip list output to extract device information (delegate to controller)"""
        return self.device_management_controller.parse_usbip_list(output)

    def auto_refresh_devices(self):
        """Auto-refresh device tables (delegate to controller)"""
        self.device_management_controller.auto_refresh_devices()

    def _get_sudo_password(self):
        """Get the deobfuscated sudo password"""
        if not self._obfuscated_sudo_password:
            return ""
        return self.memory_crypto.deobfuscate_string(self._obfuscated_sudo_password)

    def load_ips(self):
        """Load IP addresses (delegate to data persistence controller)"""
        self.data_persistence_controller.load_ips()

    def save_ips(self):
        """Save IP addresses (delegate to data persistence controller)"""
        self.data_persistence_controller.save_ips()

    def show_ip_management(self):
        """Show the IP Management dialog"""
        # Get current IPs from the combo box
        current_ips = [self.ip_input.itemText(i) for i in range(self.ip_input.count())]
        current_selection = self.ip_input.currentText()
        
        # Show the IP management dialog
        dialog = IPManagementDialog(self, current_ips)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.has_changes():
                # Update the combo box with new IPs
                new_ips = dialog.get_ips()
                
                # Clear and repopulate the combo box
                self.ip_input.clear()
                for ip in new_ips:
                    self.ip_input.addItem(ip)
                
                # Try to restore the previous selection, or select first item
                if current_selection in new_ips:
                    index = self.ip_input.findText(current_selection)
                    if index >= 0:
                        self.ip_input.setCurrentIndex(index)
                elif new_ips:
                    self.ip_input.setCurrentIndex(0)
                
                # Save the updated IPs
                self.save_ips()
                
                # Clear device table since IP list changed
                self.device_table.setRowCount(0)
                
                # Show success message
                self.append_simple_message("✅ IP addresses updated successfully")

    def extract_ping_latency(self, ping_output):
        """Extract latency value from ping output"""
        import re
        # Look for patterns like "time=8.90 ms" or "time=8.9 ms"
        match = re.search(r'time=(\d+\.?\d*)\s*ms', ping_output)
        if match:
            try:
                latency = float(match.group(1))
                # Format to one decimal place for consistency
                return f"{latency:.1f}"
            except ValueError:
                return None
        return None

    def update_ping_status(self, status, latency=None, ip=None):
        """Update the ping status indicator with latency-based color coding"""
        if status == "success":
            if latency:
                latency_float = float(latency)
                # Gaming-focused latency thresholds
                if latency_float <= 50:  # Excellent for gaming
                    color = "#00ff00"  # Green
                    status_text = "Excellent"
                elif latency_float <= 100:  # Good for most gaming
                    color = "#7fff00"  # Light green
                    status_text = "Good"
                elif latency_float <= 150:  # Acceptable for casual gaming
                    color = "#ffff00"  # Yellow
                    status_text = "Fair"
                elif latency_float <= 300:  # High latency - poor for gaming
                    color = "#ffaa00"  # Orange
                    status_text = "High"
                else:  # Very high latency - unplayable
                    color = "#ff4444"  # Red
                    status_text = "Very High"
                
                self.ping_status_indicator.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
                self.ping_status_label.setText(f"{status_text} ({latency}ms)")
                self.ping_status_label.setStyleSheet(f"color: {color}; font-size: 12px;")
            else:
                # No latency info - default green
                self.ping_status_indicator.setStyleSheet("color: #00ff00; font-size: 14px; font-weight: bold;")
                self.ping_status_label.setText("Online")
                self.ping_status_label.setStyleSheet("color: #00ff00; font-size: 12px;")
        elif status == "failed":
            self.ping_status_indicator.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
            self.ping_status_label.setText("Offline")
            self.ping_status_label.setStyleSheet("color: #ff4444; font-size: 12px;")
        elif status == "timeout":
            self.ping_status_indicator.setStyleSheet("color: #ff4444; font-size: 14px; font-weight: bold;")
            self.ping_status_label.setText("Timeout")
            self.ping_status_label.setStyleSheet("color: #ff4444; font-size: 12px;")
        elif status == "pinging":
            self.ping_status_indicator.setStyleSheet("color: #0099ff; font-size: 14px; font-weight: bold;")
            self.ping_status_label.setText("Checking...")
            self.ping_status_label.setStyleSheet("color: #0099ff; font-size: 12px;")
        else:  # unknown
            self.ping_status_indicator.setStyleSheet("color: gray; font-size: 14px; font-weight: bold;")
            self.ping_status_label.setText("Unknown")
            self.ping_status_label.setStyleSheet("color: gray; font-size: 12px;")

    def ping_ip(self):
        ip = self.ip_input.currentText()
        if not ip:
            self.show_error("No IP/hostname selected.")
            return
        
        # Validate IP before using in command
        if not SecurityValidator.validate_ip_or_hostname(ip):
            self.show_error("Invalid IP/hostname format.")
            return
        
        # Update status to pinging
        self.update_ping_status("pinging")
            
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", ip],  # Added timeout
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10  # Process timeout
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            self.append_verbose_message(f"$ ping -c 1 -W 5 {ip}\n{output}\n")
            
            if result.returncode == 0:
                # Extract latency from ping output
                latency = self.extract_ping_latency(result.stdout)
                if latency:
                    self.append_simple_message(f"✅ Ping to {ip} successful ({latency}ms)")
                    self.update_ping_status("success", latency, ip)
                else:
                    self.append_simple_message(f"✅ Ping to {ip} successful")
                    self.update_ping_status("success", None, ip)
            else:
                self.append_simple_message(f"❌ Ping to {ip} failed")
                self.update_ping_status("failed")
        except subprocess.TimeoutExpired:
            self.append_simple_message(f"⏱️ Ping to {ip} timed out")
            self.append_verbose_message(f"Ping to {ip} timed out.\n")
            self.update_ping_status("timeout")
        except Exception as e:
            self.append_simple_message(f"❌ Error pinging {ip}: Connection failed")
            self.update_ping_status("failed")
            self.append_verbose_message(f"Error pinging {ip}: {str(e)}\n")

    def _get_sudo_password(self):
        """Get the deobfuscated sudo password"""
        if not self._obfuscated_sudo_password:
            return ""
        return self.memory_crypto.deobfuscate_string(self._obfuscated_sudo_password)

    def filter_sudo_prompts(self, output):
        """Filter out sudo password prompts from output"""
        if not output:
            return ""
        lines = [line for line in output.splitlines() 
                if not line.strip().startswith('[sudo] password for')]
        return '\n'.join(lines).strip()

    def run_sudo(self, cmd):
        sudo_password = self._get_sudo_password()
        if not sudo_password:
            self.append_simple_message("❌ No sudo password set")
            return None
        try:
            proc = subprocess.run(
                ['sudo', '-S'] + cmd,
                input=sudo_password + '\n',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            # Clear password from local scope
            sudo_password = "0" * len(sudo_password)
            
            # Only show output if there's actual content, and filter out sudo password prompts
            stdout_filtered = self.filter_sudo_prompts(proc.stdout)
            stderr_filtered = self.filter_sudo_prompts(proc.stderr)
            
            if stdout_filtered:
                self.append_verbose_message(f"{stdout_filtered}\n")
            if stderr_filtered:
                self.append_verbose_message(f"{stderr_filtered}\n")
            return proc
        except Exception as e:
            self.console.append(f"Exception running sudo: {e}\n")
            return None

    def load_state(self, ip):
        return self.data_persistence_controller.load_state(ip)

    def save_state(self, ip, busid, attached):
        self.data_persistence_controller.save_state(ip, busid, attached)

    def load_remote_state(self, ip):
        """Load remote device bind states for a specific IP"""
        return self.data_persistence_controller.load_remote_state(ip)

    def save_remote_state(self, ip, busid, bound):
        """Save remote device bind state for a specific IP and busid"""
        self.data_persistence_controller.save_remote_state(ip, busid, bound)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def clear_console(self):
        """Clear the console output and stored messages"""
        self.console.clear()
        self.console_messages.clear()
        self.simple_messages.clear()
        self.console.append("Console cleared.\n")

    def append_simple_message(self, message):
        """Add a simple message that's always shown"""
        self.simple_messages.append(message)
        self.console_messages.append(('simple', message))
        self.console.append(message)  # Simple messages always show

    def append_verbose_message(self, message):
        """Add a verbose message that's only shown in verbose mode"""
        self.console_messages.append(('verbose', message))
        if self.verbose_console:
            self.console.append(message)

    def toggle_verbose_console(self, enabled):
        """Toggle between simple and verbose console modes"""
        self.verbose_console = enabled
        
        # Clear and rebuild console based on mode
        self.console.clear()
        
        if enabled:
            # Show all messages (simple and verbose)
            for msg_type, message in self.console_messages:
                self.console.append(message)
        else:
            # Show only simple messages
            for message in self.simple_messages:
                self.console.append(message)

    # Auto-reconnect functionality
    def load_auto_reconnect_settings(self):
        """Load auto-reconnect and auto-refresh settings from encrypted file"""
        return self.data_persistence_controller.load_auto_reconnect_settings()

    def save_auto_reconnect_settings(self):
        """Save auto-reconnect and auto-refresh settings to encrypted file"""
        self.data_persistence_controller.save_auto_reconnect_settings()

    def apply_theme(self):
        """Apply the selected theme to the application"""
        self.theme_manager.set_theme(self.theme_setting)
        stylesheet = self.theme_manager.get_stylesheet(self.theme_setting)
        self.setStyleSheet(stylesheet)

    def get_theme_colors(self):
        """Get theme-appropriate colors for dialogs"""
        return self.theme_manager.get_dialog_colors(self.theme_setting, self.palette())

    def get_auto_reconnect_state(self, ip, busid, table_type="local"):
        """Get auto-reconnect state for a specific device with table type separation"""
        return self.data_persistence_controller.get_auto_reconnect_state(ip, busid, table_type)

    def toggle_auto_reconnect(self, ip, busid, enabled, table_type="local"):
        """Toggle auto-reconnect for a specific device with table type separation"""
        self.data_persistence_controller.toggle_auto_reconnect(ip, busid, enabled, table_type)

    def save_device_mapping(self, remote_busid, remote_desc, port_number, port_busid):
        """Save mapping between remote device and attached port"""
        self.data_persistence_controller.save_device_mapping(remote_busid, remote_desc, port_number, port_busid)

    def get_device_mapping(self, remote_busid):
        """Get port mapping for a remote device"""
        return self.data_persistence_controller.get_device_mapping(remote_busid)

    def remove_device_mapping(self, remote_busid):
        """Remove mapping when device is detached"""
        self.data_persistence_controller.remove_device_mapping(remote_busid)

    def get_remote_busid_for_port(self, port_busid):
        """Get the original remote busid for a port busid"""
        return self.data_persistence_controller.get_remote_busid_for_port(port_busid)

    def start_grace_period(self, duration_seconds=None):
        """Start grace period to pause auto-reconnect after manual bulk operations"""
        if duration_seconds is None:
            duration_seconds = self.grace_period_duration
        
        self.auto_reconnect_grace_period = True
        self.grace_period_timer.start(duration_seconds * 1000)  # Convert to milliseconds
        self.append_simple_message(f"⏸️ Auto-reconnect paused for {duration_seconds} seconds after manual operation")

    def end_grace_period(self):
        """End the grace period and resume auto-reconnect"""
        self.auto_reconnect_grace_period = False
        if self.auto_reconnect_enabled:
            self.append_simple_message("▶️ Auto-reconnect resumed after grace period")

    def show_auto_reconnect_settings(self):
        """Show settings dialog for auto-reconnect, auto-refresh, and theme configuration"""
        current_settings = {
            'auto_reconnect_enabled': self.auto_reconnect_enabled,
            'auto_reconnect_interval': self.auto_reconnect_interval,
            'auto_reconnect_max_attempts': self.auto_reconnect_max_attempts,
            'grace_period_duration': self.grace_period_duration,
            'auto_refresh_enabled': self.auto_refresh_enabled,
            'auto_refresh_interval': self.auto_refresh_interval,
            'theme_setting': self.theme_setting,
            'verbose_console': getattr(self, 'verbose_console', False),
            'debug_mode': getattr(self, 'debug_mode', False),
        }
        
        colors = self.get_theme_colors()
        dialog = SettingsDialog(self, current_settings, colors)
        dialog.exec()

    def show_about_dialog(self):
        """Show application about dialog"""
        colors = self.get_theme_colors()
        dialog = AboutDialog(self, colors)
        dialog.exec()

    def show_help_dialog(self):
        """Show help dialog with quick start instructions"""
        colors = self.get_theme_colors()
        auto_reconnect_status = {
            'enabled': self.auto_reconnect_enabled,
            'interval': self.auto_reconnect_interval
        }
        auto_refresh_status = {
            'enabled': self.auto_refresh_enabled,
            'interval': self.auto_refresh_interval
        }
        dialog = HelpDialog(self, colors, auto_reconnect_status, auto_refresh_status)
        dialog.exec()

    def check_auto_reconnect(self):
        """Check for devices that need auto-reconnection (delegate to controller)"""
        self.auto_reconnect_controller.check_auto_reconnect()

    def should_auto_reconnect_device(self, ip, busid):
        """Check if a device should be auto-reconnected (delegate to controller)"""
        return self.auto_reconnect_controller.should_auto_reconnect_device(ip, busid)

    def should_auto_bind_device(self, ip, busid):
        """Check if a remote device should be auto-bound (delegate to controller)"""
        return self.auto_reconnect_controller.should_auto_bind_device(ip, busid)

    def attempt_auto_reconnect(self, ip, busid, device_key):
        """Attempt to auto-reconnect a device (delegate to controller)"""
        self.auto_reconnect_controller.attempt_auto_reconnect(ip, busid, device_key)

    def attempt_auto_bind(self, ip, busid, device_key):
        """Attempt to auto-bind a remote device (delegate to controller)"""
        self.auto_reconnect_controller.attempt_auto_bind(ip, busid, device_key)

    def update_device_toggle_state(self, busid, attached):
        """Update the toggle button state for a device (delegate to controller)"""
        self.auto_reconnect_controller.update_device_toggle_state(busid, attached)

    def update_remote_toggle_state(self, busid, bound):
        """Update the toggle button state for a remote device (delegate to controller)"""
        self.auto_reconnect_controller.update_remote_toggle_state(busid, bound)

    def update_auto_toggle_state(self, busid, enabled):
        """Update the auto-reconnect toggle button state for a device (delegate to controller)"""
        self.auto_reconnect_controller.update_auto_toggle_state(busid, enabled)

    def update_remote_auto_toggle_state(self, busid, enabled):
        """Update the auto-reconnect toggle button state for a remote device (delegate to controller)"""
        self.auto_reconnect_controller.update_remote_auto_toggle_state(busid, enabled)

    def perform_remote_bind(self, ip, username, password, busid, accept_fingerprint, bind=True):
        """Perform remote bind/unbind operation (delegate to SSH controller)"""
        return self.ssh_management_controller.perform_remote_bind(ip, username, password, busid, accept_fingerprint, bind)

    def refresh_local_devices_silently(self):
        """Refresh local device table without disrupting auto-reconnect states"""
        ip = self.ip_input.currentText()
        if not ip:
            return
            
        # Note: Auto-reconnect states are always read from encrypted file, not saved UI state
        # This ensures proper persistence and prevents states from becoming N/A
        
        # Temporarily disable sorting during refresh
        self.device_table.setSortingEnabled(False)
        
        try:
            # Get current attached devices
            port_result = subprocess.run(
                ["usbip", "port"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            port_output = port_result.stdout
            attached_descs = set()
            current_port = None
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                elif current_port and line and ":" in line:
                    desc = line
                    attached_descs.add(desc)

            # Get remote devices
            result = subprocess.run(
                ["usbip", "list", "-r", ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            devices = self.device_management_controller.parse_usbip_list(output)

            # Clear and repopulate table
            self.device_table.setRowCount(0)
            
            # Add remote devices
            for dev in devices:
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                self.device_table.setItem(row, 0, self.create_table_item_with_tooltip(dev["busid"]))
                self.device_table.setItem(row, 1, self.create_table_item_with_tooltip(dev["desc"]))
                
                # Create toggle button
                toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                toggle_btn.setChecked(dev["desc"] in attached_descs)
                toggle_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"], desc=dev["desc"]: self.device_management_controller.toggle_attach(ip, busid, desc, 2 if state else 0)
                )
                self.device_table.setCellWidget(row, 2, toggle_btn)
                
                # Create auto-reconnect toggle and restore state
                auto_btn = ToggleButton("AUTO", "MANUAL")
                # Always read from encrypted file for consistent state
                auto_btn.setChecked(self.get_auto_reconnect_state(ip, dev["busid"], "local"))
                auto_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"]: self.toggle_auto_reconnect(ip, busid, state, "local")
                )
                self.device_table.setCellWidget(row, 3, auto_btn)

            # Add locally attached devices that aren't in remote list
            table_descs = set()
            for row in range(self.device_table.rowCount()):
                desc_item = self.device_table.item(row, 1)
                if desc_item:
                    table_descs.add(desc_item.text())
            
            current_port = None
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                elif current_port and line and ":" in line:
                    desc = line
                    if desc not in table_descs:
                        row = self.device_table.rowCount()
                        self.device_table.insertRow(row)
                        self.device_table.setItem(row, 0, self.create_table_item_with_tooltip(f"Port {current_port}"))
                        self.device_table.setItem(row, 1, self.create_table_item_with_tooltip(desc))
                        
                        # Create toggle button for local devices
                        toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                        toggle_btn.setChecked(True)  # Local devices are already attached
                        toggle_btn.toggled.connect(
                            lambda state, port=current_port, desc=desc: self.device_management_controller.detach_local_device(port, desc, 0 if not state else 2)
                        )
                        self.device_table.setCellWidget(row, 2, toggle_btn)
                        
                        # Create disabled auto-reconnect toggle for local devices
                        auto_btn = ToggleButton("N/A", "N/A")
                        auto_btn.setEnabled(False)
                        auto_btn.setStyleSheet("QPushButton { background-color: #ccc; color: #666; }")
                        self.device_table.setCellWidget(row, 3, auto_btn)
                        
        except Exception as e:
            # Silently handle errors during auto-refresh
            pass
        finally:
            # Re-enable sorting
            self.device_table.setSortingEnabled(True)

    def closeEvent(self, event):
        # Stop auto-reconnect timer
        if hasattr(self, 'auto_reconnect_timer'):
            self.auto_reconnect_timer.stop()
        
        # Stop auto-refresh timer
        if hasattr(self, 'auto_refresh_timer'):
            self.auto_refresh_timer.stop()
        
        # Stop grace period timer
        if hasattr(self, 'grace_period_timer'):
            self.grace_period_timer.stop()
            
        # Securely clear sensitive data from memory
        if hasattr(self, '_obfuscated_sudo_password'):
            self.memory_crypto.secure_zero_memory(self._obfuscated_sudo_password)
            self._obfuscated_sudo_password = ""
        if hasattr(self, 'last_ssh_password'):
            self.memory_crypto.secure_zero_memory(self.last_ssh_password)
            self.last_ssh_password = ""
        if hasattr(self, 'last_ssh_username'):
            self.last_ssh_username = ""
        
        # Close SSH connection if active
        if hasattr(self, 'ssh_client') and self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
            self.ssh_client = None
        
        # Only save IPs if the UI was fully initialized
        if hasattr(self, 'ip_input'):
            self.save_ips()
        event.accept()

    def prompt_ssh_credentials(self):
        """Prompt for SSH credentials (delegate to SSH controller)"""
        self.ssh_management_controller.prompt_ssh_credentials()

    def load_remote_local_devices(self, username, password, accept_fingerprint):
        """Load remote devices via SSH (delegate to SSH controller)"""
        self.ssh_management_controller.load_remote_local_devices(username, password, accept_fingerprint)

    def toggle_bind_remote(self, ip, username, password, busid, desc, accept_fingerprint, state):
        """Toggle remote device binding (delegate to SSH controller)"""
        self.ssh_management_controller.toggle_bind_remote(ip, username, password, busid, desc, accept_fingerprint, state)

    def parse_ssh_usbip_list(self, output):
        """Parse SSH usbip list output (delegate to SSH controller)"""
        return self.ssh_management_controller.parse_ssh_usbip_list(output)

    def save_remote_device_states(self):
        """Save the current state of remote device toggle buttons (delegate to SSH controller)"""
        return self.ssh_management_controller.save_remote_device_states()
    
    def restore_remote_device_states(self, saved_states):
        """Restore the state of remote device toggle buttons (delegate to SSH controller)"""
        self.ssh_management_controller.restore_remote_device_states(saved_states)

    def refresh_all_tables(self):
        self.device_management_controller.load_devices()
        # Refresh SSH devices with saved credentials if available
        self.ssh_management_controller.refresh_with_saved_credentials()

    def load_ssh_state(self):
        """Load SSH state (delegate to SSH controller)"""
        return self.ssh_management_controller.load_ssh_state()

    def save_ssh_state(self, ip, username, accept_fingerprint):
        """Save SSH state (delegate to SSH controller)"""
        self.ssh_management_controller.save_ssh_state(ip, username, accept_fingerprint)

    def disconnect_ssh(self):
        """Disconnect SSH (delegate to SSH controller)"""
        self.ssh_management_controller.disconnect_ssh()

    def reset_usbipd(self):
        ip = self.ip_input.currentText()
        username = getattr(self, "last_ssh_username", "")
        password = getattr(self, "last_ssh_password", "")
        accept = getattr(self, "last_ssh_accept", False)
        if not ip or not username or not password:
            self.append_simple_message("❌ Missing SSH credentials for IPD Reset")
            return
        try:
            client = paramiko.SSHClient()
            if accept:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)
            
            # Restart usbipd using secure command builder
            actual_cmd = SecureCommandBuilder.build_systemctl_command("restart", "usbipd", password)
            if not actual_cmd:
                self.console.append("Failed to build secure restart command.\n")
                client.close()
                return
                
            safe_cmd = "echo [HIDDEN] | sudo -S systemctl restart usbipd"
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.append_verbose_message(f"SSH $ {safe_cmd}\n")
            if output:
                self.append_verbose_message(f"{SecurityValidator.sanitize_console_output(output)}\n")
                
            # Show status after restart
            actual_status_cmd = SecureCommandBuilder.build_systemctl_command("status", "usbipd", password)
            if actual_status_cmd:
                safe_status_cmd = "echo [HIDDEN] | sudo -S systemctl status usbipd"
                stdin, stdout, stderr = client.exec_command(actual_status_cmd)
                status_output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
                self.append_verbose_message(f"SSH $ {safe_status_cmd}\n")
                if status_output:
                    self.append_verbose_message(f"{SecurityValidator.sanitize_console_output(status_output)}\n")
            client.close()
        except Exception as e:
            self.console.append(f"Error restarting usbipd: Connection or authentication failed\n")