import json
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox, QInputDialog, QTextEdit, QCheckBox, QLineEdit,
                             QSplitter, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette
import subprocess
from functools import partial
import paramiko
from security.crypto import FileEncryption, MemoryProtection
from security.validator import SecurityValidator, SecureCommandBuilder
from security.rate_limiter import ConnectionSecurity

IPS_FILE = "ips.enc"
STATE_FILE = "usbip_state.enc" 
SSH_STATE_FILE = "ssh_state.enc"


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
            self.setStyleSheet("""
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
            """)
        else:
            self.setText(self.text_off)
            self.setStyleSheet("""
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
            """)


class MainWindow(QMainWindow):
    def __init__(self, sudo_password):
        super().__init__()
        
        # Initialize encryption
        self.file_crypto = FileEncryption()
        self.memory_crypto = MemoryProtection()
        self.connection_security = ConnectionSecurity()
        
        self.setWindowTitle("USBIP GUI Application")
        self.setGeometry(100, 100, 1000, 600)

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

        self.layout.addLayout(btn_layout)

        # --- Resizable splitter with two tables ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Local table widget
        local_widget = QWidget()
        local_layout = QVBoxLayout()
        local_layout.addWidget(QLabel("Local Devices"))
        
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(3)
        self.device_table.setHorizontalHeaderLabels(["Device", "Description", "Action"])
        
        # Make tables sortable
        self.device_table.setSortingEnabled(True)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
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
        self.remote_table.setColumnCount(3)
        self.remote_table.setHorizontalHeaderLabels(["Device", "Description", "Action"])
        
        # Make remote table sortable too
        self.remote_table.setSortingEnabled(True)
        self.remote_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
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
        self.console.setMinimumHeight(200)  # Make console taller to show welcome message fully
        console_layout.addWidget(self.console)
        
        # Clear button at bottom left of console
        console_bottom_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_console)
        console_bottom_layout.addWidget(self.clear_button)
        console_bottom_layout.addStretch()
        console_layout.addLayout(console_bottom_layout)
        
        self.layout.addLayout(console_layout)

        # Exit button at bottom right
        exit_layout = QHBoxLayout()
        exit_layout.addStretch()
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        exit_layout.addWidget(self.exit_button)
        self.layout.addLayout(exit_layout)

        self.load_ips()
        self.load_devices()
        
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
        self.console.append("Ready for device management!")
        self.console.append("=" * 50)
        self.console.append("")

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
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                elif current_port and line and line[0].isdigit() and '-' in line:
                    busid = line.split()[0]
                    attached_busids.add(busid)
                elif current_port and line and ":" in line:
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
                self.device_table.setItem(row, 0, QTableWidgetItem(dev["busid"]))
                self.device_table.setItem(row, 1, QTableWidgetItem(dev["desc"]))
                
                # Create toggle button instead of checkbox
                toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                toggle_btn.setChecked(dev["desc"] in attached_descs)
                toggle_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"], desc=dev["desc"]: self.toggle_attach(ip, busid, desc, 2 if state else 0)
                )
                self.device_table.setCellWidget(row, 2, toggle_btn)

            # List locally attached devices (usbip port) that aren't in the remote list
            # Build set of descriptions already added to the table
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
                    # Only add if not already present in the table
                    if desc not in table_descs:
                        row = self.device_table.rowCount()
                        self.device_table.insertRow(row)
                        self.device_table.setItem(row, 0, QTableWidgetItem(f"Port {current_port}"))
                        self.device_table.setItem(row, 1, QTableWidgetItem(desc))
                        
                        # Create toggle button for local devices
                        toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                        toggle_btn.setChecked(True)  # Local devices are already attached
                        toggle_btn.toggled.connect(
                            lambda state, port=current_port, desc=desc: self.detach_local_device(port, desc, 0 if not state else 2)
                        )
                        self.device_table.setCellWidget(row, 2, toggle_btn)
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
            self.save_state(ip, busid, True)
            return True
        elif state == 0:  # Unchecked (Detach)
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

    def closeEvent(self, event):
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
                self.remote_table.setItem(row, 0, QTableWidgetItem(dev["busid"]))
                self.remote_table.setItem(row, 1, QTableWidgetItem(dev["desc"]))
                
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