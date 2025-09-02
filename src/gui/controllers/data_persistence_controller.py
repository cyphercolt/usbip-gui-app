"""
Data Persistence Controller for USB/IP GUI Application

This controller handles all data storage and retrieval operations including:
- IP address management and persistence
- Device state management (attached/detached states)
- Remote device state tracking
- Auto-reconnect settings and preferences
- Device mapping between remote and local busids
- UI state updates and synchronization
"""

from security.crypto import FileEncryption


class DataPersistenceController:
    """
    Controller for handling all data persistence operations.
    
    Manages encrypted storage and retrieval of:
    - IP addresses and connection history
    - Device attachment states (local and remote)
    - Auto-reconnect settings and configuration
    - Device mappings between remote and local ports
    - SSH connection state and credentials
    - Theme settings and UI preferences
    
    This controller centralizes all file I/O operations to maintain
    clean separation of concerns and ensure data consistency.
    """

    # Constants
    STATE_FILE = "usbip_state.enc"
    SSH_STATE_FILE = "ssh_state.enc"
    IP_LIST_FILE = "ips.enc"
    AUTO_RECONNECT_FILE = "auto_reconnect.enc"
    DEVICE_MAPPING_FILE = "device_mapping.enc"
    WINDOWS_DEVICE_DESCRIPTIONS_FILE = "windows_device_descriptions.enc"
    
    def __init__(self, main_window):
        self.main_window = main_window
        
    # ==================== IP Management ====================
    
    def load_ips(self):
        """Load IP addresses and populate the IP combo box"""
        ip_data = self.main_window.file_crypto.load_encrypted_file(self.IP_LIST_FILE)
        for ip in ip_data.get("ips", []):
            self.main_window.ip_input.addItem(ip)

    def save_ips(self):
        """Save current IP addresses to encrypted file"""
        ips = []
        for i in range(self.main_window.ip_input.count()):
            ips.append(self.main_window.ip_input.itemText(i))
        
        ip_data = {"ips": ips}
        self.main_window.file_crypto.save_encrypted_file(self.IP_LIST_FILE, ip_data)

    def load_state(self, ip):
        """Load device states for a specific IP"""
        all_state = self.main_window.file_crypto.load_encrypted_file(self.STATE_FILE)
        return all_state.get(ip, {"attached": []})

    def save_state(self, ip, busid, attached):
        """Save device state for a specific IP and device"""
        all_state = self.main_window.file_crypto.load_encrypted_file(self.STATE_FILE)
        state = all_state.get(ip, {"attached": []})
        if attached and busid not in state["attached"]:
            state["attached"].append(busid)
        elif not attached and busid in state["attached"]:
            state["attached"].remove(busid)
        all_state[ip] = state
        self.main_window.file_crypto.save_encrypted_file(self.STATE_FILE, all_state)

    def load_remote_state(self, ip):
        """Load remote device bind states for a specific IP"""
        all_state = self.main_window.file_crypto.load_encrypted_file(self.STATE_FILE)
        return all_state.get(ip, {}).get("remote_bound", {})

    def save_remote_state(self, ip, busid, bound):
        """Save remote device bind state for a specific IP and busid"""
        all_state = self.main_window.file_crypto.load_encrypted_file(self.STATE_FILE)
        state = all_state.get(ip, {"attached": [], "remote_bound": {}})
        if "remote_bound" not in state:
            state["remote_bound"] = {}
        state["remote_bound"][busid] = bound
        all_state[ip] = state
        self.main_window.file_crypto.save_encrypted_file(self.STATE_FILE, all_state)

    def load_auto_reconnect_settings(self):
        """Load auto-reconnect and auto-refresh settings from encrypted file"""
        data = self.main_window.file_crypto.load_encrypted_file(self.AUTO_RECONNECT_FILE)
        self.main_window.auto_reconnect_enabled = data.get('auto_reconnect_enabled', True)  # Default to enabled
        self.main_window.auto_reconnect_interval = data.get('interval', 30)
        self.main_window.auto_reconnect_max_attempts = data.get('max_attempts', 5)
        self.main_window.grace_period_duration = data.get('grace_period', 60)
        self.main_window.auto_refresh_enabled = data.get('auto_refresh_enabled', False)
        self.main_window.auto_refresh_interval = data.get('auto_refresh_interval', 60)
        self.main_window.theme_setting = data.get('theme_setting', 'System Theme')
        
        # Load verbose console setting and apply it
        verbose_console = data.get('verbose_console', False)
        self.main_window.verbose_console = verbose_console
        
        # Load debug mode setting and apply it
        debug_mode = data.get('debug_mode', False)  # Default to disabled
        self.main_window.debug_mode = debug_mode
        self.main_window.apply_debug_mode()
        
        # Apply theme on startup
        self.main_window.apply_theme()
        
        # Start auto-refresh timer if enabled
        if self.main_window.auto_refresh_enabled:
            self.main_window.auto_refresh_timer.start(self.main_window.auto_refresh_interval * 1000)
        
        return data.get('devices', {})

    def save_auto_reconnect_settings(self):
        """Save auto-reconnect and auto-refresh settings to encrypted file"""
        data = self.main_window.file_crypto.load_encrypted_file(self.AUTO_RECONNECT_FILE)
        data['auto_reconnect_enabled'] = self.main_window.auto_reconnect_enabled
        data['interval'] = self.main_window.auto_reconnect_interval
        data['max_attempts'] = self.main_window.auto_reconnect_max_attempts
        data['grace_period'] = self.main_window.grace_period_duration
        data['auto_refresh_enabled'] = self.main_window.auto_refresh_enabled
        data['auto_refresh_interval'] = self.main_window.auto_refresh_interval
        data['theme_setting'] = self.main_window.theme_setting
        data['verbose_console'] = getattr(self.main_window, 'verbose_console', False)
        data['debug_mode'] = getattr(self.main_window, 'debug_mode', False)
        if 'devices' not in data:
            data['devices'] = {}
        self.main_window.file_crypto.save_encrypted_file(self.AUTO_RECONNECT_FILE, data)

    def get_auto_reconnect_state(self, ip, busid, table_type="local"):
        """Get auto-reconnect state for a specific device with table type separation"""
        data = self.main_window.file_crypto.load_encrypted_file(self.AUTO_RECONNECT_FILE)
        devices = data.get('devices', {})
        device_key = f"{table_type}:{ip}:{busid}"  # Separate by table type
        return devices.get(device_key, False)

    def toggle_auto_reconnect(self, ip, busid, enabled, table_type="local"):
        """Toggle auto-reconnect for a specific device with table type separation"""
        data = self.main_window.file_crypto.load_encrypted_file(self.AUTO_RECONNECT_FILE)
        if 'devices' not in data:
            data['devices'] = {}
        
        device_key = f"{table_type}:{ip}:{busid}"  # Separate by table type
        data['devices'][device_key] = enabled
        
        if enabled:
            self.main_window.console.append(f"🔄 Auto-reconnect enabled for {busid} on {ip} ({table_type})")
            # Reset attempt counter when enabled
            if device_key in self.main_window.auto_reconnect_attempts:
                del self.main_window.auto_reconnect_attempts[device_key]
        else:
            self.main_window.console.append(f"⏹️ Auto-reconnect disabled for {busid} on {ip} ({table_type})")
            # Remove from attempt tracking
            if device_key in self.main_window.auto_reconnect_attempts:
                del self.main_window.auto_reconnect_attempts[device_key]
        
        self.main_window.file_crypto.save_encrypted_file(self.AUTO_RECONNECT_FILE, data)

    def set_auto_reconnect_state_silent(self, ip, busid, enabled, table_type="local"):
        """Set auto-reconnect state without console logging (for save/restore operations)"""
        data = self.main_window.file_crypto.load_encrypted_file(self.AUTO_RECONNECT_FILE)
        if 'devices' not in data:
            data['devices'] = {}
        
        device_key = f"{table_type}:{ip}:{busid}"  # Separate by table type
        data['devices'][device_key] = enabled
        
        # Update attempt counter tracking without console output
        if enabled:
            # Reset attempt counter when enabled
            if device_key in self.main_window.auto_reconnect_attempts:
                del self.main_window.auto_reconnect_attempts[device_key]
        else:
            # Remove from attempt tracking
            if device_key in self.main_window.auto_reconnect_attempts:
                del self.main_window.auto_reconnect_attempts[device_key]
        
        self.main_window.file_crypto.save_encrypted_file(self.AUTO_RECONNECT_FILE, data)

    def save_device_mapping(self, remote_busid, remote_desc, port_number, port_busid):
        """Save mapping between remote device and attached port"""
        import time
        data = self.main_window.file_crypto.load_encrypted_file(self.DEVICE_MAPPING_FILE)
        if 'mappings' not in data:
            data['mappings'] = {}
        
        # Store mapping: remote_busid -> port info
        data['mappings'][remote_busid] = {
            'remote_desc': remote_desc,
            'port_number': port_number,
            'port_busid': port_busid,
            'timestamp': time.time()
        }
        
        self.main_window.file_crypto.save_encrypted_file(self.DEVICE_MAPPING_FILE, data)
        self.main_window.console.append(f"🔗 Mapped remote device {remote_busid} to port {port_number} (busid: {port_busid})")

    def get_device_mapping(self, remote_busid):
        """Get port mapping for a remote device"""
        data = self.main_window.file_crypto.load_encrypted_file(self.DEVICE_MAPPING_FILE)
        mappings = data.get('mappings', {})
        return mappings.get(remote_busid)

    def remove_device_mapping(self, remote_busid):
        """Remove mapping when device is detached"""
        data = self.main_window.file_crypto.load_encrypted_file(self.DEVICE_MAPPING_FILE)
        if 'mappings' in data and remote_busid in data['mappings']:
            del data['mappings'][remote_busid]
            self.main_window.file_crypto.save_encrypted_file(self.DEVICE_MAPPING_FILE, data)
            self.main_window.console.append(f"🔗 Removed mapping for remote device {remote_busid}")

    def get_remote_busid_for_port(self, port_busid):
        """Get the original remote busid for a port busid"""
        data = self.main_window.file_crypto.load_encrypted_file(self.DEVICE_MAPPING_FILE)
        mappings = data.get('mappings', {})
        for remote_busid, mapping_info in mappings.items():
            if mapping_info.get('port_busid') == port_busid:
                return remote_busid
        return None

    # ==================== Windows Device Descriptions ====================
    
    def save_windows_device_description(self, ip, busid, description):
        """Save Windows device description for later use when displaying 'unknown product'"""
        data = self.main_window.file_crypto.load_encrypted_file(self.WINDOWS_DEVICE_DESCRIPTIONS_FILE)
        if 'descriptions' not in data:
            data['descriptions'] = {}
        if ip not in data['descriptions']:
            data['descriptions'][ip] = {}
        
        # Store: IP -> busid -> description
        data['descriptions'][ip][busid] = description
        self.main_window.file_crypto.save_encrypted_file(self.WINDOWS_DEVICE_DESCRIPTIONS_FILE, data)
        self.main_window.console.append(f"🔧 Stored Windows description for {ip}/{busid}: '{description}'")

    def get_windows_device_description(self, ip, busid):
        """Get stored Windows device description for a busid"""
        data = self.main_window.file_crypto.load_encrypted_file(self.WINDOWS_DEVICE_DESCRIPTIONS_FILE)
        descriptions = data.get('descriptions', {})
        result = descriptions.get(ip, {}).get(busid)
        self.main_window.console.append(f"🔧 Retrieved Windows description for {ip}/{busid}: '{result}'")
        return result

    def clear_windows_device_descriptions(self, ip):
        """Clear all Windows device descriptions for an IP (when refreshing)"""
        data = self.main_window.file_crypto.load_encrypted_file(self.WINDOWS_DEVICE_DESCRIPTIONS_FILE)
        if 'descriptions' in data and ip in data['descriptions']:
            del data['descriptions'][ip]
            self.main_window.file_crypto.save_encrypted_file(self.WINDOWS_DEVICE_DESCRIPTIONS_FILE, data)

    # ==================== Device State Management ====================
    
    def load_state(self, ip):
        """Load device states for a specific IP"""
        all_state = self.main_window.file_crypto.load_encrypted_file("usbip_state.enc")
        return all_state.get(ip, {"attached": []})

    def save_state(self, ip, busid, attached):
        """Save device state for a specific IP and device"""
        all_state = self.main_window.file_crypto.load_encrypted_file("usbip_state.enc")
        state = all_state.get(ip, {"attached": []})
        if attached and busid not in state["attached"]:
            state["attached"].append(busid)
        elif not attached and busid in state["attached"]:
            state["attached"].remove(busid)
        all_state[ip] = state
        self.main_window.file_crypto.save_encrypted_file("usbip_state.enc", all_state)

    def load_remote_state(self, ip):
        """Load remote device bind states for a specific IP"""
        all_state = self.main_window.file_crypto.load_encrypted_file("usbip_state.enc")
        return all_state.get(ip, {}).get("remote_bound", {})

    def save_remote_state(self, ip, busid, bound):
        """Save remote device bind state for a specific IP and busid"""
        all_state = self.main_window.file_crypto.load_encrypted_file("usbip_state.enc")
        state = all_state.get(ip, {"attached": [], "remote_bound": {}})
        if "remote_bound" not in state:
            state["remote_bound"] = {}
        state["remote_bound"][busid] = bound
        all_state[ip] = state
        self.main_window.file_crypto.save_encrypted_file("usbip_state.enc", all_state)

    # ==================== Auto-Reconnect Settings ====================
    
    # ==================== Device Mapping Management ====================
    
    # ==================== Legacy/Deprecated Methods ====================

    def get_device_mapping(self, remote_busid):
        """Get device mapping for a remote busid"""
        try:
            data = self.main_window.file_crypto.load_encrypted_file("device_mapping.enc")
            return data.get(remote_busid)
        except Exception:
            return None

    def remove_device_mapping(self, remote_busid):
        """Remove device mapping for a remote busid"""
        try:
            data = self.main_window.file_crypto.load_encrypted_file("device_mapping.enc")
            if remote_busid in data:
                del data[remote_busid]
                self.main_window.file_crypto.save_encrypted_file("device_mapping.enc", data)
        except Exception as e:
            self.main_window.console.append(f"Error removing device mapping: {e}\n")

    def get_remote_busid_for_port(self, port_busid):
        """Get the original remote busid for a given port busid"""
        try:
            data = self.main_window.file_crypto.load_encrypted_file("device_mapping.enc")
            for remote_busid, mapping in data.items():
                if mapping.get("port_busid") == port_busid:
                    return remote_busid
            return None
        except Exception:
            return None

    # ==================== UI State Updates ====================
    
    def update_device_toggle_state(self, busid, attached):
        """Update device toggle button state in the UI"""
        for row in range(self.main_window.device_table.rowCount()):
            busid_item = self.main_window.device_table.item(row, 0)
            if busid_item and busid_item.text() == busid:
                toggle_btn = self.main_window.device_table.cellWidget(row, 2)
                if toggle_btn:
                    toggle_btn.setChecked(attached)
                break

    def update_remote_toggle_state(self, busid, bound):
        """Update remote device toggle button state in the UI"""
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            if busid_item and busid_item.text() == busid:
                toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
                if toggle_btn:
                    toggle_btn.setChecked(bound)
                break

    def update_auto_toggle_state(self, busid, enabled):
        """Update auto-reconnect toggle button state in the device table"""
        for row in range(self.main_window.device_table.rowCount()):
            busid_item = self.main_window.device_table.item(row, 0)
            if busid_item and busid_item.text() == busid:
                auto_btn = self.main_window.device_table.cellWidget(row, 3)
                if auto_btn:
                    auto_btn.setChecked(enabled)
                break

    def update_remote_auto_toggle_state(self, busid, enabled):
        """Update auto-reconnect toggle button state in the remote table"""
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            if busid_item and busid_item.text() == busid:
                auto_btn = self.main_window.remote_table.cellWidget(row, 3)
                if auto_btn:
                    auto_btn.setChecked(enabled)
                break

    # ==================== Theme Support ====================
    
    def get_theme_colors(self):
        """Get theme colors for UI styling"""
        return self.main_window.theme_manager.get_colors()
