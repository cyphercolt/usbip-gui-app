import json
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox, QInputDialog, QTextEdit, QCheckBox, QLineEdit)
from PyQt6.QtCore import Qt
import subprocess
from functools import partial
import paramiko
from security.crypto import FileEncryption, MemoryProtection

IPS_FILE = "ips.enc"
STATE_FILE = "usbip_state.enc" 
SSH_STATE_FILE = "ssh_state.enc"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize encryption
        self.file_crypto = FileEncryption()
        self.memory_crypto = MemoryProtection()
        
        self.setWindowTitle("USBIP GUI Application")
        self.setGeometry(100, 100, 1000, 600)

        self._obfuscated_sudo_password = ""  # Obfuscated password storage
        self.prompt_sudo_password()

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

        # --- Two tables side by side ---
        tables_layout = QHBoxLayout()

        # Local table
        local_layout = QVBoxLayout()
        local_layout.addWidget(QLabel("Local Devices"))
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(3)
        self.device_table.setHorizontalHeaderLabels(["Device", "Description", "Attached"])
        local_layout.addWidget(self.device_table)
        # Attach All / Detach All / Clear buttons under local table
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_console)
        self.attach_all_button = QPushButton("Attach All")
        self.attach_all_button.clicked.connect(self.attach_all_devices)
        self.detach_all_button = QPushButton("Detach All")
        self.detach_all_button.clicked.connect(self.detach_all_devices)
        btns_widget = QWidget()
        btns_layout = QHBoxLayout()
        btns_layout.addWidget(self.clear_button)
        btns_layout.addStretch()
        btns_layout.addWidget(self.attach_all_button)
        btns_layout.addWidget(self.detach_all_button)
        btns_widget.setLayout(btns_layout)
        local_layout.addWidget(btns_widget)
        tables_layout.addLayout(local_layout)

        # Remote SSH table
        remote_layout = QVBoxLayout()
        remote_layout.addWidget(QLabel("Remote SSH Devices"))
        self.remote_table = QTableWidget()
        self.remote_table.setColumnCount(3)
        self.remote_table.setHorizontalHeaderLabels(["Device", "Description", "Remote Bind"])
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
        
        tables_layout.addLayout(remote_layout)

        self.layout.addLayout(tables_layout)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.layout.addWidget(QLabel("Console Output:"))
        self.layout.addWidget(self.console)

        # Exit button at bottom right
        exit_layout = QHBoxLayout()
        exit_layout.addStretch()
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close)
        exit_layout.addWidget(self.exit_button)
        self.layout.addLayout(exit_layout)

        self.load_ips()
        self.load_devices()

    def attach_all_devices(self):
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 2)
            busid_item = self.device_table.item(row, 0)
            desc_item = self.device_table.item(row, 1)
            if checkbox and not checkbox.isChecked():
                # Only attach if not checked
                checkbox.setChecked(True)
                # The checkbox's stateChanged signal will call toggle_attach

    def detach_all_devices(self):
        for row in range(self.device_table.rowCount()):
            checkbox = self.device_table.cellWidget(row, 2)
            busid_item = self.device_table.item(row, 0)
            desc_item = self.device_table.item(row, 1)
            if checkbox and checkbox.isChecked():
                # Only detach if checked
                checkbox.setChecked(False)
                # The checkbox's stateChanged signal will call toggle_attach

    def unbind_all_devices(self):
        """Unbind all bound devices on the remote SSH server and refresh tables"""
        ip = self.ip_input.currentText()
        username = getattr(self, "last_ssh_username", "")
        password = getattr(self, "last_ssh_password", "")
        accept = getattr(self, "last_ssh_accept", False)
        
        if not ip or not username or not password:
            self.console.append("Missing SSH credentials for Unbind All.\n")
            return
            
        try:
            import paramiko
            client = paramiko.SSHClient()
            if accept:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=10)
            
            # Unbind all bound devices
            for row in range(self.remote_table.rowCount()):
                checkbox = self.remote_table.cellWidget(row, 2)
                busid_item = self.remote_table.item(row, 0)
                if checkbox and checkbox.isChecked() and busid_item:
                    busid = busid_item.text()
                    cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {busid}"
                    actual_cmd = f"echo {password} | sudo -S usbip unbind -b {busid}"
                    stdin, stdout, stderr = client.exec_command(actual_cmd)
                    output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
                    self.console.append(f"SSH $ {cmd}\n")
                    if output:
                        self.console.append(f"{output}\n")
            
            client.close()
            self.console.append("All devices unbound successfully.\n")
            
            # Refresh all tables to update the UI and uncheck checkboxes
            self.refresh_all_tables()
            
        except Exception as e:
            self.console.append(f"Error unbinding all devices: {e}\n")

    def _get_sudo_password(self):
        """Get the deobfuscated sudo password"""
        if not self._obfuscated_sudo_password:
            return ""
        return self.memory_crypto.deobfuscate_string(self._obfuscated_sudo_password)

    def prompt_sudo_password(self):
        max_attempts = 3
        attempts = 0
        
        while attempts < max_attempts:
            password, ok = QInputDialog.getText(
                self,
                "Sudo Password",
                f"Enter your sudo password (attempt {attempts + 1}/{max_attempts}):" if attempts > 0 else "Enter your sudo password:",
                QLineEdit.EchoMode.Password
            )
            
            if not ok:  # User cancelled
                self.show_error("Sudo password is required for this application to function properly.")
                self.close()
                return
                
            if not password.strip():  # Empty password
                attempts += 1
                if attempts < max_attempts:
                    QMessageBox.warning(self, "Invalid Password", "Password cannot be empty. Please try again.")
                    continue
                else:
                    self.show_error("No valid sudo password provided. Application will exit.")
                    self.close()
                    return
            
            # Test the password by running a simple sudo command
            if self.test_sudo_password(password):
                # Store obfuscated password in memory
                self._obfuscated_sudo_password = self.memory_crypto.obfuscate_string(password)
                # Clear the plain text password from local scope
                password = "0" * len(password)  # Overwrite
                print(f"Sudo password validated successfully")
                return
            else:
                attempts += 1
                if attempts < max_attempts:
                    QMessageBox.warning(self, "Invalid Password", "Incorrect sudo password. Please try again.")
                else:
                    self.show_error("Invalid sudo password after multiple attempts. Application will exit.")
                    self.close()
                    return

    def test_sudo_password(self, password):
        """Test if the provided sudo password is correct"""
        try:
            proc = subprocess.run(
                ['sudo', '-S', 'true'],  # Simple command that just returns true
                input=password + '\n',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False
            )
            return proc.returncode == 0
        except Exception:
            return False

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
        if ok and text and text not in [self.ip_input.itemText(i) for i in range(self.ip_input.count())]:
            self.ip_input.addItem(text)
            self.save_ips()

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
        try:
            result = subprocess.run(
                ["ping", "-c", "1", ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            self.console.append(f"$ ping -c 1 {ip}\n{output}\n")
        except Exception as e:
            self.console.append(f"Error pinging {ip}: {e}\n")

    def load_devices(self):
        self.device_table.setRowCount(0)
        ip = self.ip_input.currentText()
        if not ip:
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
            current_port = None
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                elif current_port and line and line[0].isdigit() and '-' in line:
                    busid = line.split()[0]
                    attached_busids.add(busid)

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

            # Prepare attached_descs before using it
            attached_descs = set()
            for row in range(self.device_table.rowCount()):
                desc_item = self.device_table.item(row, 1)
                if desc_item:
                    desc = desc_item.text()
                    attached_descs.add(desc)

            # Add remote devices
            for dev in devices:
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                self.device_table.setItem(row, 0, QTableWidgetItem(dev["busid"]))
                self.device_table.setItem(row, 1, QTableWidgetItem(dev["desc"]))
                checkbox = QCheckBox()
                checkbox.blockSignals(True)
                checkbox.setChecked(dev["desc"] in attached_descs)
                checkbox.blockSignals(False)
                checkbox.stateChanged.connect(
                    lambda state, ip=ip, busid=dev["busid"], desc=dev["desc"]: self.toggle_attach(ip, busid, desc, state)
                )
                self.device_table.setCellWidget(row, 2, checkbox)

            # List locally attached devices (usbip port) that aren't in the remote list
            attached_descs = set()
            for row in range(self.device_table.rowCount()):
                desc_item = self.device_table.item(row, 1)
                if desc_item:
                    desc = desc_item.text()
                    attached_descs.add(desc)

            current_port = None
            for line in port_output.splitlines():
                line = line.strip()
                if line.startswith("Port"):
                    current_port = line.split()[1].replace(":", "")
                elif current_port and line and ":" in line:
                    desc = line
                    # Only add if not already present
                    if desc not in attached_descs:
                        row = self.device_table.rowCount()
                        self.device_table.insertRow(row)
                        self.device_table.setItem(row, 0, QTableWidgetItem(f"Port {current_port}"))
                        self.device_table.setItem(row, 1, QTableWidgetItem(desc))
                        checkbox = QCheckBox()
                        checkbox.setChecked(True)
                        checkbox.stateChanged.connect(
                            lambda state, port=current_port, desc=desc: self.detach_local_device(port, desc, state)
                        )
                        self.device_table.setCellWidget(row, 2, checkbox)
        except Exception as e:
            self.console.append(f"Error loading devices: {e}\n")

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
            self.save_state(ip, busid, True)
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
            else:
                self.console.append(f"Could not find port for device '{desc}'\n")
            self.save_state(ip, busid, False)

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

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def clear_console(self):
        """Clear the console output"""
        self.console.clear()
        self.console.append("Console cleared.\n")

    def closeEvent(self, event):
        # Clear sensitive data from memory
        if hasattr(self, '_obfuscated_sudo_password'):
            self._obfuscated_sudo_password = "0" * len(self._obfuscated_sudo_password)
        if hasattr(self, 'last_ssh_password'):
            self.last_ssh_password = "0" * len(self.last_ssh_password)
        
        # Only save IPs if the UI was fully initialized
        if hasattr(self, 'ip_input'):
            self.save_ips()
        event.accept()

    def prompt_ssh_credentials(self):
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox

        ip = self.ip_input.currentText()
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
            self.save_ssh_state(ip, username, accept)
            self.last_ssh_username = username
            self.last_ssh_password = password
            self.last_ssh_accept = accept
            self.load_remote_local_devices(username, password, accept)

    def load_remote_local_devices(self, username, password, accept_fingerprint):
        ip = self.ip_input.currentText()
        self.remote_table.setRowCount(0)
        # Get attached descriptions from local table
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
            client.connect(ip, username=username, password=password, timeout=10)
            self.ssh_client = client
            self.ssh_disco_button.setVisible(True)
            self.ipd_reset_button.setVisible(True)
            self.unbind_all_button.setVisible(True)  # Show the unbind all button
            stdin, stdout, stderr = client.exec_command("usbip list -l")
            output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.console.append(f"SSH $ usbip list -l\n")
            if output:
                self.console.append(f"{output}\n")
            devices = self.parse_ssh_usbip_list(output)
            for row, dev in enumerate(devices):
                self.remote_table.insertRow(row)
                self.remote_table.setItem(row, 0, QTableWidgetItem(dev["busid"]))
                self.remote_table.setItem(row, 1, QTableWidgetItem(dev["desc"]))
                checkbox = QCheckBox()
                checkbox.blockSignals(True)
                # Set checked if description matches any attached local device
                checkbox.setChecked(dev["desc"] in attached_descs)
                checkbox.blockSignals(False)
                checkbox.stateChanged.connect(
                    lambda state, ip=ip, username=username, password=password, busid=dev["busid"], accept=accept_fingerprint: 
                        self.toggle_bind_remote(ip, username, password, busid, accept, state)
                )
                self.remote_table.setCellWidget(row, 2, checkbox)
            client.close()
        except Exception as e:
            self.console.append(f"SSH error: {e}\n")
            # Hide SSH buttons on error
            self.ssh_disco_button.setVisible(False)
            self.ipd_reset_button.setVisible(False)
            self.unbind_all_button.setVisible(False)

    def toggle_bind_remote(self, ip, username, password, busid, accept_fingerprint, state):
        import paramiko
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=10)
            if state == 2:  # Checked (Bind)
                actual_cmd = f"echo {password} | sudo -S usbip bind -b {busid}"
                safe_cmd = f"echo [HIDDEN] | sudo -S usbip bind -b {busid}"
            elif state == 0:  # Unchecked (Unbind)
                actual_cmd = f"echo {password} | sudo -S usbip unbind -b {busid}"
                safe_cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {busid}"
            else:
                client.close()
                return
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.console.append(f"SSH $ {safe_cmd}\n")
            if output:
                self.console.append(f"{output}\n")
            client.close()
            self.load_devices()  # Only refresh local table
        except Exception as e:
            self.console.append(f"SSH bind/unbind error: {e}\n")

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

    def refresh_all_tables(self):
        self.load_devices()
        # If you want to use last SSH credentials, store them after successful SSH login
        if hasattr(self, "last_ssh_username") and hasattr(self, "last_ssh_password") and hasattr(self, "last_ssh_accept"):
            self.load_remote_local_devices(self.last_ssh_username, self.last_ssh_password, self.last_ssh_accept)

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
            client.connect(ip, username=username, password=password, timeout=10)
            # Restart usbipd
            actual_cmd = f"echo {password} | sudo -S systemctl restart usbipd"
            safe_cmd = f"echo [HIDDEN] | sudo -S systemctl restart usbipd"
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.console.append(f"SSH $ {safe_cmd}\n")
            if output:
                self.console.append(f"{output}\n")
            # Show status after restart
            actual_status_cmd = f"echo {password} | sudo -S systemctl status usbipd"
            safe_status_cmd = f"echo [HIDDEN] | sudo -S systemctl status usbipd"
            stdin, stdout, stderr = client.exec_command(actual_status_cmd)
            status_output = self.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.console.append(f"SSH $ {safe_status_cmd}\n")
            if status_output:
                self.console.append(f"{status_output}\n")
            client.close()
        except Exception as e:
            self.console.append(f"Error restarting usbipd: {e}\n")