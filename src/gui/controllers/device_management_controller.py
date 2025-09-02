"""Device management controller for handling USB/IP device operations."""

import subprocess
import time
import platform
from PyQt6.QtCore import QObject
from gui.widgets.toggle_button import ToggleButton
from security.validator import SecurityValidator
from utils.admin_utils import get_platform_usbip_port_command, is_windows_usbipd_available


class DeviceManagementController(QObject):
    """Controller for handling USB/IP device management operations."""
    
    def get_subprocess_creation_flags(self):
        """Get subprocess creation flags to hide console windows on Windows"""
        if platform.system() == "Windows":
            return subprocess.CREATE_NO_WINDOW
        return 0
    
    def __init__(self, main_window):
        """
        Initialize the device management controller.
        
        Args:
            main_window: Reference to the main window instance
        """
        super().__init__()
        self.main_window = main_window
        
    def safe_toggle_attach(self, ip, busid, desc, state):
        """Safely toggle attach with immediate button disabling"""
        # Immediately disable all buttons to prevent race conditions
        self.main_window.disable_all_device_buttons()
        # Call the actual toggle method
        self.toggle_attach(ip, busid, desc, state)
        
    def safe_detach_local_device(self, port, desc, state):
        """Safely detach local device with immediate button disabling"""
        # Immediately disable all buttons to prevent race conditions
        self.main_window.disable_all_device_buttons()
        # Call the actual detach method
        self.detach_local_device(port, desc, state)
        
    def attach_all_devices(self):
        """Attach all detached devices."""
        ip = self.main_window.ip_input.currentText()
        if not ip:
            self.main_window.append_simple_message("❌ No IP selected for Attach All")
            return
        
        attached_count = 0
        failed_count = 0
        for row in range(self.main_window.device_table.rowCount()):
            toggle_btn = self.main_window.device_table.cellWidget(row, 2)
            busid_item = self.main_window.device_table.item(row, 0)
            desc_item = self.main_window.device_table.item(row, 1)
            if toggle_btn and not toggle_btn.isChecked() and busid_item and desc_item:
                # Only attach if not checked
                busid = busid_item.text().strip()  # Strip whitespace
                desc = desc_item.text()
                # Actually perform the attachment
                success = self.toggle_attach(ip, busid, desc, 2, start_grace_period=False)  # 2 = checked/attached state
                if success:
                    attached_count += 1
                else:
                    failed_count += 1
        
        # Provide detailed feedback
        if attached_count > 0:
            self.main_window.append_simple_message(f"✅ Successfully attached {attached_count} devices")
        if failed_count > 0:
            self.main_window.append_simple_message(f"❌ Failed to attach {failed_count} devices")
        if attached_count > 0:
            self.main_window.append_simple_message("🔄 Refreshing device list...")
            # Add a small delay to allow usbip commands to complete
            time.sleep(0.5)
        
        # Refresh the device table to show updated states
        self.load_devices()
        
        # Start grace period to prevent immediate auto-reconnect after attach all
        if attached_count > 0:
            self.main_window.start_grace_period()  # Use default grace period duration

    def detach_all_devices(self):
        """Detach all attached devices."""
        detached_count = 0
        failed_count = 0
        for row in range(self.main_window.device_table.rowCount()):
            toggle_btn = self.main_window.device_table.cellWidget(row, 2)
            busid_item = self.main_window.device_table.item(row, 0)
            desc_item = self.main_window.device_table.item(row, 1)
            if toggle_btn and toggle_btn.isChecked() and busid_item and desc_item:
                # Only detach if checked
                busid = busid_item.text().strip()  # Strip whitespace
                desc = desc_item.text()
                # Actually perform the detachment
                success = self.toggle_attach("", busid, desc, 0, start_grace_period=False)  # 0 = unchecked/detached state
                if success:
                    detached_count += 1
                else:
                    failed_count += 1
        
        # Provide detailed feedback
        if detached_count > 0:
            self.main_window.append_simple_message(f"✅ Successfully detached {detached_count} devices")
        if failed_count > 0:
            self.main_window.append_simple_message(f"❌ Failed to detach {failed_count} devices")
        if detached_count > 0:
            self.main_window.append_simple_message("🔄 Refreshing device list...")
            # Add a small delay to allow usbip commands to complete
            time.sleep(0.5)
        
        # Refresh the device table to show updated states
        self.load_devices()
        
        # Start grace period to prevent immediate auto-reconnect
        if detached_count > 0:
            self.main_window.start_grace_period()  # Use default grace period duration

    def unbind_all_devices(self):
        """Unbind all bound devices on the remote SSH server and refresh tables"""
        ip = self.main_window.ip_input.currentText()
        username = getattr(self.main_window, "last_ssh_username", "")
        password = getattr(self.main_window, "last_ssh_password", "")
        accept = getattr(self.main_window, "last_ssh_accept", False)
        
        if not ip or not username or not password:
            self.main_window.append_simple_message("❌ Missing SSH credentials for Unbind All")
            return
        
        # Check rate limiting
        allowed, remaining_time = self.main_window.connection_security.check_ssh_connection_allowed(ip)
        if not allowed:
            self.main_window.append_simple_message(f"⏳ Too many SSH attempts. Try again in {remaining_time} seconds")
            return
            
        try:
            import paramiko
            from security.validator import SecurityValidator, SecureCommandBuilder
            from utils.remote_os_detector import RemoteOSDetector
            
            self.main_window.connection_security.record_ssh_attempt(ip)
            client = paramiko.SSHClient()
            if accept:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            client.connect(ip, username=username, password=password, timeout=10)
            
            # Get remote OS type from SSH controller if available
            remote_os_type = getattr(self.main_window.ssh_management_controller, 'remote_os_type', 'linux')
            remote_has_usbipd = getattr(self.main_window.ssh_management_controller, 'remote_has_usbipd', False)
            
            # Unbind all bound devices
            for row in range(self.main_window.remote_table.rowCount()):
                toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
                busid_item = self.main_window.remote_table.item(row, 0)
                if toggle_btn and toggle_btn.isChecked() and busid_item:
                    busid = busid_item.text().strip()  # Strip whitespace
                    
                    # Validate busid format for security
                    if not SecurityValidator.validate_busid(busid):
                        self.main_window.console.append(f"Invalid busid format: {busid}\n")
                        continue
                    
                    # Use appropriate command based on remote OS type
                    if remote_os_type == 'windows' and remote_has_usbipd:
                        # Windows usbipd command
                        actual_cmd = RemoteOSDetector.get_remote_usbip_unbind_command(
                            remote_os_type, busid, remote_has_usbipd
                        )
                        safe_cmd = actual_cmd  # No password hiding needed for Windows usbipd
                    else:
                        # Linux/Unix system - use sudo with password
                        actual_cmd = SecureCommandBuilder.build_usbip_unbind_command(busid, password, remote_execution=True)
                        safe_cmd = f"echo [HIDDEN] | sudo -S usbip unbind -b {SecurityValidator.sanitize_for_shell(busid)}"
                    
                    if not actual_cmd:
                        self.main_window.console.append(f"Failed to build secure command for busid: {busid}\n")
                        continue
                    
                    stdin, stdout, stderr = client.exec_command(actual_cmd)
                    output = self.main_window.filter_sudo_prompts(stdout.read().decode() + stderr.read().decode())
                    self.main_window.append_verbose_message(f"SSH $ {safe_cmd}\n")
                    if output:
                        self.main_window.append_verbose_message(f"{SecurityValidator.sanitize_console_output(output)}\n")
            
            client.close()
            if remote_os_type == 'windows' and remote_has_usbipd:
                self.main_window.append_simple_message("✅ All devices unbound successfully (Windows usbipd)")
            else:
                self.main_window.append_simple_message("✅ All devices unbound successfully")
            
            # Update toggle buttons and save states to persistent storage
            for row in range(self.main_window.remote_table.rowCount()):
                toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
                busid_item = self.main_window.remote_table.item(row, 0)
                if toggle_btn and toggle_btn.isChecked() and busid_item:
                    busid = busid_item.text()
                    # Block signals to prevent triggering bind/unbind operations
                    toggle_btn.blockSignals(True)
                    toggle_btn.setChecked(False)  # Set to unbound state
                    toggle_btn.blockSignals(False)
                    # Save the unbound state to persistent storage
                    self.main_window.save_remote_state(ip, busid, False)
            
            # Refresh only the local devices table to show available devices
            self.load_devices()
            
            # Start grace period to prevent immediate auto-reconnect
            self.main_window.start_grace_period()  # Use default grace period duration
            
        except Exception as e:
            self.main_window.console.append(f"Error unbinding all devices: {e}\n")

    def load_devices(self):
        """Load and display USB/IP devices from remote server."""
        # Save auto-reconnect states before clearing the table
        saved_auto_states = {}
        ip = self.main_window.ip_input.currentText()
        if ip:
            for row in range(self.main_window.device_table.rowCount()):
                busid_item = self.main_window.device_table.item(row, 0)
                auto_btn = self.main_window.device_table.cellWidget(row, 3)
                if busid_item and auto_btn and hasattr(auto_btn, 'isChecked'):
                    busid = busid_item.text()
                    # Only save if it's not a "Port" entry and has a real auto state
                    if not busid.startswith("Port") and auto_btn.isEnabled():
                        auto_state = auto_btn.isChecked()
                        saved_auto_states[busid] = auto_state
        
        # Disable sorting during table population to prevent widget issues
        self.main_window.device_table.setSortingEnabled(False)
        
        self.main_window.device_table.setRowCount(0)
        ip = self.main_window.ip_input.currentText()
        if not ip:
            # Re-enable sorting before returning
            self.main_window.device_table.setSortingEnabled(True)
            return
            
        try:
            # Get list of attached busids from platform-appropriate command
            port_output = ""  # Initialize for both branches
            
            if platform.system() == "Windows":
                if not is_windows_usbipd_available():
                    self.main_window.append_simple_message("⚠️ USB/IP client tools not available. Please install usbip for Windows.")
                    return
                
                port_cmd = get_platform_usbip_port_command()
                port_result = subprocess.run(
                    port_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    creationflags=self.get_subprocess_creation_flags()
                )
                
                # Parse usbip port output (same format on Windows and Unix)
                port_output = port_result.stdout
                attached_busids = set()
                attached_descs = set()
                current_port = None
                current_busid = None
                for line in port_output.splitlines():
                    line = line.strip()
                    if line.startswith("Port"):
                        current_port = line.split()[1].replace(":", "")
                        current_busid = None
                    elif platform.system() == "Windows":
                        # Windows-specific parsing: extract busid from usbip URL
                        if current_port and line.startswith("-> usbip://") and "/" in line:
                            # Extract busid from usbip URL format: -> usbip://192.168.2.184:3240/3-2.3
                            busid_part = line.split("/")[-1]  # Get the part after the last /
                            if busid_part and "-" in busid_part:
                                attached_busids.add(busid_part)
                                current_busid = busid_part
                        elif current_port and line and ":" in line and not line.startswith("->"):
                            # This is a description line
                            desc = line.strip()
                            attached_descs.add(desc)
                    else:
                        # Linux-specific parsing: use description matching (original logic)
                        if current_port and line and line[0].isdigit() and '-' in line:
                            current_busid = line.split()[0]
                            attached_busids.add(current_busid)
                        elif current_port and current_busid and line and ":" in line:
                            desc = line
                            attached_descs.add(desc)
                        elif current_port and line and ":" in line and not line.startswith("Port"):
                            # Linux: Just description line without busid
                            desc = line.strip()
                            attached_descs.add(desc)
                
            else:
                # Unix-like systems - use description matching approach
                port_result = subprocess.run(
                    ["usbip", "port"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,  # 10 second timeout
                    creationflags=self.get_subprocess_creation_flags()
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
                    elif current_port and line and ":" in line and not line.startswith("Port"):
                        # Linux: Description line without explicit busid in port output
                        desc = line.strip()
                        attached_descs.add(desc)
                        # For Linux, we'll rely on description matching rather than busid extraction

            # List remote devices
            result = subprocess.run(
                ["usbip", "list", "-r", ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,  # 15 second timeout for remote connections
                creationflags=self.get_subprocess_creation_flags()
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            self.main_window.append_verbose_message(f"$ usbip list -r {ip}\n{output}\n")
            devices = self.parse_usbip_list(output)

            # Add remote devices
            self._add_remote_devices(devices, ip, attached_descs, attached_busids, saved_auto_states)
            
            # Add devices that are attached but no longer in remote list (using mappings)
            self._add_mapped_devices(ip, attached_busids, attached_descs, saved_auto_states)
            
            # List locally attached devices (usbip port) that aren't in the remote list
            self._add_local_attached_devices(port_output, ip, saved_auto_states)
            
        except subprocess.TimeoutExpired:
            self.main_window.append_simple_message(f"⏱️ Timeout connecting to {ip} - Check if IP is correct and usbip daemon is running")
            self.main_window.append_verbose_message(f"Timeout occurred while connecting to {ip}. The IP may not have a usbip daemon running.\n")
        except Exception as e:
            self.main_window.append_simple_message(f"❌ Error loading devices from {ip}: {str(e)}")
            self.main_window.append_verbose_message(f"Error loading devices: {e}\n")
        finally:
            # Re-enable sorting after table population is complete
            self.main_window.device_table.setSortingEnabled(True)

    def _add_remote_devices(self, devices, ip, attached_descs, attached_busids, saved_auto_states):
        """Add remote devices to the device table."""
        for dev in devices:
            row = self.main_window.device_table.rowCount()
            self.main_window.device_table.insertRow(row)
            # Strip whitespace from busid when storing in table
            clean_busid = dev["busid"].strip()
            self.main_window.device_table.setItem(row, 0, self.main_window.create_table_item_with_tooltip(clean_busid))
            self.main_window.device_table.setItem(row, 1, self.main_window.create_table_item_with_tooltip(dev["desc"]))
            
            # Create toggle button instead of checkbox
            toggle_btn = ToggleButton("ATTACHED", "DETACHED")
            
            # Set initial state WITHOUT triggering signal
            toggle_btn.blockSignals(True)
            # Use busid matching instead of description matching for more reliable state detection
            is_attached = clean_busid in attached_busids
            toggle_btn.setChecked(is_attached)
            toggle_btn.blockSignals(False)
            
            # Now connect the signal handler - use clean busid
            toggle_btn.toggled.connect(
                lambda state, ip=ip, busid=clean_busid, desc=dev["desc"]: self.safe_toggle_attach(ip, busid, desc, 2 if state else 0)
            )
            self.main_window.device_table.setCellWidget(row, 2, toggle_btn)
            
            # Create auto-reconnect toggle button
            auto_btn = ToggleButton("AUTO", "MANUAL")
            
            # Set initial state WITHOUT triggering signal
            auto_btn.blockSignals(True)
            # Use saved state if available, otherwise read from encrypted file
            if dev["busid"] in saved_auto_states:
                auto_state = saved_auto_states[dev["busid"]]
                auto_btn.setChecked(auto_state)
            else:
                auto_state = self.main_window.get_auto_reconnect_state(ip, dev["busid"], "local")
                auto_btn.setChecked(auto_state)
            auto_btn.blockSignals(False)
            
            # Now connect the signal handler
            auto_btn.toggled.connect(
                lambda state, ip=ip, busid=dev["busid"]: self.main_window.toggle_auto_reconnect(ip, busid, state, "local")
            )
            self.main_window.device_table.setCellWidget(row, 3, auto_btn)

    def _add_mapped_devices(self, ip, attached_busids, attached_descs, saved_auto_states):
        """Add devices that are attached but no longer in remote list (using mappings)."""
        data = self.main_window.file_crypto.load_encrypted_file("device_mapping.enc")
        mappings = data.get('mappings', {})
        
        for remote_busid, mapping_info in mappings.items():
            port_busid = mapping_info.get('port_busid')
            
            # Check if this mapped device is currently attached
            # On Windows: use busid matching, on Linux: use description matching from attached_descs
            if platform.system() == "Windows":
                is_attached = port_busid in attached_busids
            else:
                # On Linux, check if the description is in attached_descs
                remote_desc = mapping_info.get('remote_desc', '')
                is_attached = any(remote_desc in desc or desc in remote_desc for desc in attached_descs)
            
            if is_attached:
                # This device is attached but not in remote list - add it
                remote_desc = mapping_info.get('remote_desc', 'Unknown Device')
                
                # Check if we already added this device from the remote list
                already_in_table = False
                for row in range(self.main_window.device_table.rowCount()):
                    busid_item = self.main_window.device_table.item(row, 0)
                    if busid_item and busid_item.text() == remote_busid:
                        already_in_table = True
                        break
                
                if not already_in_table:
                    row = self.main_window.device_table.rowCount()
                    self.main_window.device_table.insertRow(row)
                    self.main_window.device_table.setItem(row, 0, self.main_window.create_table_item_with_tooltip(remote_busid))
                    self.main_window.device_table.setItem(row, 1, self.main_window.create_table_item_with_tooltip(remote_desc))
                    
                    # Create toggle button (attached state)
                    toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                    
                    # Set initial state WITHOUT triggering signal
                    toggle_btn.blockSignals(True)
                    toggle_btn.setChecked(True)  # It's attached
                    toggle_btn.blockSignals(False)
                    
                    # Now connect the signal handler
                    toggle_btn.toggled.connect(
                        lambda state, ip=ip, busid=remote_busid, desc=remote_desc: self.toggle_attach(ip, busid, desc, 2 if state else 0)
                    )
                    self.main_window.device_table.setCellWidget(row, 2, toggle_btn)
                    
                    # Create auto-reconnect toggle button with preserved state
                    auto_btn = ToggleButton("AUTO", "MANUAL")
                    
                    # Set initial state WITHOUT triggering signal
                    auto_btn.blockSignals(True)
                    if remote_busid in saved_auto_states:
                        auto_state = saved_auto_states[remote_busid]
                        auto_btn.setChecked(auto_state)
                    else:
                        auto_state = self.main_window.get_auto_reconnect_state(ip, remote_busid, "local")
                        auto_btn.setChecked(auto_state)
                    auto_btn.blockSignals(False)
                    
                    # Now connect the signal handler
                    auto_btn.toggled.connect(
                        lambda state, ip=ip, busid=remote_busid: self.main_window.toggle_auto_reconnect(ip, busid, state, "local")
                    )
                    self.main_window.device_table.setCellWidget(row, 3, auto_btn)

    def _add_local_attached_devices(self, port_output, ip, saved_auto_states):
        """Add locally attached devices that aren't in the remote list."""
        # Build set of descriptions and busids already added to the table
        table_descs = set()
        table_busids = set()
        for row in range(self.main_window.device_table.rowCount()):
            desc_item = self.main_window.device_table.item(row, 1)
            busid_item = self.main_window.device_table.item(row, 0)
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
                
                # Check if this is a Windows "unknown product" and we have a stored description
                ip = self.main_window.ip_input.currentText()
                self.main_window.append_verbose_message(f"🔍 Local device debug - Port: {current_port}, Busid: {current_busid}, Desc: '{desc}'")
                
                if "unknown product" in desc.lower() and ip:
                    # Try to get the remote busid for this port to look up the Windows description
                    remote_busid = self.main_window.get_remote_busid_for_port(current_busid)
                    self.main_window.append_verbose_message(f"🔍 Found 'unknown product', looking up remote busid for {current_busid}: {remote_busid}")
                    
                    if remote_busid:
                        stored_desc = self.main_window.get_windows_device_description(ip, remote_busid)
                        self.main_window.append_verbose_message(f"🔍 Stored description for {remote_busid}: '{stored_desc}'")
                        
                        if stored_desc:
                            # Use the stored Windows description instead of "unknown product"
                            desc = stored_desc
                            self.main_window.append_verbose_message(f"🪟 Using stored Windows description for local device {current_busid}: {desc}")
                    else:
                        self.main_window.append_verbose_message(f"🔍 No remote busid mapping found for {current_busid}")
                else:
                    if "unknown product" not in desc.lower():
                        self.main_window.append_verbose_message(f"🔍 'unknown product' not found in desc: '{desc.lower()}'")
                    if not ip:
                        self.main_window.append_verbose_message(f"🔍 No IP address available")
                
                # Check if this device is already in the table (by busid or mapping)
                remote_busid = self.main_window.get_remote_busid_for_port(current_busid)
                
                # Skip if already in table (either by port busid or remote busid)
                already_in_table = (current_busid in table_busids or 
                                  (remote_busid and remote_busid in table_busids))
                
                if not already_in_table:
                    row = self.main_window.device_table.rowCount()
                    self.main_window.device_table.insertRow(row)
                    self.main_window.device_table.setItem(row, 0, self.main_window.create_table_item_with_tooltip(f"Port {current_port}"))
                    self.main_window.device_table.setItem(row, 1, self.main_window.create_table_item_with_tooltip(desc))
                    
                    # Create toggle button for local devices
                    toggle_btn = ToggleButton("ATTACHED", "DETACHED")
                    
                    # Set initial state WITHOUT triggering signal
                    toggle_btn.blockSignals(True)
                    toggle_btn.setChecked(True)  # Local devices are already attached
                    toggle_btn.blockSignals(False)
                    
                    # Now connect the signal handler
                    toggle_btn.toggled.connect(
                        lambda state, port=current_port, desc=desc: self.safe_detach_local_device(port, desc, 0 if not state else 2)
                    )
                    self.main_window.device_table.setCellWidget(row, 2, toggle_btn)
                    
                    # Create auto-reconnect toggle using the original remote busid if available
                    auto_btn = ToggleButton("AUTO", "MANUAL")
                    busid_for_auto = remote_busid if remote_busid else current_busid
                    
                    # Set initial state WITHOUT triggering signal
                    auto_btn.blockSignals(True)
                    # Use saved state if available, otherwise read from encrypted file
                    if busid_for_auto in saved_auto_states:
                        auto_state = saved_auto_states[busid_for_auto]
                        auto_btn.setChecked(auto_state)
                    else:
                        auto_state = self.main_window.get_auto_reconnect_state(ip, busid_for_auto, "local")
                        auto_btn.setChecked(auto_state)
                    auto_btn.blockSignals(False)
                    
                    # Now connect the signal handler
                    auto_btn.toggled.connect(
                        lambda state, ip=ip, busid=busid_for_auto: self.main_window.toggle_auto_reconnect(ip, busid, state, "local")
                    )
                    self.main_window.device_table.setCellWidget(row, 3, auto_btn)

    def detach_local_device(self, port, desc, state):
        """Detach a local device by port."""
        if state == 0:  # Unchecked (Detach)
            cmd = ["usbip", "detach", "-p", port]
            self.main_window.console.append(f"$ sudo {' '.join(cmd)}\n")
            result = self.main_window.run_sudo(cmd)
            if not result:
                self.main_window.console.append("Detach command failed or returned no output.\n")

    def toggle_attach(self, ip, busid, desc, state, start_grace_period=True):
        """Toggle device attach/detach state.
        
        Args:
            ip: IP address for remote server
            busid: Device bus ID
            desc: Device description
            state: 0 for detach, 2 for attach
            start_grace_period: Whether to start grace period after operation (default True)
        """
        # Clean up any whitespace from busid
        busid = busid.strip()
        
        if state == 2:  # Checked (Attach)
            # Attach device locally (device should already be bound on remote server)
            cmd = ["usbip", "attach", "-r", ip, "-b", busid]
            if platform.system() == "Windows":
                self.main_window.append_verbose_message(f"$ {' '.join(cmd)}\n")
            else:
                self.main_window.append_verbose_message(f"$ sudo {' '.join(cmd)}\n")
            
            result = self.main_window.run_sudo(cmd)
            if not result or result.returncode != 0:
                self.main_window.append_simple_message(f"❌ Failed to attach device {desc}")
                if result:
                    self.main_window.append_verbose_message(f"Attach command failed with exit code {result.returncode}\n")
                    if result.stderr:
                        self.main_window.append_verbose_message(f"Error: {result.stderr.strip()}\n")
                else:
                    self.main_window.append_verbose_message("Attach command failed or returned no output.\n")
                return False
            
            # Check if attach was actually successful by looking for success message
            success_detected = False
            if result.stdout and ("successfully attached" in result.stdout.lower() or "succesfully attached" in result.stdout.lower()):
                success_detected = True
            elif result.stderr and ("successfully attached" in result.stderr.lower() or "succesfully attached" in result.stderr.lower()):
                success_detected = True
            
            if not success_detected:
                self.main_window.append_simple_message(f"❌ Device {desc} attach may have failed - no success confirmation")
                self.main_window.append_verbose_message("No 'successfully attached' message found in command output.\n")
                # Don't return False here - continue and check port list
            
            # After successful attach, find which port it was assigned to
            time.sleep(0.5)  # Give time for device to appear in port list
            port_cmd = get_platform_usbip_port_command()
            port_result = subprocess.run(
                port_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,  # 10 second timeout
                creationflags=self.get_subprocess_creation_flags()
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
                elif platform.system() == "Windows":
                    # Windows-specific mapping creation
                    if current_port and line and ":" in line and not line.startswith("->"):
                        # This is a description line
                        port_desc = line
                    elif current_port and line.startswith("-> usbip://") and "/" in line:
                        # Extract busid from usbip URL format: -> usbip://192.168.2.184:3240/3-2.3
                        port_busid = line.split("/")[-1]  # Get the part after the last /
                        
                        # Now we have all info - check if this matches our target device
                        if port_desc:
                            if desc in port_desc or desc.split("(")[0].strip() in port_desc:
                                # Found the device - save the mapping
                                self.main_window.save_device_mapping(busid, desc, current_port, port_busid)
                                break
                else:
                    # Linux-specific mapping creation (description-based)
                    if current_port and line and ":" in line and not line.startswith("Port"):
                        # Linux: Just description line, use description for mapping
                        port_desc = line.strip()
                        
                        # For Linux, we match by description and use description as "busid"
                        if desc in port_desc or desc.split("(")[0].strip() in port_desc:
                            # Found the device - save mapping using description as identifier
                            self.main_window.save_device_mapping(busid, desc, current_port, port_desc)
                            break
            
            self.main_window.save_state(ip, busid, True)
            self.main_window.append_simple_message(f"✅ Device '{desc}' attached successfully")
            
            # Add a small delay before refreshing to ensure mapping is properly saved
            time.sleep(1.0)
            
            self.load_devices()  # Refresh device list after successful attach
            if start_grace_period:
                self.main_window.start_grace_period()  # Prevent auto-refresh interference
            
            # Windows-specific: Add extra delay after attach to prevent kernel conflicts
            if platform.system() == "Windows":
                self.main_window.append_simple_message("⏳ Waiting for Windows USB subsystem to stabilize...")
                time.sleep(5.0)  # 5 seconds for Windows to fully process USB connection
                self.main_window.append_simple_message("✅ USB subsystem ready - operations unlocked")
            
            # Re-enable all buttons after successful attach
            self.main_window.enable_all_device_buttons()
            return True
        elif state == 0:  # Unchecked (Detach)
            # Get the stored port mapping for this device
            device_mapping = self.main_window.get_device_mapping(busid)
            port_num = None
            
            if device_mapping:
                # Use stored port number from mapping
                port_num = device_mapping.get('port_number')
                self.main_window.append_verbose_message(f"🔗 Found stored mapping for {busid}: port {port_num}")
            else:
                # Fallback: try to find the port by parsing current port output
                self.main_window.append_verbose_message(f"⚠️ No stored mapping found for {busid}, attempting port detection...")
                port_cmd = get_platform_usbip_port_command()
                port_result = subprocess.run(
                    port_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,  # 10 second timeout
                    creationflags=self.get_subprocess_creation_flags()
                )
                port_output = port_result.stdout
                current_port = None
                for line in port_output.splitlines():
                    line = line.strip()
                    if line.startswith("Port"):
                        current_port = line.split()[1].replace(":", "")
                    # For Windows: also try matching by VID:PID from the description
                    elif current_port and line:
                        # Extract VID:PID from description if present
                        if "(" in desc and ":" in desc:
                            vid_pid = desc.split("(")[-1].split(")")[0]
                            if ":" in vid_pid and vid_pid.lower() in line.lower():
                                port_num = current_port
                                self.main_window.append_verbose_message(f"🔍 Matched by VID:PID {vid_pid} to port {port_num}")
                                break
                        # Fallback: try partial description match
                        if desc in line or desc.split("(")[0].strip() in line:
                            port_num = current_port
                            self.main_window.append_verbose_message(f"🔍 Matched by description to port {port_num}")
                            break
            if port_num:
                cmd = ["usbip", "detach", "-p", port_num]
                if platform.system() == "Windows":
                    self.main_window.append_verbose_message(f"$ {' '.join(cmd)}\n")
                else:
                    self.main_window.append_verbose_message(f"$ sudo {' '.join(cmd)}\n")
                result = self.main_window.run_sudo(cmd)
                if not result:
                    self.main_window.append_simple_message(f"❌ Failed to detach device '{desc}'")
                    self.main_window.append_verbose_message("Detach command failed or returned no output.\n")
                    
                    # Re-enable all buttons after failed detach
                    self.main_window.enable_all_device_buttons()
                    return False
                
                # Remove device mapping after successful detach
                self.main_window.remove_device_mapping(busid)
                
                self.main_window.save_state(ip, busid, False)
                self.main_window.append_simple_message(f"✅ Device '{desc}' detached successfully")
                self.load_devices()  # Initial refresh after successful detach
                if start_grace_period:
                    self.main_window.start_grace_period()  # Prevent auto-refresh interference
                
                # Small delay to let Windows process the USB detach
                time.sleep(1.0)  # Just 1 second for USB state to update
                
                # Final refresh to ensure device appears in local list
                self.load_devices()
                
                # Re-enable all buttons after successful detach
                self.main_window.enable_all_device_buttons()
                return True
            else:
                self.main_window.append_simple_message(f"❌ Could not find port for device '{desc}'")
                self.main_window.append_verbose_message(f"Could not find port for device '{desc}'\n")
                
                # Re-enable all buttons after failed detach
                self.main_window.enable_all_device_buttons()
                return False

    def parse_usbip_list(self, output):
        """Parse usbip list output to extract device information."""
        devices = []
        lines = output.splitlines()
        ip = self.main_window.ip_input.currentText()
        
        for line in lines:
            line = line.strip()
            # Match lines like: 3-2.1: Razer USA, Ltd : unknown product (1532:0077)
            if line and line[0].isdigit() and ':' in line:
                busid, rest = line.split(':', 1)
                busid = busid.strip()  # Remove any trailing spaces from busid
                desc = rest.strip()
                
                self.main_window.append_verbose_message(f"🔍 Remote device debug - Busid: '{busid}', Desc: '{desc}'")
                
                # Check if this is a Windows "unknown product" and we have a stored description
                if "unknown product" in desc.lower() and ip:
                    stored_desc = self.main_window.get_windows_device_description(ip, busid)
                    self.main_window.append_verbose_message(f"🔍 Found 'unknown product', checking stored desc for {busid}: '{stored_desc}'")
                    
                    if stored_desc:
                        # Use the stored Windows description instead of "unknown product"
                        desc = stored_desc
                        self.main_window.append_verbose_message(f"🪟 Using stored Windows description for {busid}: {desc}")
                    else:
                        self.main_window.append_verbose_message(f"🔍 No stored description found for {busid}")
                else:
                    if "unknown product" not in desc.lower():
                        self.main_window.append_verbose_message(f"🔍 'unknown product' not found in remote desc: '{desc.lower()}'")
                
                devices.append({"busid": busid, "desc": desc})
        return devices

    def auto_refresh_devices(self):
        """Auto-refresh device tables."""
        if not self.main_window.auto_refresh_enabled:
            return
            
        # Skip auto-refresh during grace period to prevent interference
        if hasattr(self.main_window, 'auto_reconnect_grace_period') and self.main_window.auto_reconnect_grace_period:
            return
            
        # Log auto-refresh activity to console
        self.main_window.console.append("Auto-refresh: Updating device tables...\n")
            
        # Use full device refresh to properly handle all device types
        self.load_devices()
        
        # If SSH is connected, also refresh remote devices
        if hasattr(self.main_window, 'last_ssh_username') and self.main_window.last_ssh_username:
            self.main_window.ssh_management_controller.refresh_with_saved_credentials()
            self.main_window.append_simple_message("🔄 Auto-refresh: Updated remote SSH devices")
