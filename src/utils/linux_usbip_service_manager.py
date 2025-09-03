"""
Linux USB/IP Service Management Utility

Provides methods for managing USB/IP daemon and kernel modules
on remote Linux systems via SSH.
"""

import re
import time
from security.validator import SecurityValidator, SecureCommandBuilder


class LinuxUSBIPServiceManager:
    """Utility class for managing USB/IP services on Linux systems"""

    @staticmethod
    def check_service_status(ssh_client, password=None):
        """
        Check the status of USB/IP daemon and kernel modules
        Returns: (is_ready_for_operations, detailed_status_message)
        """
        try:
            status_parts = []
            # Track what's needed for USB/IP client operations
            modules_loaded = False
            command_available = False

            # Check usbipd daemon using sudo systemctl status (most reliable)
            daemon_running = False
            daemon_status_msg = ""

            # Use sudo systemctl status to get the actual service state
            if password:
                status_cmd = f"echo '{password}' | sudo -S systemctl status usbipd"
            else:
                status_cmd = "sudo systemctl status usbipd"

            stdin, stdout, stderr = ssh_client.exec_command(status_cmd)
            status_output = stdout.read().decode()

            # Parse the Active line to determine actual status - be more specific
            active_line = ""
            for line in status_output.split("\n"):
                line = line.strip()
                if line.startswith("Active:"):
                    active_line = line
                    break

            # Check chronological order of log entries to determine true state
            log_lines = status_output.split("\n")
            last_listening_line = -1
            last_stopped_line = -1

            for i, line in enumerate(log_lines):
                if "listening on" in line.lower() and (
                    "3240" in line or "0.0.0.0" in line or ":::" in line
                ):
                    last_listening_line = i
                elif "stopped" in line.lower() and "usbipd" in line.lower():
                    last_stopped_line = i

            # Determine if daemon is actually running based on chronological order
            listening_on_port = (
                last_listening_line > last_stopped_line and last_listening_line >= 0
            )

            if active_line:
                # More precise parsing - check the Active line content
                active_lower = active_line.lower()

                # If daemon is listening, it's running - override any systemctl status
                if listening_on_port:
                    daemon_status_msg = "🟢 usbipd daemon: RUNNING (can share devices)"
                    daemon_running = True
                elif "failed" in active_lower:
                    daemon_status_msg = "� usbipd daemon: FAILED (check service logs)"
                    daemon_running = False
                elif "inactive" in active_lower:
                    daemon_status_msg = (
                        "ℹ️ usbipd daemon: STOPPED (start if you need to share devices)"
                    )
                    daemon_running = False
                elif "active (running)" in active_lower:
                    daemon_status_msg = "� usbipd daemon: RUNNING (can share devices)"
                    daemon_running = True
                elif "activating" in active_lower:
                    daemon_status_msg = (
                        "🟡 usbipd daemon: STARTING (can share devices soon)"
                    )
                    daemon_running = False  # Not fully operational yet
                elif "deactivating" in active_lower:
                    daemon_status_msg = (
                        "� usbipd daemon: STOPPING (service shutting down)"
                    )
                    daemon_running = False  # No longer operational
                elif listening_on_port:
                    # Only use listening port as indicator if Active status is unclear
                    daemon_status_msg = "🟢 usbipd daemon: RUNNING (can share devices)"
                    daemon_running = True
                else:
                    daemon_status_msg = (
                        f"⚠️ usbipd daemon: UNKNOWN STATUS ({active_line})"
                    )
                    daemon_running = False
            else:
                daemon_status_msg = "❌ usbipd daemon: STATUS CHECK FAILED"
                daemon_running = False

            status_parts.append(daemon_status_msg)

            # Check if usbipd is enabled (try different service names)
            enabled_status = "disabled"
            for service_name in ["usbipd", "usbip", "usbip-daemon"]:
                stdin, stdout, stderr = ssh_client.exec_command(
                    f"systemctl is-enabled {service_name} 2>/dev/null || echo 'disabled'"
                )
                status = stdout.read().decode().strip()
                if status == "enabled":
                    enabled_status = "enabled"
                    break

            if enabled_status == "enabled":
                status_parts.append("🟢 usbipd auto-start: ENABLED")
            else:
                status_parts.append(
                    "ℹ️ usbipd auto-start: DISABLED (enable if you need to share devices)"
                )

            # Check kernel modules (REQUIRED for attaching devices)
            stdin, stdout, stderr = ssh_client.exec_command(
                "lsmod | grep -E 'usbip_host|usbip_core'"
            )
            modules_output = stdout.read().decode().strip()

            if "usbip_host" in modules_output and "usbip_core" in modules_output:
                status_parts.append(
                    "🟢 USB/IP kernel modules: LOADED (can attach devices)"
                )
                modules_loaded = True
            else:
                status_parts.append(
                    "🔴 USB/IP kernel modules: NOT LOADED (cannot attach devices)"
                )

            # Check usbip command availability (REQUIRED for attaching devices)
            stdin, stdout, stderr = ssh_client.exec_command("which usbip")
            usbip_path = stdout.read().decode().strip()
            if usbip_path:
                status_parts.append(f"🟢 usbip command: AVAILABLE ({usbip_path})")
                command_available = True
            else:
                status_parts.append("🔴 usbip command: NOT FOUND")

            # System is ready for USB/IP operations if modules and command are available
            # Daemon is only needed for sharing devices TO others
            is_operational = modules_loaded and command_available

            return is_operational, "\n".join(status_parts), daemon_running

        except Exception as e:
            return False, f"Failed to check service status: {str(e)}", False

    @staticmethod
    def start_service(ssh_client, password):
        """
        Start USB/IP daemon and load kernel modules
        Returns: (success, message)
        """
        try:
            operations = []

            # Load kernel modules first using secure command builder
            modprobe_cmd = SecureCommandBuilder.build_modprobe_command(
                "usbip_host usbip_core", password, remote_execution=True
            )
            if modprobe_cmd:
                stdin, stdout, stderr = ssh_client.exec_command(modprobe_cmd)
                stderr_output = stderr.read().decode().strip()
                if stderr_output and "already loaded" not in stderr_output.lower():
                    operations.append("⚠️ Kernel modules may have failed to load")
                else:
                    operations.append("✅ USB/IP kernel modules loaded")
            else:
                operations.append("❌ Failed to build modprobe command")

            # Find the correct service name to start
            service_to_start = "usbipd"  # Default
            for service_name in ["usbipd", "usbip", "usbip-daemon"]:
                stdin, stdout, stderr = ssh_client.exec_command(
                    f"systemctl list-unit-files | grep {service_name} | head -1"
                )
                if stdout.read().decode().strip():
                    service_to_start = service_name
                    break

            # Start usbipd service using secure command builder
            start_cmd = SecureCommandBuilder.build_systemctl_command(
                "start", service_to_start, password, remote_execution=True
            )
            if not start_cmd:
                return False, "Failed to build secure start command"

            stdin, stdout, stderr = ssh_client.exec_command(start_cmd)
            stderr_output = stderr.read().decode().strip()
            if stderr_output and "failed" in stderr_output.lower():
                return (
                    False,
                    f"Failed to start {service_to_start} service: {stderr_output}",
                )

            operations.append(f"✅ {service_to_start} daemon started")

            # Wait for service to fully start
            time.sleep(3)

            # Check if it's actually running
            is_operational, status_message, daemon_running = (
                LinuxUSBIPServiceManager.check_service_status(ssh_client, password)
            )

            if daemon_running:
                operations.append("✅ Service startup confirmed")
                return True, "\n".join(operations)
            else:
                operations.append("⚠️ Service may still be starting")
                return True, "\n".join(operations)

        except Exception as e:
            return False, f"Failed to start service: {str(e)}"

    @staticmethod
    def stop_service(ssh_client, password):
        """
        Stop USB/IP daemon
        Returns: (success, message)
        """
        try:
            # Stop usbipd service using secure command builder
            stop_cmd = SecureCommandBuilder.build_systemctl_command(
                "stop", "usbipd", password, remote_execution=True
            )
            if not stop_cmd:
                return (
                    False,
                    "Failed to build secure stop command - check SecureCommandBuilder service whitelist",
                )

            # Execute the command
            stdin, stdout, stderr = ssh_client.exec_command(stop_cmd)
            stderr_output = stderr.read().decode().strip()
            stdout_output = stdout.read().decode().strip()

            # Improved error checking - systemctl stop usually succeeds silently
            if stderr_output and (
                "failed" in stderr_output.lower() or "error" in stderr_output.lower()
            ):
                return False, f"Failed to stop usbipd service: {stderr_output}"

            # Wait for service to fully stop
            time.sleep(3)

            # Check if it's actually stopped
            is_operational, status_message, daemon_running = (
                LinuxUSBIPServiceManager.check_service_status(ssh_client, password)
            )

            if not daemon_running:
                return True, "✅ usbipd daemon stopped successfully"
            else:
                return True, "⚠️ Service may still be stopping"

        except Exception as e:
            return False, f"Failed to stop service: {str(e)}"

    @staticmethod
    def enable_auto_start(ssh_client, password):
        """
        Enable USB/IP daemon to start automatically on boot
        Returns: (success, message)
        """
        try:
            enable_cmd = SecureCommandBuilder.build_systemctl_command(
                "enable", "usbipd", password, remote_execution=True
            )
            if not enable_cmd:
                return False, "Failed to build secure enable command"

            stdin, stdout, stderr = ssh_client.exec_command(enable_cmd)
            stderr_output = stderr.read().decode().strip()
            if stderr_output and "Failed" in stderr_output:
                return False, f"Failed to enable auto-start: {stderr_output}"

            return True, "✅ usbipd daemon enabled for auto-start on boot"

        except Exception as e:
            return False, f"Failed to enable auto-start: {str(e)}"

    @staticmethod
    def disable_auto_start(ssh_client, password):
        """
        Disable USB/IP daemon auto-start on boot
        Returns: (success, message)
        """
        try:
            disable_cmd = SecureCommandBuilder.build_systemctl_command(
                "disable", "usbipd", password, remote_execution=True
            )
            if not disable_cmd:
                return False, "Failed to build secure disable command"

            stdin, stdout, stderr = ssh_client.exec_command(disable_cmd)
            stderr_output = stderr.read().decode().strip()
            if stderr_output and "Failed" in stderr_output:
                return False, f"Failed to disable auto-start: {stderr_output}"

            return True, "✅ usbipd daemon disabled from auto-start"

        except Exception as e:
            return False, f"Failed to disable auto-start: {str(e)}"

    @staticmethod
    def check_installation(ssh_client):
        """
        Check if USB/IP tools are installed
        Returns: (success, message, version_info)
        """
        try:
            # Check for usbip command
            stdin, stdout, stderr = ssh_client.exec_command(
                "usbip version 2>/dev/null || usbip --version 2>/dev/null || echo 'not found'"
            )
            version_output = stdout.read().decode().strip()

            if "not found" in version_output:
                return (
                    False,
                    "USB/IP tools not installed. Install with: sudo apt install linux-tools-generic (Ubuntu) or equivalent",
                    "",
                )

            # Check for systemd service
            stdin, stdout, stderr = ssh_client.exec_command(
                "systemctl list-unit-files | grep usbipd || echo 'no service'"
            )
            service_output = stdout.read().decode().strip()

            if "no service" in service_output:
                return (
                    False,
                    "usbipd systemd service not found. USB/IP may not be properly installed",
                    version_output,
                )

            # Check kernel modules availability
            stdin, stdout, stderr = ssh_client.exec_command(
                "modinfo usbip_host usbip_core 2>/dev/null | grep -E '^filename:' | wc -l"
            )
            module_count = stdout.read().decode().strip()

            if int(module_count) < 2:
                return (
                    False,
                    "USB/IP kernel modules not available. Install linux-tools or usbip packages",
                    version_output,
                )

            return (
                True,
                f"USB/IP installation verified - {version_output}",
                version_output,
            )

        except Exception as e:
            return False, f"Failed to check installation: {str(e)}", ""

    @staticmethod
    def load_kernel_modules(ssh_client, password):
        """
        Load USB/IP kernel modules
        Returns: (success, message)
        """
        try:
            modprobe_cmd = SecureCommandBuilder.build_modprobe_command(
                "usbip_host usbip_core", password, remote_execution=True
            )
            if not modprobe_cmd:
                return False, "Failed to build secure modprobe command"

            stdin, stdout, stderr = ssh_client.exec_command(modprobe_cmd)
            stderr_output = stderr.read().decode().strip()

            if (
                stderr_output
                and "failed" in stderr_output.lower()
                and "already loaded" not in stderr_output.lower()
            ):
                return False, f"Failed to load kernel modules: {stderr_output}"

            # Verify modules are loaded
            stdin, stdout, stderr = ssh_client.exec_command(
                "lsmod | grep -E 'usbip_host|usbip_core' | wc -l"
            )
            loaded_count = stdout.read().decode().strip()

            if int(loaded_count) >= 2:
                return True, "✅ USB/IP kernel modules loaded successfully"
            else:
                return False, "Kernel modules failed to load properly"

        except Exception as e:
            return False, f"Failed to load kernel modules: {str(e)}"

    @staticmethod
    def unload_kernel_modules(ssh_client, password):
        """
        Unload USB/IP kernel modules
        Returns: (success, message)
        """
        try:
            # Build modprobe -r command
            unload_cmd = SecureCommandBuilder.build_modprobe_command(
                "-r usbip_host usbip_core", password, remote_execution=True
            )
            if not unload_cmd:
                return False, "Failed to build secure modprobe remove command"

            # Try to unload modules (may fail if in use)
            stdin, stdout, stderr = ssh_client.exec_command(f"{unload_cmd} 2>/dev/null")

            # Check if modules are still loaded
            stdin, stdout, stderr = ssh_client.exec_command(
                "lsmod | grep -E 'usbip_host|usbip_core' | wc -l"
            )
            loaded_count = stdout.read().decode().strip()

            if int(loaded_count) == 0:
                return True, "✅ USB/IP kernel modules unloaded successfully"
            else:
                return (
                    False,
                    "⚠️ Some modules may still be in use and cannot be unloaded",
                )

        except Exception as e:
            return False, f"Failed to unload kernel modules: {str(e)}"
