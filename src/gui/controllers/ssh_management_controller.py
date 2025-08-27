"""
SSH Management Controller for USB/IP GUI Application

This controller handles all SSH-related operations including:
- SSH connection management and credential handling
- Remote device discovery and binding operations
- SSH state persistence and security
- Remote command execution via paramiko
"""

import paramiko
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox
from ..widgets.toggle_button import ToggleButton
from security.validator import SecurityValidator, SecureCommandBuilder


class SSHManagementController:
    """Controller for SSH connection and remote device management operations"""
    
    def __init__(self, main_window):
        """Initialize SSH management controller with reference to main window"""
        self.main_window = main_window
        self.ssh_client = None
        
    def prompt_ssh_credentials(self):
        """Prompt user for SSH credentials and initiate connection"""
        ip = self.main_window.ip_input.currentText()
        
        # Validate IP before proceeding
        if not SecurityValidator.validate_ip_or_hostname(ip):
            self.main_window.show_error("Invalid IP/hostname format.")
            return
            
        ssh_state = self.load_ssh_state()
        prev_username = ssh_state.get(ip, {}).get("username", "")
        prev_accept = ssh_state.get(ip, {}).get("accept_fingerprint", False)

        dialog = QDialog(self.main_window)
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
                self.main_window.show_error("Invalid username format. Use only alphanumeric characters, dots, underscores, and hyphens.")
                return
            
            self.save_ssh_state(ip, username, accept)
            self.main_window.last_ssh_username = username
            self.main_window.last_ssh_password = password
            self.main_window.last_ssh_accept = accept
            self.load_remote_local_devices(username, password, accept)

    def load_remote_local_devices(self, username, password, accept_fingerprint):
        """Load remote devices via SSH connection and populate remote table"""
        ip = self.main_window.ip_input.currentText()
        
        # Disable sorting during table population to prevent widget issues
        self.main_window.remote_table.setSortingEnabled(False)
        
        self.main_window.remote_table.setRowCount(0)
        
        # Load remote device states from persistent storage
        remote_states = self.main_window.load_remote_state(ip)
        
        if not ip:
            self.main_window.console.append("No IP selected for SSH.\n")
            return
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)  # Increased timeout
            self.ssh_client = client
            self.main_window.ssh_client = client  # Keep reference in main window
            self.main_window.ssh_disco_button.setVisible(True)
            self.main_window.ipd_reset_button.setVisible(True)
            self.main_window.unbind_all_button.setVisible(True)  # Show the unbind all button
            stdin, stdout, stderr = client.exec_command("usbip list -l")
            output = self.main_window.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.main_window.console.append(f"SSH $ usbip list -l\n")
            if output:
                self.main_window.console.append(f"{SecurityValidator.sanitize_console_output(output)}\n")
            devices = self.parse_ssh_usbip_list(output)
            
            for row, dev in enumerate(devices):
                self.main_window.remote_table.insertRow(row)
                self.main_window.remote_table.setItem(row, 0, self.main_window.create_table_item_with_tooltip(dev["busid"]))
                self.main_window.remote_table.setItem(row, 1, self.main_window.create_table_item_with_tooltip(dev["desc"]))
                
                # Create toggle button for remote devices
                toggle_btn = ToggleButton("BOUND", "UNBOUND")
                # Check if this device is currently bound based on persistent state
                is_bound = remote_states.get(dev["busid"], False)
                
                # Set the initial state WITHOUT triggering the signal
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(is_bound)
                toggle_btn.blockSignals(False)
                
                # Now connect the signal handler
                toggle_btn.toggled.connect(
                    lambda state, ip=ip, username=username, password=password, busid=dev["busid"], accept=accept_fingerprint: 
                        self.toggle_bind_remote(ip, username, password, busid, accept, 2 if state else 0)
                )
                self.main_window.remote_table.setCellWidget(row, 2, toggle_btn)
                
                # Create auto-reconnect toggle for remote devices
                auto_btn = ToggleButton("AUTO", "MANUAL")
                
                # Set the initial state WITHOUT triggering the signal
                auto_btn.blockSignals(True)
                auto_btn.setChecked(self.main_window.get_auto_reconnect_state(ip, dev["busid"], "remote"))
                auto_btn.blockSignals(False)
                
                # Now connect the signal handler
                auto_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev["busid"]: self.main_window.toggle_auto_reconnect(ip, busid, state, "remote")
                )
                self.main_window.remote_table.setCellWidget(row, 3, auto_btn)
            client.close()
        except Exception as e:
            self.main_window.console.append(f"SSH connection failed: Authentication or network error\n")
            # Hide SSH buttons on error
            self.main_window.ssh_disco_button.setVisible(False)
            self.main_window.ipd_reset_button.setVisible(False)
            self.main_window.unbind_all_button.setVisible(False)
        finally:
            # Re-enable sorting after table population is complete
            self.main_window.remote_table.setSortingEnabled(True)

    def toggle_bind_remote(self, ip, username, password, busid, accept_fingerprint, state):
        """Toggle bind/unbind state for remote device"""
        # Validate busid format for security
        if not SecurityValidator.validate_busid(busid):
            self.main_window.console.append(f"Invalid busid format: {busid}\n")
            return
            
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)
            
            # Get the sudo password from main window for usbip commands
            sudo_password = self.main_window._get_sudo_password()
            
            if state == 2:  # Checked (Bind)
                actual_cmd = SecureCommandBuilder.build_usbip_bind_command(busid, sudo_password)
                safe_cmd = f"echo [HIDDEN] | sudo -S usbip bind -b {SecurityValidator.sanitize_for_shell(busid)}"
            elif state == 0:  # Unchecked (Unbind)
                actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(busid, sudo_password)
                safe_cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {SecurityValidator.sanitize_for_shell(busid)}"
            else:
                client.close()
                return
                
            if not actual_cmd:
                self.main_window.console.append(f"Failed to build secure command for busid: {busid}\n")
                client.close()
                return
                
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            output = self.main_window.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
            self.main_window.console.append(f"SSH $ {safe_cmd}\n")
            if output:
                self.main_window.console.append(f"{SecurityValidator.sanitize_console_output(output)}\n")
            
            client.close()
            
            # Save the remote bind state after successful operation
            if state == 2:  # Bind operation
                self.main_window.save_remote_state(ip, busid, True)
                self.main_window.console.append(f"✓ Remote device {busid} bound and state saved\n")
            elif state == 0:  # Unbind operation  
                self.main_window.save_remote_state(ip, busid, False)
                self.main_window.console.append(f"✓ Remote device {busid} unbound and state saved\n")
            
            # Start grace period to prevent auto-reconnect interference
            self.main_window.start_grace_period()
            
            self.main_window.device_management_controller.load_devices()  # Only refresh local table
        except Exception as e:
            self.main_window.console.append(f"SSH bind/unbind failed: Connection or authentication error\n")

    def perform_remote_bind(self, ip, username, password, busid, accept_fingerprint, bind=True):
        """Perform remote bind/unbind operation and return success status"""
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
            
            # Get the sudo password from main window for usbip commands
            sudo_password = self.main_window._get_sudo_password()
            
            if bind:
                actual_cmd = SecureCommandBuilder.build_usbip_bind_command(busid, sudo_password)
            else:
                actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(busid, sudo_password)
                
            if not actual_cmd:
                client.close()
                return False
                
            stdin, stdout, stderr = client.exec_command(actual_cmd)
            stdout.read()  # Wait for command completion
            stderr.read()
            
            # Save the remote bind state after successful operation
            self.main_window.save_remote_state(ip, busid, bind)
            
            client.close()
            return True  # Assume success if no exception
        except Exception:
            return False

    def parse_ssh_usbip_list(self, output):
        """Parse SSH usbip list output and return list of devices"""
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
        """Save the current state of remote device toggle buttons to persistent storage"""
        ip = self.main_window.ip_input.currentText()
        if not ip:
            return {}
            
        states = {}
        saved_count = 0
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
            auto_btn = self.main_window.remote_table.cellWidget(row, 3)
            
            if busid_item and toggle_btn and auto_btn:
                busid = busid_item.text()
                is_bound = toggle_btn.isChecked()
                auto_enabled = auto_btn.isChecked()
                
                states[busid] = {'bound': is_bound, 'auto': auto_enabled}
                
                # Save bind state to persistent storage
                self.main_window.save_remote_state(ip, busid, is_bound)
                
                # Save auto-reconnect state using the silent method (no console output)
                self.main_window.data_persistence_controller.set_auto_reconnect_state_silent(ip, busid, auto_enabled, "remote")
                
                saved_count += 1
                self.main_window.console.append(f"  Saving {busid}: bind={is_bound}, auto={auto_enabled}")
        
        self.main_window.console.append(f"  Saved {saved_count} device states total")
        return states
    
    def restore_remote_device_states(self, saved_states):
        """Restore the state of remote device toggle buttons from persistent storage"""
        ip = self.main_window.ip_input.currentText()
        if not ip:
            return
            
        # Load from persistent storage - both bind states and auto-reconnect states
        remote_states = self.main_window.load_remote_state(ip)
        
        restored_count = 0
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
            auto_btn = self.main_window.remote_table.cellWidget(row, 3)
            
            if busid_item and toggle_btn and auto_btn:
                busid = busid_item.text()
                
                # Restore bind state
                is_bound = remote_states.get(busid, False)
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(is_bound)
                toggle_btn.blockSignals(False)
                
                # Restore auto-reconnect state
                auto_enabled = self.main_window.get_auto_reconnect_state(ip, busid, "remote")
                auto_btn.blockSignals(True)
                auto_btn.setChecked(auto_enabled)
                auto_btn.blockSignals(False)
                
                restored_count += 1
                self.main_window.console.append(f"  Device {busid}: bind={is_bound}, auto={auto_enabled}")
        
        self.main_window.console.append(f"  Restored {restored_count} device states total")

    def load_ssh_state(self):
        """Load SSH state from encrypted file"""
        return self.main_window.file_crypto.load_encrypted_file("ssh_state.enc")

    def save_ssh_state(self, ip, username, accept_fingerprint):
        """Save SSH state to encrypted file"""
        state = self.load_ssh_state()
        state[ip] = {
            "username": username,
            "accept_fingerprint": accept_fingerprint
        }
        self.main_window.file_crypto.save_encrypted_file("ssh_state.enc", state)

    def disconnect_ssh(self):
        """Disconnect SSH connection and clean up UI"""
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception:
                pass
            self.ssh_client = None
            
        # Also clear main window reference
        if hasattr(self.main_window, 'ssh_client'):
            self.main_window.ssh_client = None
            
        self.main_window.remote_table.setRowCount(0)
        
        # Hide SSH-related buttons
        self.main_window.ssh_disco_button.setVisible(False)
        self.main_window.ipd_reset_button.setVisible(False)
        self.main_window.unbind_all_button.setVisible(False)

    def refresh_with_saved_credentials(self):
        """Refresh remote devices using previously saved SSH credentials"""
        # If you want to use last SSH credentials, store them after successful SSH login
        if (hasattr(self.main_window, "last_ssh_username") and 
            hasattr(self.main_window, "last_ssh_password") and 
            hasattr(self.main_window, "last_ssh_accept")):
            
            # Instead of saving UI state, save from persistent storage before any operations
            ip = self.main_window.ip_input.currentText()
            if ip:
                # Read current states from persistent storage (not UI)
                remote_bind_states = self.main_window.load_remote_state(ip)
                auto_reconnect_states = {}
                
                # Get current device list to check what auto-reconnect states exist
                for row in range(self.main_window.remote_table.rowCount()):
                    busid_item = self.main_window.remote_table.item(row, 0)
                    if busid_item:
                        busid = busid_item.text()
                        auto_state = self.main_window.get_auto_reconnect_state(ip, busid, "remote")
                        auto_reconnect_states[busid] = auto_state
                
                # Now refresh the UI
                self.load_remote_local_devices(
                    self.main_window.last_ssh_username, 
                    self.main_window.last_ssh_password, 
                    self.main_window.last_ssh_accept
                )
                
                # The load_remote_local_devices should now correctly restore from persistent storage
                self.main_window.console.append(f"Refresh: UI refreshed with persistent state data\n")
