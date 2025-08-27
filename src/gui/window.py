import json
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox, QInputDialog, QTextEdit, QCheckBox, QLineEdit,
                             QSplitter, QHeaderView, QSpinBox, QGroupBox, QFormLayout,
                             QScrollArea, QDialogButtonBox)
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
from gui.controllers.auto_reconnect_controller import AutoReconnectController

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

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.ip_input = QComboBox()
        self.layout.addWidget(QLabel("IP Address/Hostname:"))
        self.layout.addWidget(self.ip_input)
        self.ip_input.currentIndexChanged.connect(self.load_devices)

        btn_layout = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self.add_ip)
        btn_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_ip)
        btn_layout.addWidget(self.remove_button)

        self.ping_button = QPushButton("Ping")
        self.ping_button.clicked.connect(self.ping_ip)
        btn_layout.addWidget(self.ping_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_all_tables)
        btn_layout.addWidget(self.refresh_button)

        self.ssh_button = QPushButton("SSH Devices")
        self.ssh_button.clicked.connect(self.prompt_ssh_credentials)
        btn_layout.addWidget(self.ssh_button)

        self.ssh_disco_button = QPushButton("SSH Disco")
        self.ssh_disco_button.clicked.connect(self.disconnect_ssh)
        self.ssh_disco_button.setVisible(False)
        btn_layout.addWidget(self.ssh_disco_button)

        self.ipd_reset_button = QPushButton("IPD Reset")
        self.ipd_reset_button.clicked.connect(self.reset_usbipd)
        self.ipd_reset_button.setVisible(False)
        btn_layout.addWidget(self.ipd_reset_button)

        # Auto-reconnect controls
        self.auto_reconnect_enabled = True
        self.auto_reconnect_grace_period = False  # Flag to pause auto-reconnect temporarily

        # Auto-reconnect settings button
        self.auto_settings_button = QPushButton("Settings")
        self.auto_settings_button.clicked.connect(self.show_auto_reconnect_settings)
        btn_layout.addWidget(self.auto_settings_button)

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
        self.load_devices()
        
        # Initialize auto-reconnect system
        self.auto_reconnect_interval = 30  # seconds
        self.auto_reconnect_max_attempts = 5
        self.grace_period_duration = 60  # seconds
        self.auto_reconnect_attempts = {}  # Track attempts per device
        
        # Initialize auto-refresh system
        self.auto_refresh_enabled = False
        self.auto_refresh_interval = 60  # seconds
        
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
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_devices)
        
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
        self.show_welcome_instructions()

    def show_welcome_instructions(self):
        """Show helpful instructions in the console on startup"""
        self.console.append("🚀 Welcome to USBIP GUI Application!")
        self.console.append("")
        self.console.append("Quick Start Instructions:")
        self.console.append("• Add an IP / Hostname")
        self.console.append("• Use SSH Devices to start connection")
        self.console.append("• IPD Reset refreshes the USBIP Daemon on the remote if needed")
        self.console.append("")
        self.console.append("✨ NEW: Auto-Reconnect & Auto-Refresh Features")
        self.console.append(f"• Auto-reconnect {'enabled' if self.auto_reconnect_enabled else 'disabled'} every {self.auto_reconnect_interval} seconds")
        self.console.append("• Use 'Auto' column to enable per-device auto-reconnect")
        self.console.append("• Works for both ATTACH (local) and BIND (remote) operations")
        self.console.append("• Use 'Settings' to customize timing and enable/disable features")
        self.console.append("")
        self.console.append("Ready for device management!")
        self.console.append("=" * 50)
        self.console.append("")

    def create_table_item_with_tooltip(self, text):
        """Create a QTableWidgetItem with tooltip for long text"""
        item = QTableWidgetItem(text)
        item.setToolTip(text)  # Set full text as tooltip
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make non-editable
        return item

    def attach_all_devices(self):
        ip = self.ip_input.currentText()
        if not ip:
            self.console.append("No IP selected for Attach All.\n")
            return
        
        attached_count = 0
        failed_count = 0
        for row in range(self.device_table.rowCount()):
            toggle_btn = self.device_table.cellWidget(row, 2)
            busid_item = self.device_table.item(row, 0)
            desc_item = self.device_table.item(row, 1)
            if toggle_btn and not toggle_btn.isChecked() and busid_item and desc_item:
                # Only attach if not checked
                busid = busid_item.text()
                desc = desc_item.text()
                # Actually perform the attachment
                success = self.toggle_attach(ip, busid, desc, 2)  # 2 = checked/attached state
                if success:
                    attached_count += 1
                else:
                    failed_count += 1
        
        # Provide detailed feedback
        if attached_count > 0:
            self.console.append(f"Successfully attached {attached_count} devices.")
        if failed_count > 0:
            self.console.append(f"Failed to attach {failed_count} devices.")
        if attached_count > 0:
            self.console.append("Refreshing device list...\n")
            # Add a small delay to allow usbip commands to complete
            import time
            time.sleep(0.5)
        
        # Refresh the device table to show updated states
        self.load_devices()
        
        # Start grace period to prevent immediate auto-reconnect after attach all
        if attached_count > 0:
            self.start_grace_period()  # Use default grace period duration

    def detach_all_devices(self):
        detached_count = 0
        failed_count = 0
        for row in range(self.device_table.rowCount()):
            toggle_btn = self.device_table.cellWidget(row, 2)
            busid_item = self.device_table.item(row, 0)
            desc_item = self.device_table.item(row, 1)
            if toggle_btn and toggle_btn.isChecked() and busid_item and desc_item:
                # Only detach if checked
                busid = busid_item.text()
                desc = desc_item.text()
                # Actually perform the detachment
                success = self.toggle_attach("", busid, desc, 0)  # 0 = unchecked/detached state
                if success:
                    detached_count += 1
                else:
                    failed_count += 1
        
        # Provide detailed feedback
        if detached_count > 0:
            self.console.append(f"Successfully detached {detached_count} devices.")
        if failed_count > 0:
            self.console.append(f"Failed to detach {failed_count} devices.")
        if detached_count > 0:
            self.console.append("Refreshing device list...\n")
            # Add a small delay to allow usbip commands to complete
            import time
            time.sleep(0.5)
        
        # Refresh the device table to show updated states
        self.load_devices()
        
        # Start grace period to prevent immediate auto-reconnect
        if detached_count > 0:
            self.start_grace_period()  # Use default grace period duration

    def unbind_all_devices(self):
        """Unbind all bound devices on the remote SSH server and refresh tables"""
        ip = self.ip_input.currentText()
        username = getattr(self, "last_ssh_username", "")
        password = getattr(self, "last_ssh_password", "")
        accept = getattr(self, "last_ssh_accept", False)
        
        if not ip or not username or not password:
            self.console.append("Missing SSH credentials for Unbind All.\n")
            return
        
        # Check rate limiting
        allowed, remaining_time = self.connection_security.check_ssh_connection_allowed(ip)
        if not allowed:
            self.console.append(f"Too many SSH attempts. Try again in {remaining_time} seconds.\n")
            return
            
        try:
            import paramiko
            self.connection_security.record_ssh_attempt(ip)
            client = paramiko.SSHClient()
            if accept:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=10)
            
            # Unbind all bound devices
            for row in range(self.remote_table.rowCount()):
                toggle_btn = self.remote_table.cellWidget(row, 2)
                busid_item = self.remote_table.item(row, 0)
                if toggle_btn and toggle_btn.isChecked() and busid_item:
                    busid = busid_item.text()
                    
                    # Validate busid format for security
                    if not SecurityValidator.validate_busid(busid):
                        self.console.append(f"Invalid busid format: {busid}\n")
                        continue
                    
                    # Use secure command builder
                    actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(busid, password)
                    if not actual_cmd:
                        self.console.append(f"Failed to build secure command for busid: {busid}\n")
                        continue
                    
                    safe_cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {SecurityValidator.sanitize_for_shell(busid)}"
                    stdin, stdout, stderr = client.exec_command(actual_cmd)
                    output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
                    self.console.append(f"SSH $ {safe_cmd}\n")
                    if output:
                        self.console.append(f"{SecurityValidator.sanitize_console_output(output)}\n")
            
            client.close()
            self.console.append("All devices unbound successfully.\n")
            
            # Update toggle buttons instead of refreshing entire table
            for row in range(self.remote_table.rowCount()):
                toggle_btn = self.remote_table.cellWidget(row, 2)
                if toggle_btn and toggle_btn.isChecked():
                    toggle_btn.setChecked(False)  # Set to unbound state
            
            # Refresh only the local devices table to show available devices
            self.load_devices()
            
            # Start grace period to prevent immediate auto-reconnect
            self.start_grace_period()  # Use default grace period duration
            
        except Exception as e:
            self.console.append(f"Error unbinding all devices: {e}\n")

    def _get_sudo_password(self):
        """Get the deobfuscated sudo password"""
        if not self._obfuscated_sudo_password:
            return ""
        return self.memory_crypto.deobfuscate_string(self._obfuscated_sudo_password)

    def load_ips(self):
        data = self.file_crypto.load_encrypted_file(IPS_FILE)
        ips = data.get('ips', [])
        for ip in ips:
            self.ip_input.addItem(ip)

    def save_ips(self):
        ips = [self.ip_input.itemText(i) for i in range(self.ip_input.count())]
        data = {'ips': ips}
        self.file_crypto.save_encrypted_file(IPS_FILE, data)

    def add_ip(self):
        text, ok = QInputDialog.getText(self, "Add IP/Hostname", "Enter IP address or hostname:")
        if ok and text:
            # Validate the IP/hostname format
            if not SecurityValidator.validate_ip_or_hostname(text):
                self.show_error("Invalid IP address or hostname format.")
                return
            
            # Check for duplicates
            existing_ips = [self.ip_input.itemText(i) for i in range(self.ip_input.count())]
            if text not in existing_ips:
                self.ip_input.addItem(text)
                self.save_ips()
            else:
                self.show_error("IP/hostname already exists in the list.")

    def remove_ip(self):
        current_index = self.ip_input.currentIndex()
        if current_index >= 0:
            self.ip_input.removeItem(current_index)
            self.save_ips()
            self.device_table.setRowCount(0)

    def ping_ip(self):
        ip = self.ip_input.currentText()
        if not ip:
            self.show_error("No IP/hostname selected.")
            return
        
        # Validate IP before using in command
        if not SecurityValidator.validate_ip_or_hostname(ip):
            self.show_error("Invalid IP/hostname format.")
            return
            
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", ip],  # Added timeout
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10  # Process timeout
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            self.console.append(f"$ ping -c 1 -W 5 {ip}\n{output}\n")
        except subprocess.TimeoutExpired:
            self.console.append(f"Ping to {ip} timed out.\n")
        except Exception as e:
            self.console.append(f"Error pinging {ip}: Connection failed\n")

    def load_devices(self):
        # Save auto-reconnect states before clearing the table
        saved_auto_states = {}
        ip = self.ip_input.currentText()
        if ip:
            for row in range(self.device_table.rowCount()):
                busid_item = self.device_table.item(row, 0)
                auto_btn = self.device_table.cellWidget(row, 3)
                if busid_item and auto_btn and hasattr(auto_btn, 'isChecked'):
                    busid = busid_item.text()
                    # Only save if it's not a "Port" entry and has a real auto state
                    if not busid.startswith("Port") and auto_btn.isEnabled():
                        auto_state = auto_btn.isChecked()
                        saved_auto_states[busid] = auto_state
        
        # Disable sorting during table population to prevent widget issues
        self.device_table.setSortingEnabled(False)
        
        self.device_table.setRowCount(0)
        ip = self.ip_input.currentText()
        if not ip:
            # Re-enable sorting before returning
            self.device_table.setSortingEnabled(True)
            return
        try:
            # Get list of attached busids from usbip port
            port_result = subprocess.run(
                ["usbip", "port"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            port_output = port_result.stdout
            attached_busids = set()
            attached_descs = set()  # Build attached descriptions from port output
            current_port = None
            current_busid = None  # Track the busid for the current port
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                    current_busid = None  # Reset busid for new port
                elif current_port and line and line[0].isdigit() and '-' in line:
                    current_busid = line.split()[0]  # This is the busid line
                    attached_busids.add(current_busid)
                elif current_port and current_busid and line and ":" in line:
                    desc = line
                    attached_descs.add(desc)  # Capture attached device descriptions

            # List remote devices
            result = subprocess.run(
                ["usbip", "list", "-r", ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            self.console.append(f"$ usbip list -r {ip}\n{output}\n")
            devices = self.parse_usbip_list(output)

            # Add remote devices
            for dev in devices:
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                self.device_table.setItem(row, 0, self.create_table_item_with_tooltip(dev["busid"]))
                self.device_table.setItem(row, 1, self.create_table_item_with_tooltip(dev["desc"]))
                
                # Create toggle button instead of checkbox
                toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                toggle_btn.setChecked(dev["desc"] in attached_descs)
                toggle_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"], desc=dev["desc"]: self.toggle_attach(ip, busid, desc, 2 if state else 0)
                )
                self.device_table.setCellWidget(row, 2, toggle_btn)
                
                # Create auto-reconnect toggle button
                auto_btn = ToggleButton("AUTO", "MANUAL")
                # Use saved state if available, otherwise read from encrypted file
                if dev["busid"] in saved_auto_states:
                    auto_state = saved_auto_states[dev["busid"]]
                    auto_btn.setChecked(auto_state)
                else:
                    auto_state = self.get_auto_reconnect_state(ip, dev["busid"], "local")
                    auto_btn.setChecked(auto_state)
                auto_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"]: self.toggle_auto_reconnect(ip, busid, state, "local")
                )
                self.device_table.setCellWidget(row, 3, auto_btn)

            # Add devices that are attached but no longer in remote list (using mappings)
            data = self.file_crypto.load_encrypted_file(DEVICE_MAPPING_FILE)
            mappings = data.get('mappings', {})
            
            for remote_busid, mapping_info in mappings.items():
                port_busid = mapping_info.get('port_busid')
                
                # Check if this mapped device is currently attached
                if port_busid in attached_busids:
                    # This device is attached but not in remote list - add it
                    remote_desc = mapping_info.get('remote_desc', 'Unknown Device')
                    
                    # Check if we already added this device from the remote list
                    already_in_table = False
                    for row in range(self.device_table.rowCount()):
                        busid_item = self.device_table.item(row, 0)
                        if busid_item and busid_item.text() == remote_busid:
                            already_in_table = True
                            break
                    
                    if not already_in_table:
                        row = self.device_table.rowCount()
                        self.device_table.insertRow(row)
                        self.device_table.setItem(row, 0, self.create_table_item_with_tooltip(remote_busid))
                        self.device_table.setItem(row, 1, self.create_table_item_with_tooltip(remote_desc))
                        
                        # Create toggle button (attached state)
                        toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                        toggle_btn.setChecked(True)  # It's attached
                        toggle_btn.toggled.connect(
                            lambda state, ip=ip, busid=remote_busid, desc=remote_desc: self.toggle_attach(ip, busid, desc, 2 if state else 0)
                        )
                        self.device_table.setCellWidget(row, 2, toggle_btn)
                        
                        # Create auto-reconnect toggle button with preserved state
                        auto_btn = ToggleButton("AUTO", "MANUAL")
                        if remote_busid in saved_auto_states:
                            auto_state = saved_auto_states[remote_busid]
                            auto_btn.setChecked(auto_state)
                        else:
                            auto_state = self.get_auto_reconnect_state(ip, remote_busid, "local")
                            auto_btn.setChecked(auto_state)
                        auto_btn.toggled.connect(
                            lambda state, ip=ip, busid=remote_busid: self.toggle_auto_reconnect(ip, busid, state, "local")
                        )
                        self.device_table.setCellWidget(row, 3, auto_btn)

            # List locally attached devices (usbip port) that aren't in the remote list
            # Build set of descriptions and busids already added to the table
            table_descs = set()
            table_busids = set()
            for row in range(self.device_table.rowCount()):
                desc_item = self.device_table.item(row, 1)
                busid_item = self.device_table.item(row, 0)
                if desc_item:
                    table_descs.add(desc_item.text())
                if busid_item:
                    # Extract busid from items like "1-1.2" or "Port 00"
                    busid_text = busid_item.text()
                    if not busid_text.startswith("Port"):  # Only add actual busids
                        table_busids.add(busid_text)
            
            current_port = None
            current_busid = None
            port_to_busid = {}  # Map port to busid
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                    current_busid = None
                elif current_port and line and line[0].isdigit() and '-' in line:
                    current_busid = line.split()[0]
                    port_to_busid[current_port] = current_busid
                elif current_port and current_busid and line and ":" in line:
                    desc = line
                    # Check if this device is already in the table (by busid or mapping)
                    remote_busid = self.get_remote_busid_for_port(current_busid)
                    
                    # Skip if already in table (either by port busid or remote busid)
                    already_in_table = (current_busid in table_busids or 
                                      (remote_busid and remote_busid in table_busids))
                    
                    if not already_in_table:
                        row = self.device_table.rowCount()
                        self.device_table.insertRow(row)
                        self.device_table.setItem(row, 0, self.create_table_item_with_tooltip(f"Port {current_port}"))
                        self.device_table.setItem(row, 1, self.create_table_item_with_tooltip(desc))
                        
                        # Create toggle button for local devices
                        toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                        toggle_btn.setChecked(True)  # Local devices are already attached
                        toggle_btn.toggled.connect(
                            lambda state, port=current_port, desc=desc: self.detach_local_device(port, desc, 0 if not state else 2)
                        )
                        self.device_table.setCellWidget(row, 2, toggle_btn)
                        
                        # Create auto-reconnect toggle using the original remote busid if available
                        auto_btn = ToggleButton("AUTO", "MANUAL")
                        busid_for_auto = remote_busid if remote_busid else current_busid
                        
                        # Use saved state if available, otherwise read from encrypted file
                        if busid_for_auto in saved_auto_states:
                            auto_state = saved_auto_states[busid_for_auto]
                            auto_btn.setChecked(auto_state)
                        else:
                            auto_state = self.get_auto_reconnect_state(ip, busid_for_auto, "local")
                            auto_btn.setChecked(auto_state)
                        auto_btn.toggled.connect(
                            lambda state, ip=ip, busid=busid_for_auto: self.toggle_auto_reconnect(ip, busid, state, "local")
                        )
                        self.device_table.setCellWidget(row, 3, auto_btn)
        except Exception as e:
            self.console.append(f"Error loading devices: {e}\n")
        finally:
            # Re-enable sorting after table population is complete
            self.device_table.setSortingEnabled(True)

    def detach_local_device(self, port, desc, state):
        if state == 0:  # Unchecked (Detach)
            cmd = ["usbip", "detach", "-p", port]
            self.console.append(f"$ sudo {' '.join(cmd)}\n")
            result = self.run_sudo(cmd)
            if not result:
                self.console.append("Detach command failed or returned no output.\n")

    def parse_usbip_list(self, output):
        devices = []
        lines = output.splitlines()
        for line in lines:
            line = line.strip()
            # Match lines like: 3-2.1: Razer USA, Ltd : unknown product (1532:0077)
            if line and line[0].isdigit() and ':' in line:
                busid, rest = line.split(':', 1)
                desc = rest.strip()
                devices.append({"busid": busid, "desc": desc})
        return devices

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
            self.console.append("No sudo password set.\n")
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
                self.console.append(f"{stdout_filtered}\n")
            if stderr_filtered:
                self.console.append(f"{stderr_filtered}\n")
            return proc
        except Exception as e:
            self.console.append(f"Exception running sudo: {e}\n")
            return None

    def toggle_attach(self, ip, busid, desc, state):
        if state == 2:  # Checked (Attach)
            cmd = ["usbip", "attach", "-r", ip, "-b", busid]
            self.console.append(f"$ sudo {' '.join(cmd)}\n")
            result = self.run_sudo(cmd)
            if not result:
                self.console.append("Attach command failed or returned no output.\n")
                return False
            
            # After successful attach, find which port it was assigned to
            time.sleep(0.5)  # Give time for device to appear in port list
            port_result = subprocess.run(
                ["usbip", "port"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Find the newly attached device in port list
            port_output = port_result.stdout
            current_port = None
            port_desc = None
            port_busid = None
            
            for line in port_output.splitlines():
                line = line.strip()
                
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                    port_desc = None
                    port_busid = None
                elif current_port and line and ":" in line and not line.startswith("Port") and "->" not in line:
                    # This is a description line
                    port_desc = line
                elif current_port and line and "->" in line and line[0].isdigit():
                    # This is the busid line (e.g., "3-1 -> unknown host...")
                    port_busid = line.split()[0]
                    
                    # Now we have all info - check if this matches our target device
                    if port_desc:
                        
                        if desc in port_desc or desc.split("(")[0].strip() in port_desc:
                            # Found the device - save the mapping
                            self.save_device_mapping(busid, desc, current_port, port_busid)
                            break
            
            self.save_state(ip, busid, True)
            return True
        elif state == 0:  # Unchecked (Detach)
            # Remove device mapping when detaching
            self.remove_device_mapping(busid)
            
            # Find the port number for this device description
            port_result = subprocess.run(
                ["usbip", "port"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            port_output = port_result.stdout
            port_num = None
            current_port = None
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                # Match by description (exact or partial)
                elif current_port and line and (desc in line or desc.split("(")[0].strip() in line):
                    port_num = current_port
                    break
            if port_num:
                cmd = ["usbip", "detach", "-p", port_num]
                self.console.append(f"$ sudo {' '.join(cmd)}\n")
                result = self.run_sudo(cmd)
                if not result:
                    self.console.append("Detach command failed or returned no output.\n")
                    return False
                self.save_state(ip, busid, False)
                return True
            else:
                self.console.append(f"Could not find port for device '{desc}'\n")
                return False

    def load_state(self, ip):
        all_state = self.file_crypto.load_encrypted_file(STATE_FILE)
        return all_state.get(ip, {"attached": []})

    def save_state(self, ip, busid, attached):
        all_state = self.file_crypto.load_encrypted_file(STATE_FILE)
        state = all_state.get(ip, {"attached": []})
        if attached and busid not in state["attached"]:
            state["attached"].append(busid)
        elif not attached and busid in state["attached"]:
            state["attached"].remove(busid)
        all_state[ip] = state
        self.file_crypto.save_encrypted_file(STATE_FILE, all_state)

    def load_remote_state(self, ip):
        """Load remote device bind states for a specific IP"""
        all_state = self.file_crypto.load_encrypted_file(STATE_FILE)
        return all_state.get(ip, {}).get("remote_bound", {})

    def save_remote_state(self, ip, busid, bound):
        """Save remote device bind state for a specific IP and busid"""
        all_state = self.file_crypto.load_encrypted_file(STATE_FILE)
        state = all_state.get(ip, {"attached": [], "remote_bound": {}})
        if "remote_bound" not in state:
            state["remote_bound"] = {}
        state["remote_bound"][busid] = bound
        all_state[ip] = state
        self.file_crypto.save_encrypted_file(STATE_FILE, all_state)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def clear_console(self):
        """Clear the console output"""
        self.console.clear()
        self.console.append("Console cleared.\n")

    # Auto-reconnect functionality
    def load_auto_reconnect_settings(self):
        """Load auto-reconnect and auto-refresh settings from encrypted file"""
        data = self.file_crypto.load_encrypted_file(AUTO_RECONNECT_FILE)
        self.auto_reconnect_enabled = data.get('auto_reconnect_enabled', True)  # Default to enabled
        self.auto_reconnect_interval = data.get('interval', 30)
        self.auto_reconnect_max_attempts = data.get('max_attempts', 5)
        self.grace_period_duration = data.get('grace_period', 60)
        self.auto_refresh_enabled = data.get('auto_refresh_enabled', False)
        self.auto_refresh_interval = data.get('auto_refresh_interval', 60)
        self.theme_setting = data.get('theme_setting', 'System Theme')
        
        # Apply theme on startup
        self.apply_theme()
        
        # Start auto-refresh timer if enabled
        if self.auto_refresh_enabled:
            self.auto_refresh_timer.start(self.auto_refresh_interval * 1000)
        
        return data.get('devices', {})

    def save_auto_reconnect_settings(self):
        """Save auto-reconnect and auto-refresh settings to encrypted file"""
        data = self.file_crypto.load_encrypted_file(AUTO_RECONNECT_FILE)
        data['auto_reconnect_enabled'] = self.auto_reconnect_enabled
        data['interval'] = self.auto_reconnect_interval
        data['max_attempts'] = self.auto_reconnect_max_attempts
        data['grace_period'] = self.grace_period_duration
        data['auto_refresh_enabled'] = self.auto_refresh_enabled
        data['auto_refresh_interval'] = self.auto_refresh_interval
        data['theme_setting'] = self.theme_setting
        if 'devices' not in data:
            data['devices'] = {}
        self.file_crypto.save_encrypted_file(AUTO_RECONNECT_FILE, data)

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
        data = self.file_crypto.load_encrypted_file(AUTO_RECONNECT_FILE)
        devices = data.get('devices', {})
        device_key = f"{table_type}:{ip}:{busid}"  # Separate by table type
        return devices.get(device_key, False)

    def toggle_auto_reconnect(self, ip, busid, enabled, table_type="local"):
        """Toggle auto-reconnect for a specific device with table type separation"""
        data = self.file_crypto.load_encrypted_file(AUTO_RECONNECT_FILE)
        if 'devices' not in data:
            data['devices'] = {}
        
        device_key = f"{table_type}:{ip}:{busid}"  # Separate by table type
        data['devices'][device_key] = enabled
        
        if enabled:
            self.console.append(f"🔄 Auto-reconnect enabled for {busid} on {ip} ({table_type})")
            # Reset attempt counter when enabled
            if device_key in self.auto_reconnect_attempts:
                del self.auto_reconnect_attempts[device_key]
        else:
            self.console.append(f"⏹️ Auto-reconnect disabled for {busid} on {ip} ({table_type})")
            # Remove from attempt tracking
            if device_key in self.auto_reconnect_attempts:
                del self.auto_reconnect_attempts[device_key]
        
        self.file_crypto.save_encrypted_file(AUTO_RECONNECT_FILE, data)

    def save_device_mapping(self, remote_busid, remote_desc, port_number, port_busid):
        """Save mapping between remote device and attached port"""
        data = self.file_crypto.load_encrypted_file(DEVICE_MAPPING_FILE)
        if 'mappings' not in data:
            data['mappings'] = {}
        
        # Store mapping: remote_busid -> port info
        data['mappings'][remote_busid] = {
            'remote_desc': remote_desc,
            'port_number': port_number,
            'port_busid': port_busid,
            'timestamp': time.time()
        }
        
        self.file_crypto.save_encrypted_file(DEVICE_MAPPING_FILE, data)
        self.console.append(f"🔗 Mapped remote device {remote_busid} to port {port_number} (busid: {port_busid})")

    def get_device_mapping(self, remote_busid):
        """Get port mapping for a remote device"""
        data = self.file_crypto.load_encrypted_file(DEVICE_MAPPING_FILE)
        mappings = data.get('mappings', {})
        return mappings.get(remote_busid)

    def remove_device_mapping(self, remote_busid):
        """Remove mapping when device is detached"""
        data = self.file_crypto.load_encrypted_file(DEVICE_MAPPING_FILE)
        if 'mappings' in data and remote_busid in data['mappings']:
            del data['mappings'][remote_busid]
            self.file_crypto.save_encrypted_file(DEVICE_MAPPING_FILE, data)
            self.console.append(f"🔗 Removed mapping for remote device {remote_busid}")

    def get_remote_busid_for_port(self, port_busid):
        """Get the original remote busid for a port busid"""
        data = self.file_crypto.load_encrypted_file(DEVICE_MAPPING_FILE)
        mappings = data.get('mappings', {})
        for remote_busid, mapping_info in mappings.items():
            if mapping_info.get('port_busid') == port_busid:
                return remote_busid
        return None

    def start_grace_period(self, duration_seconds=None):
        """Start grace period to pause auto-reconnect after manual bulk operations"""
        if duration_seconds is None:
            duration_seconds = self.grace_period_duration
        
        self.auto_reconnect_grace_period = True
        self.grace_period_timer.start(duration_seconds * 1000)  # Convert to milliseconds
        self.console.append(f"⏸️ Auto-reconnect paused for {duration_seconds} seconds after manual operation")

    def end_grace_period(self):
        """End the grace period and resume auto-reconnect"""
        self.auto_reconnect_grace_period = False
        if self.auto_reconnect_enabled:
            self.console.append("▶️ Auto-reconnect resumed after grace period")

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
        """Perform remote bind/unbind operation and return success status"""
        import paramiko
        
        # Validate busid format for security
        if not SecurityValidator.validate_busid(busid):
            return False
            
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)
            
            if bind:
                actual_cmd = SecureCommandBuilder.build_usbip_bind_command(busid, password)
            else:
                actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(busid, password)
                
            if not actual_cmd:
                client.close()
                return False
                
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            stdout.read()  # Wait for command completion
            stderr.read()
            
            client.close()
            return True  # Assume success if no exception
        except Exception:
            return False

    def auto_refresh_devices(self):
        """Automatically refresh both local and SSH device tables"""
        if not self.auto_refresh_enabled:
            return
            
        # Only auto-refresh if we have an IP selected
        current_ip = self.ip_input.currentText()
        if not current_ip:
            return
            
        # Refresh all tables silently
        self.refresh_all_tables()

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
            devices = self.parse_usbip_list(output)

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
                    lambda state, ip=ip, busid=dev["busid"], desc=dev["desc"]: self.toggle_attach(ip, busid, desc, 2 if state else 0)
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
                            lambda state, port=current_port, desc=desc: self.detach_local_device(port, desc, 0 if not state else 2)
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
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox

        ip = self.ip_input.currentText()
        
        # Validate IP before proceeding
        if not SecurityValidator.validate_ip_or_hostname(ip):
            self.show_error("Invalid IP/hostname format.")
            return
            
        ssh_state = self.load_ssh_state()
        prev_username = ssh_state.get(ip, {}).get("username", "")
        prev_accept = ssh_state.get(ip, {}).get("accept_fingerprint", False)

        dialog = QDialog(self)
        dialog.setWindowTitle("SSH Credentials")
        layout = QFormLayout(dialog)

        username_input = QLineEdit()
        username_input.setText(prev_username)
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        accept_fingerprint = QCheckBox("Accept fingerprint automatically")
        accept_fingerprint.setChecked(prev_accept)

        layout.addRow("Username:", username_input)
        layout.addRow("Password:", password_input)
        layout.addRow(accept_fingerprint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            username = username_input.text()
            password = password_input.text()
            accept = accept_fingerprint.isChecked()
            
            # Validate username format
            if not SecurityValidator.validate_username(username):
                self.show_error("Invalid username format. Use only alphanumeric characters, dots, underscores, and hyphens.")
                return
            
            self.save_ssh_state(ip, username, accept)
            self.last_ssh_username = username
            self.last_ssh_password = password
            self.last_ssh_accept = accept
            self.load_remote_local_devices(username, password, accept)

    def load_remote_local_devices(self, username, password, accept_fingerprint):
        ip = self.ip_input.currentText()
        
        # Disable sorting during table population to prevent widget issues
        self.remote_table.setSortingEnabled(False)
        
        self.remote_table.setRowCount(0)
        
        # Get attached descriptions from local device table 
        attached_descs = set()
        for row in range(self.device_table.rowCount()):
            desc_item = self.device_table.item(row, 1)
            if desc_item:
                desc = desc_item.text()
                attached_descs.add(desc)
        
        if not ip:
            self.console.append("No IP selected for SSH.\n")
            return
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)  # Increased timeout
            self.ssh_client = client
            self.ssh_disco_button.setVisible(True)
            self.ipd_reset_button.setVisible(True)
            self.unbind_all_button.setVisible(True)  # Show the unbind all button
            stdin, stdout, stderr = client.exec_command("usbip list -l")
            output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.console.append(f"SSH $ usbip list -l\n")
            if output:
                self.console.append(f"{SecurityValidator.sanitize_console_output(output)}\n")
            devices = self.parse_ssh_usbip_list(output)
            
            for row, dev in enumerate(devices):
                self.remote_table.insertRow(row)
                self.remote_table.setItem(row, 0, self.create_table_item_with_tooltip(dev["busid"]))
                self.remote_table.setItem(row, 1, self.create_table_item_with_tooltip(dev["desc"]))
                
                # Create toggle button for remote devices
                toggle_btn = ToggleButton("BOUND", "UNBOUND")
                # Check if this device is currently attached by matching descriptions
                is_bound = dev["desc"] in attached_descs
                toggle_btn.setChecked(is_bound)
                toggle_btn.toggled.connect(
                    lambda state, ip=ip, username=username, password=password, busid=dev["busid"], accept=accept_fingerprint: 
                        self.toggle_bind_remote(ip, username, password, busid, accept, 2 if state else 0)
                )
                self.remote_table.setCellWidget(row, 2, toggle_btn)
                
                # Create auto-reconnect toggle for remote devices
                auto_btn = ToggleButton("AUTO", "MANUAL")
                auto_btn.setChecked(self.get_auto_reconnect_state(ip, dev["busid"], "remote"))
                auto_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"]: self.toggle_auto_reconnect(ip, busid, state, "remote")
                )
                self.remote_table.setCellWidget(row, 3, auto_btn)
            client.close()
        except Exception as e:
            self.console.append(f"SSH connection failed: Authentication or network error\n")
            # Hide SSH buttons on error
            self.ssh_disco_button.setVisible(False)
            self.ipd_reset_button.setVisible(False)
            self.unbind_all_button.setVisible(False)
        finally:
            # Re-enable sorting after table population is complete
            self.remote_table.setSortingEnabled(True)

    def toggle_bind_remote(self, ip, username, password, busid, accept_fingerprint, state):
        import paramiko
        
        # Validate busid format for security
        if not SecurityValidator.validate_busid(busid):
            self.console.append(f"Invalid busid format: {busid}\n")
            return
            
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)
            
            if state == 2:  # Checked (Bind)
                actual_cmd = SecureCommandBuilder.build_usbip_bind_command(busid, password)
                safe_cmd = f"echo [HIDDEN] | sudo -S usbip bind -b {SecurityValidator.sanitize_for_shell(busid)}"
            elif state == 0:  # Unchecked (Unbind)
                actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(busid, password)
                safe_cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {SecurityValidator.sanitize_for_shell(busid)}"
            else:
                client.close()
                return
                
            if not actual_cmd:
                self.console.append(f"Failed to build secure command for busid: {busid}\n")
                client.close()
                return
                
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.console.append(f"SSH $ {safe_cmd}\n")
            if output:
                self.console.append(f"{SecurityValidator.sanitize_console_output(output)}\n")
            
            client.close()
            self.load_devices()  # Only refresh local table
        except Exception as e:
            self.console.append(f"SSH bind/unbind failed: Connection or authentication error\n")

    def parse_ssh_usbip_list(self, output):
        devices = []
        lines = output.splitlines()
        busid = None
        desc = ""
        for line in lines:
            line = line.strip()
            if line.startswith("- busid"):
                # Example: - busid 2-1.4 (0bda:8153)
                parts = line.split()
                busid = parts[2]
                desc = ""
            elif busid and line:
                desc = line
                devices.append({"busid": busid, "desc": desc})
                busid = None
                desc = ""
        return devices

    def save_remote_device_states(self):
        """Save the current state of remote device toggle buttons"""
        states = {}
        for row in range(self.remote_table.rowCount()):
            busid_item = self.remote_table.item(row, 0)
            toggle_btn = self.remote_table.cellWidget(row, 2)
            if busid_item and toggle_btn:
                states[busid_item.text()] = toggle_btn.isChecked()
        return states
    
    def restore_remote_device_states(self, saved_states):
        """Restore the state of remote device toggle buttons"""
        for row in range(self.remote_table.rowCount()):
            busid_item = self.remote_table.item(row, 0)
            toggle_btn = self.remote_table.cellWidget(row, 2)
            if busid_item and toggle_btn and busid_item.text() in saved_states:
                toggle_btn.setChecked(saved_states[busid_item.text()])

    def refresh_all_tables(self):
        # Save current remote device states before refresh
        saved_remote_states = {}
        if hasattr(self, 'remote_table'):
            saved_remote_states = self.save_remote_device_states()
        
        self.load_devices()
        # If you want to use last SSH credentials, store them after successful SSH login
        if hasattr(self, "last_ssh_username") and hasattr(self, "last_ssh_password") and hasattr(self, "last_ssh_accept"):
            self.load_remote_local_devices(self.last_ssh_username, self.last_ssh_password, self.last_ssh_accept)
            # Restore the saved states
            if saved_remote_states:
                self.restore_remote_device_states(saved_remote_states)

    def load_ssh_state(self):
        return self.file_crypto.load_encrypted_file(SSH_STATE_FILE)

    def save_ssh_state(self, ip, username, accept_fingerprint):
        state = self.load_ssh_state()
        state[ip] = {
            "username": username,
            "accept_fingerprint": accept_fingerprint
        }
        self.file_crypto.save_encrypted_file(SSH_STATE_FILE, state)

    def disconnect_ssh(self):
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None
        self.remote_table.setRowCount(0)
        self.ssh_disco_button.setVisible(False)
        self.ipd_reset_button.setVisible(False)
        self.unbind_all_button.setVisible(False)  # Hide the unbind all button
        self.console.append("SSH session disconnected.\n")

    def reset_usbipd(self):
        ip = self.ip_input.currentText()
        username = getattr(self, "last_ssh_username", "")
        password = getattr(self, "last_ssh_password", "")
        accept = getattr(self, "last_ssh_accept", False)
        if not ip or not username or not password:
            self.console.append("Missing SSH credentials for IPD Reset.\n")
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
            self.console.append(f"SSH $ {safe_cmd}\n")
            if output:
                self.console.append(f"{SecurityValidator.sanitize_console_output(output)}\n")
                
            # Show status after restart
            actual_status_cmd = SecureCommandBuilder.build_systemctl_command("status", "usbipd", password)
            if actual_status_cmd:
                safe_status_cmd = "echo [HIDDEN] | sudo -S systemctl status usbipd"
                stdin, stdout, stderr = client.exec_command(actual_status_cmd)
                status_output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
                self.console.append(f"SSH $ {safe_status_cmd}\n")
                if status_output:
                    self.console.append(f"{SecurityValidator.sanitize_console_output(status_output)}\n")
            client.close()
        except Exception as e:
            self.console.append(f"Error restarting usbipd: Connection or authentication failed\n")