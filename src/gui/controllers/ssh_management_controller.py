"""
SSH Management Controller for USB/IP GUI Application

This controller handles all SSH-related operations including:
- SSH connection management and credential handling
- Remote device discovery and binding operations
- SSH state persistence and security
- Remote command execution via paramiko
"""

import paramiko
import platform
import time
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QCheckBox,
    QTableWidgetItem,
)
from ..widgets.toggle_button import ToggleButton
from security.validator import SecurityValidator, SecureCommandBuilder
from utils.remote_os_detector import RemoteOSDetector


class SSHManagementController:
    """Controller for SSH connection and remote device management operations"""

    def __init__(self, main_window):
        """Initialize SSH management controller with reference to main window"""
        self.main_window = main_window
        self.ssh_client = None
        self.remote_os_type = None
        self.remote_has_usbipd = False

    def safe_toggle_bind_remote(
        self, ip, username, password, busid, desc, accept_fingerprint, state
    ):
        """Safely toggle bind with immediate button disabling"""
        # Immediately disable all buttons to prevent race conditions
        self.main_window.disable_all_device_buttons()
        # Call the actual toggle method
        self.toggle_bind_remote(
            ip, username, password, busid, desc, accept_fingerprint, state
        )

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec():
            username = username_input.text()
            password = password_input.text()
            accept = accept_fingerprint.isChecked()

            # Validate username format
            if not SecurityValidator.validate_username(username):
                self.main_window.show_error(
                    "Invalid username format. Use only alphanumeric characters, dots, underscores, and hyphens."
                )
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
            self.main_window.append_simple_message("❌ No IP selected for SSH")
            return
        try:
            # First, detect remote OS type
            self.main_window.append_simple_message(
                "🔍 Detecting remote operating system..."
            )
            self.remote_os_type, self.remote_has_usbipd = (
                RemoteOSDetector.detect_remote_os(
                    ip, username, password, accept_fingerprint
                )
            )

            if self.remote_os_type:
                os_msg = f"🖥️ Remote OS detected: {self.remote_os_type.title()}"
                if self.remote_os_type == "windows" and self.remote_has_usbipd:
                    os_msg += " (usbipd service running)"
                elif self.remote_os_type == "windows" and not self.remote_has_usbipd:
                    os_msg += " (usbipd service not available)"
                self.main_window.append_simple_message(os_msg)
            else:
                self.main_window.append_simple_message(
                    "⚠️ Could not detect remote OS, assuming Linux"
                )
                self.remote_os_type = "linux"
                self.remote_has_usbipd = False

            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(
                ip, username=username, password=password, timeout=15
            )  # Increased timeout
            self.ssh_client = client
            self.main_window.ssh_client = client  # Keep reference in main window
            self.main_window.ssh_disco_button.setVisible(True)
            self.main_window.unbind_all_button.setVisible(
                True
            )  # Show the unbind all button

            # Show appropriate service management button based on remote OS
            if self.remote_os_type == "windows":
                self.main_window.usbipd_service_button.setVisible(True)
                self.main_window.linux_usbip_service_button.setVisible(False)
            else:
                # Linux system - show Linux USB/IP service management
                self.main_window.usbipd_service_button.setVisible(False)
                self.main_window.linux_usbip_service_button.setVisible(True)

            # Use appropriate command based on remote OS
            list_cmd = RemoteOSDetector.get_remote_usbip_list_command(
                self.remote_os_type, self.remote_has_usbipd
            )

            # Execute the list command
            if self.remote_os_type == "windows" and self.remote_has_usbipd:
                # Windows usbipd doesn't need sudo
                stdin, stdout, stderr = client.exec_command(list_cmd)
                safe_cmd = list_cmd
            else:
                # Linux/Unix or Windows without usbipd - traditional usbip
                stdin, stdout, stderr = client.exec_command(list_cmd)
                safe_cmd = list_cmd

            output = self.main_window.filter_sudo_prompts(
                stdout.read().decode() + stderr.read().decode()
            )
            self.main_window.append_verbose_message(f"SSH $ {safe_cmd}\n")
            if output:
                self.main_window.append_verbose_message(
                    f"{SecurityValidator.sanitize_console_output(output)}\n"
                )

            # Parse output based on remote OS type
            if self.remote_os_type == "windows" and self.remote_has_usbipd:
                devices = self.parse_usbipd_list(output)
            else:
                devices = self.parse_ssh_usbip_list(output)

            for row, dev in enumerate(devices):
                self.main_window.remote_table.insertRow(row)
                self.main_window.remote_table.setItem(
                    row,
                    0,
                    self.main_window.create_table_item_with_tooltip(dev["busid"]),
                )
                self.main_window.remote_table.setItem(
                    row, 1, self.main_window.create_table_item_with_tooltip(dev["desc"])
                )

                # Create toggle button for remote devices
                toggle_btn = ToggleButton("BOUND", "UNBOUND")
                # Check if this device is currently bound based on persistent state
                is_bound = remote_states.get(dev["busid"], False)

                # Set the initial state WITHOUT triggering the signal
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(is_bound)
                toggle_btn.blockSignals(False)

                # Add sortable text item for the Action column
                action_item = QTableWidgetItem("BOUND" if is_bound else "UNBOUND")
                self.main_window.remote_table.setItem(row, 2, action_item)

                # Now connect the signal handler
                toggle_btn.toggled.connect(
                    lambda state, ip=ip, username=username, password=password, busid=dev[
                        "busid"
                    ], desc=dev[
                        "desc"
                    ], accept=accept_fingerprint: self.safe_toggle_bind_remote(
                        ip, username, password, busid, desc, accept, 2 if state else 0
                    )
                )
                self.main_window.remote_table.setCellWidget(row, 2, toggle_btn)

                # Create auto-reconnect toggle for remote devices
                auto_btn = ToggleButton("AUTO", "MANUAL")

                # Set the initial state WITHOUT triggering the signal
                auto_btn.blockSignals(True)
                auto_enabled = self.main_window.get_auto_reconnect_state(
                    ip, dev["busid"], "remote"
                )
                auto_btn.setChecked(auto_enabled)
                auto_btn.blockSignals(False)

                # Add sortable text item for the Auto column
                auto_item = QTableWidgetItem("AUTO" if auto_enabled else "MANUAL")
                self.main_window.remote_table.setItem(row, 3, auto_item)

                # Now connect the signal handler
                auto_btn.toggled.connect(
                    lambda state, ip=ip, busid=dev[
                        "busid"
                    ]: self.main_window.toggle_auto_reconnect(
                        ip, busid, state, "remote"
                    )
                )
                self.main_window.remote_table.setCellWidget(row, 3, auto_btn)
            client.close()
        except Exception as e:
            self.main_window.append_simple_message(
                "❌ SSH connection failed: Authentication or network error"
            )
            # Hide SSH buttons on error
            self.main_window.ssh_disco_button.setVisible(False)
            self.main_window.unbind_all_button.setVisible(False)
            self.main_window.usbipd_service_button.setVisible(False)
            self.main_window.linux_usbip_service_button.setVisible(False)
        finally:
            # Re-enable sorting after table population is complete
            self.main_window.remote_table.setSortingEnabled(True)

    def toggle_bind_remote(
        self, ip, username, password, busid, desc, accept_fingerprint, state
    ):
        """Toggle bind/unbind state for remote device"""
        # Validate busid format for security
        if not SecurityValidator.validate_busid(busid):
            self.main_window.append_simple_message(
                f"❌ Invalid device ID format: {busid}"
            )
            self.main_window.append_verbose_message(f"Invalid busid format: {busid}\n")
            # Re-enable buttons after validation failure
            self.main_window.enable_all_device_buttons()
            return

        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=15)

            # Get appropriate command based on remote OS type
            if state == 2:  # Checked (Bind)
                if self.remote_os_type == "windows" and self.remote_has_usbipd:
                    # Windows usbipd command
                    actual_cmd = RemoteOSDetector.get_remote_usbip_bind_command(
                        self.remote_os_type, busid, self.remote_has_usbipd
                    )
                    safe_cmd = (
                        actual_cmd  # No password hiding needed for Windows usbipd
                    )
                else:
                    # Linux/Unix system - use sudo with password
                    sudo_password = password
                    actual_cmd = SecureCommandBuilder.build_usbip_bind_command(
                        busid, sudo_password, remote_execution=True
                    )
                    safe_cmd = f"echo [HIDDEN] | sudo -S usbip bind -b {SecurityValidator.sanitize_for_shell(busid)}"

            elif state == 0:  # Unchecked (Unbind)
                if self.remote_os_type == "windows" and self.remote_has_usbipd:
                    # Windows usbipd command
                    actual_cmd = RemoteOSDetector.get_remote_usbip_unbind_command(
                        self.remote_os_type, busid, self.remote_has_usbipd
                    )
                    safe_cmd = (
                        actual_cmd  # No password hiding needed for Windows usbipd
                    )
                else:
                    # Linux/Unix system - use sudo with password
                    sudo_password = password
                    actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(
                        busid, sudo_password, remote_execution=True
                    )
                    safe_cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {SecurityValidator.sanitize_for_shell(busid)}"
            else:
                client.close()
                return

            if not actual_cmd:
                self.main_window.console.append(
                    f"Failed to build secure command for busid: {busid}\n"
                )
                client.close()
                return

            stdin, stdout, stderr = client.exec_command(actual_cmd)
            output = self.main_window.filter_sudo_prompts(
                stdout.read().decode() + stderr.read().decode()
            )
            self.main_window.append_verbose_message(f"SSH $ {safe_cmd}\n")
            if output:
                self.main_window.append_verbose_message(
                    f"{SecurityValidator.sanitize_console_output(output)}\n"
                )

            client.close()

            # Save the remote bind state after successful operation
            if state == 2:  # Bind operation
                self.main_window.save_remote_state(ip, busid, True)

                # Store Windows device description for later use (to fix "unknown product" issue)
                if self.remote_os_type == "windows" and self.remote_has_usbipd:
                    self.main_window.save_windows_device_description(ip, busid, desc)
                    self.main_window.append_simple_message(
                        f"✅ Device '{desc}' bound successfully (Windows usbipd)"
                    )

                    # Windows-specific: Add delay after bind to allow device to become available for attach
                    self.main_window.append_simple_message(
                        "⏳ Waiting for Windows usbipd to export device..."
                    )
                    time.sleep(
                        2.0
                    )  # 2 second delay for Windows to properly export the device
                    self.main_window.append_simple_message(
                        "✅ Device ready for attachment"
                    )
                else:
                    self.main_window.append_simple_message(
                        f"✅ Device '{desc}' bound successfully"
                    )
                # Update sorting item
                self.main_window.update_remote_table_sorting_items(busid, bound=True)
            elif state == 0:  # Unbind operation
                self.main_window.save_remote_state(ip, busid, False)
                if self.remote_os_type == "windows" and self.remote_has_usbipd:
                    self.main_window.append_simple_message(
                        f"✅ Device '{desc}' unbound successfully (Windows usbipd)"
                    )
                else:
                    self.main_window.append_simple_message(
                        f"✅ Device '{desc}' unbound successfully"
                    )
                # Update sorting item
                self.main_window.update_remote_table_sorting_items(busid, bound=False)

            # Start grace period to prevent auto-reconnect interference
            self.main_window.start_grace_period()

            self.main_window.device_management_controller.load_devices()  # Only refresh local table

            # Re-enable all buttons after successful operation
            self.main_window.enable_all_device_buttons()
        except Exception as e:
            error_msg = "❌ SSH bind/unbind failed: Connection or authentication error"
            if self.remote_os_type == "windows" and not self.remote_has_usbipd:
                error_msg += " (usbipd service may not be running)"
            self.main_window.append_simple_message(error_msg)

            # Re-enable all buttons after failed operation
            self.main_window.enable_all_device_buttons()

    def perform_remote_bind(
        self, ip, username, password, busid, accept_fingerprint, bind=True
    ):
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

            # Use SSH password as sudo password for remote Linux commands
            sudo_password = password

            if bind:
                actual_cmd = SecureCommandBuilder.build_usbip_bind_command(
                    busid, sudo_password, remote_execution=True
                )
            else:
                actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(
                    busid, sudo_password, remote_execution=True
                )

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

    def parse_usbipd_list(self, output):
        """Parse Windows usbipd list output and return list of devices"""
        devices = []
        lines = output.splitlines()

        # Look for the "Connected:" section and process device entries
        in_connected_section = False
        for line in lines:
            line = line.strip()

            # Check for section headers
            if line.startswith("Connected:"):
                in_connected_section = True
                continue
            elif line.startswith("Persisted:") or line.startswith("GUID"):
                in_connected_section = False
                continue

            # Skip empty lines and headers
            if not line or line.startswith("-") or line.startswith("BUSID"):
                continue

            # Only process lines in the Connected section
            if in_connected_section and line:
                # Windows usbipd format: BUSID  VID:PID    DEVICE                                          STATE
                # Example: 3-1    32ac:0002  HDMI Expansion Card, USB Input Device                         Not shared
                parts = line.split(None, 3)  # Split into max 4 parts
                if len(parts) >= 3:
                    busid = parts[0]
                    vid_pid = parts[1] if len(parts) > 1 else ""

                    # Handle device name and state - device name might contain commas and spaces
                    remaining = line[len(busid) :].strip()
                    remaining = (
                        remaining[len(vid_pid) :].strip() if vid_pid else remaining
                    )

                    # Split by multiple spaces to separate device name from state
                    import re

                    parts_remaining = re.split(r"\s{2,}", remaining)
                    device_name = (
                        parts_remaining[0] if parts_remaining else "Unknown Device"
                    )

                    # Combine VID:PID with device name for description
                    if vid_pid and ":" in vid_pid:
                        desc = f"{device_name} ({vid_pid})"
                    else:
                        desc = device_name

                    # Store Windows device description for later use (to fix "unknown product" issue)
                    ip = self.main_window.ip_input.currentText()
                    if ip:
                        self.main_window.save_windows_device_description(
                            ip, busid, desc
                        )

                    devices.append({"busid": busid, "desc": desc})

        return devices

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

                states[busid] = {"bound": is_bound, "auto": auto_enabled}

                # Save bind state to persistent storage
                self.main_window.save_remote_state(ip, busid, is_bound)

                # Save auto-reconnect state using the silent method (no console output)
                self.main_window.data_persistence_controller.set_auto_reconnect_state_silent(
                    ip, busid, auto_enabled, "remote"
                )

                saved_count += 1
                self.main_window.console.append(
                    f"  Saving {busid}: bind={is_bound}, auto={auto_enabled}"
                )

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
                auto_enabled = self.main_window.get_auto_reconnect_state(
                    ip, busid, "remote"
                )
                auto_btn.blockSignals(True)
                auto_btn.setChecked(auto_enabled)
                auto_btn.blockSignals(False)

                restored_count += 1
                self.main_window.console.append(
                    f"  Device {busid}: bind={is_bound}, auto={auto_enabled}"
                )

        self.main_window.console.append(
            f"  Restored {restored_count} device states total"
        )

    def load_ssh_state(self):
        """Load SSH state from encrypted file"""
        return self.main_window.file_crypto.load_encrypted_file("ssh_state.enc")

    def save_ssh_state(self, ip, username, accept_fingerprint):
        """Save SSH state to encrypted file"""
        state = self.load_ssh_state()
        state[ip] = {"username": username, "accept_fingerprint": accept_fingerprint}
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
        if hasattr(self.main_window, "ssh_client"):
            self.main_window.ssh_client = None

        self.main_window.remote_table.setRowCount(0)

        # Hide SSH-related buttons
        self.main_window.ssh_disco_button.setVisible(False)
        self.main_window.unbind_all_button.setVisible(False)
        self.main_window.usbipd_service_button.setVisible(False)
        self.main_window.linux_usbip_service_button.setVisible(False)

    def refresh_with_saved_credentials(self):
        """Refresh remote devices using previously saved SSH credentials"""
        # If you want to use last SSH credentials, store them after successful SSH login
        if (
            hasattr(self.main_window, "last_ssh_username")
            and hasattr(self.main_window, "last_ssh_password")
            and hasattr(self.main_window, "last_ssh_accept")
        ):

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
                        auto_state = self.main_window.get_auto_reconnect_state(
                            ip, busid, "remote"
                        )
                        auto_reconnect_states[busid] = auto_state

                # Now refresh the UI
                self.load_remote_local_devices(
                    self.main_window.last_ssh_username,
                    self.main_window.last_ssh_password,
                    self.main_window.last_ssh_accept,
                )

                # The load_remote_local_devices should now correctly restore from persistent storage
                self.main_window.append_simple_message(
                    "🔄 Refresh: UI refreshed with persistent state data"
                )
