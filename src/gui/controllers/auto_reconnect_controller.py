"""Auto-reconnect controller for managing automatic device reconnection logic."""

from PyQt6.QtCore import QObject


class AutoReconnectController(QObject):
    """Controller for handling automatic device reconnection logic."""

    def __init__(self, main_window):
        """
        Initialize the auto-reconnect controller.

        Args:
            main_window: Reference to the main window instance
        """
        super().__init__()
        self.main_window = main_window

    def check_auto_reconnect(self):
        """Check for devices that need auto-reconnection"""
        if (
            not self.main_window.auto_reconnect_enabled
            or self.main_window.auto_reconnect_grace_period
        ):
            return

        current_ip = self.main_window.ip_input.currentText()
        if not current_ip:
            return

        from security.crypto import FileEncryption

        data = self.main_window.file_crypto.load_encrypted_file("auto_reconnect.enc")
        auto_devices = data.get("devices", {})

        # Check each device with auto-reconnect enabled
        for device_key, enabled in auto_devices.items():
            if not enabled:
                continue

            try:
                # New format: table_type:ip:busid
                if device_key.count(":") >= 2:
                    table_type, ip, busid = device_key.split(":", 2)
                else:
                    # Legacy format: ip:busid (assume local)
                    ip, busid = device_key.split(":", 1)
                    table_type = "local"

                if ip != current_ip:
                    continue  # Only check current IP

                # Check based on table type
                if table_type == "local" and self.should_auto_reconnect_device(
                    ip, busid
                ):
                    self.attempt_auto_reconnect(ip, busid, device_key)
                elif table_type == "remote" and self.should_auto_bind_device(ip, busid):
                    self.attempt_auto_bind(ip, busid, device_key)

            except Exception as e:
                continue  # Skip malformed device keys

    def should_auto_reconnect_device(self, ip, busid):
        """Check if a device should be auto-reconnected"""
        # Find the device in the local device table
        for row in range(self.main_window.device_table.rowCount()):
            busid_item = self.main_window.device_table.item(row, 0)
            toggle_btn = self.main_window.device_table.cellWidget(row, 2)
            auto_btn = self.main_window.device_table.cellWidget(row, 3)

            if (
                busid_item
                and busid_item.text() == busid
                and toggle_btn
                and not toggle_btn.isChecked()  # Device is detached
                and auto_btn
                and auto_btn.isChecked()
            ):  # Auto-reconnect is enabled
                return True
        return False

    def should_auto_bind_device(self, ip, busid):
        """Check if a remote device should be auto-bound"""
        # Find the device in the remote device table
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
            auto_btn = self.main_window.remote_table.cellWidget(row, 3)

            if (
                busid_item
                and busid_item.text() == busid
                and toggle_btn
                and not toggle_btn.isChecked()  # Device is unbound
                and auto_btn
                and auto_btn.isChecked()
            ):  # Auto-reconnect is enabled
                return True
        return False

    def attempt_auto_reconnect(self, ip, busid, device_key):
        """Attempt to auto-reconnect a device (local table - attach)"""
        # Check attempt limits
        if device_key not in self.main_window.auto_reconnect_attempts:
            self.main_window.auto_reconnect_attempts[device_key] = 0

        if (
            self.main_window.auto_reconnect_attempts[device_key]
            >= self.main_window.auto_reconnect_max_attempts
        ):
            return  # Max attempts reached

        self.main_window.auto_reconnect_attempts[device_key] += 1

        # Find device description for the attach command
        device_desc = None
        for row in range(self.main_window.device_table.rowCount()):
            busid_item = self.main_window.device_table.item(row, 0)
            desc_item = self.main_window.device_table.item(row, 1)
            if busid_item and busid_item.text() == busid and desc_item:
                device_desc = desc_item.text()
                break

        if not device_desc:
            return  # Device not found

        # Attempt reconnection
        self.main_window.append_simple_message(
            f"🔄 Auto-attaching {busid} "
            f"(attempt {self.main_window.auto_reconnect_attempts[device_key]}/"
            f"{self.main_window.auto_reconnect_max_attempts})"
        )

        success = self.main_window.toggle_attach(
            ip, busid, device_desc, 2, start_grace_period=False
        )  # 2 = attach

        if success:
            self.main_window.append_simple_message(
                f"✅ Auto-attach successful: {busid}"
            )
            # Reset attempt counter on success
            if device_key in self.main_window.auto_reconnect_attempts:
                del self.main_window.auto_reconnect_attempts[device_key]
            # Update the toggle button state
            self.update_device_toggle_state(busid, True)
        else:
            if (
                self.main_window.auto_reconnect_attempts[device_key]
                >= self.main_window.auto_reconnect_max_attempts
            ):
                self.main_window.append_simple_message(
                    f"❌ Auto-attach failed for {busid} - max attempts reached"
                )
                # Disable auto-reconnect for this device after max attempts
                self.main_window.toggle_auto_reconnect(ip, busid, False, "local")
                self.main_window.update_auto_toggle_state(busid, False)

    def attempt_auto_bind(self, ip, busid, device_key):
        """Attempt to auto-bind a remote device (remote table - bind)"""
        # Check if we have SSH credentials
        username = getattr(self.main_window, "last_ssh_username", "")
        password = getattr(self.main_window, "last_ssh_password", "")
        accept = getattr(self.main_window, "last_ssh_accept", False)

        if not username or not password:
            # Skip silently if no SSH credentials available
            return

        # Check attempt limits
        if device_key not in self.main_window.auto_reconnect_attempts:
            self.main_window.auto_reconnect_attempts[device_key] = 0

        if (
            self.main_window.auto_reconnect_attempts[device_key]
            >= self.main_window.auto_reconnect_max_attempts
        ):
            return  # Max attempts reached

        self.main_window.auto_reconnect_attempts[device_key] += 1

        # Attempt auto-bind
        self.main_window.append_simple_message(
            f"🔄 Auto-binding {busid} "
            f"(attempt {self.main_window.auto_reconnect_attempts[device_key]}/"
            f"{self.main_window.auto_reconnect_max_attempts})"
        )

        success = self.main_window.perform_remote_bind(
            ip, username, password, busid, accept, bind=True
        )

        if success:
            self.main_window.append_simple_message(f"✅ Auto-bind successful: {busid}")
            self.main_window.append_simple_message(
                "🔄 Refreshing local devices to show newly bound device..."
            )
            # Reset attempt counter on success
            if device_key in self.main_window.auto_reconnect_attempts:
                del self.main_window.auto_reconnect_attempts[device_key]
            # Update the toggle button state
            self.main_window.update_remote_toggle_state(busid, True)
            # Refresh local devices to show newly bound device (preserve state)
            self.main_window.refresh_local_devices_silently()
        else:
            if (
                self.main_window.auto_reconnect_attempts[device_key]
                >= self.main_window.auto_reconnect_max_attempts
            ):
                self.main_window.append_simple_message(
                    f"❌ Auto-bind failed for {busid} - max attempts reached"
                )
                # Disable auto-reconnect for this device after max attempts
                self.main_window.toggle_auto_reconnect(ip, busid, False, "remote")
                self.main_window.update_remote_auto_toggle_state(busid, False)

    def update_device_toggle_state(self, busid, attached):
        """Update the toggle button state for a device"""
        for row in range(self.main_window.device_table.rowCount()):
            busid_item = self.main_window.device_table.item(row, 0)
            toggle_btn = self.main_window.device_table.cellWidget(row, 2)

            if busid_item and busid_item.text() == busid and toggle_btn:
                # Block signals to prevent triggering bind/unbind operations
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(attached)
                toggle_btn.blockSignals(False)
                break

    def update_remote_toggle_state(self, busid, bound):
        """Update the toggle button state for a remote device"""
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            toggle_btn = self.main_window.remote_table.cellWidget(row, 2)
            if busid_item and busid_item.text() == busid and toggle_btn:
                # Block signals to prevent triggering bind/unbind operations
                toggle_btn.blockSignals(True)
                toggle_btn.setChecked(bound)
                toggle_btn.blockSignals(False)
                break

    def update_auto_toggle_state(self, busid, enabled):
        """Update the auto-reconnect toggle button state for a device"""
        for row in range(self.main_window.device_table.rowCount()):
            busid_item = self.main_window.device_table.item(row, 0)
            auto_btn = self.main_window.device_table.cellWidget(row, 3)
            if busid_item and busid_item.text() == busid and auto_btn:
                # Block signals to prevent triggering auto-reconnect changes
                auto_btn.blockSignals(True)
                auto_btn.setChecked(enabled)
                auto_btn.blockSignals(False)
                break

    def update_remote_auto_toggle_state(self, busid, enabled):
        """Update the auto-reconnect toggle button state for a remote device"""
        for row in range(self.main_window.remote_table.rowCount()):
            busid_item = self.main_window.remote_table.item(row, 0)
            auto_btn = self.main_window.remote_table.cellWidget(row, 3)
            if busid_item and busid_item.text() == busid and auto_btn:
                # Block signals to prevent triggering auto-reconnect changes
                auto_btn.blockSignals(True)
                auto_btn.setChecked(enabled)
                auto_btn.blockSignals(False)
                break
