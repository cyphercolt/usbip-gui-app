"""
Windows usbipd Service Management Utility

Provides functionality to manage the Windows usbipd service
via SSH connections to remote Windows servers.
"""

import paramiko
from typing import Tuple, Optional
from security.validator import SecurityValidator


class USBIPDServiceManager:
    """Utility class for managing Windows usbipd service via SSH"""

    @staticmethod
    def check_service_status(client: paramiko.SSHClient) -> Tuple[bool, str]:
        """
        Check the status of the usbipd service on a Windows system.

        Args:
            client: Active SSH client connection to Windows system

        Returns:
            Tuple of (is_running, status_message)
        """
        try:
            # Check service status
            stdin, stdout, stderr = client.exec_command("sc query usbipd", timeout=10)
            output = stdout.read().decode() + stderr.read().decode()

            if "RUNNING" in output:
                return True, "usbipd service is running"
            elif "STOPPED" in output:
                return False, "usbipd service is stopped"
            elif "does not exist" in output.lower():
                return False, "usbipd service is not installed"
            else:
                return False, f"usbipd service status unknown: {output.strip()}"

        except Exception as e:
            return False, f"Failed to check service status: {str(e)}"

    @staticmethod
    def start_service(client: paramiko.SSHClient) -> Tuple[bool, str]:
        """
        Attempt to start the usbipd service on a Windows system.

        Args:
            client: Active SSH client connection to Windows system

        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to start the service
            stdin, stdout, stderr = client.exec_command("sc start usbipd", timeout=15)
            output = stdout.read().decode() + stderr.read().decode()

            if "START_PENDING" in output or "RUNNING" in output:
                return True, "usbipd service started successfully"
            elif "already been started" in output:
                return True, "usbipd service was already running"
            elif "Access is denied" in output:
                return False, "Access denied - administrator privileges required"
            else:
                return False, f"Failed to start service: {output.strip()}"

        except Exception as e:
            return False, f"Error starting service: {str(e)}"

    @staticmethod
    def stop_service(client: paramiko.SSHClient) -> Tuple[bool, str]:
        """
        Attempt to stop the usbipd service on a Windows system.

        Args:
            client: Active SSH client connection to Windows system

        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to stop the service
            stdin, stdout, stderr = client.exec_command("sc stop usbipd", timeout=15)
            output = stdout.read().decode() + stderr.read().decode()

            if "STOP_PENDING" in output or "STOPPED" in output:
                return True, "usbipd service stopped successfully"
            elif "not started" in output:
                return True, "usbipd service was already stopped"
            elif "Access is denied" in output:
                return False, "Access denied - administrator privileges required"
            else:
                return False, f"Failed to stop service: {output.strip()}"

        except Exception as e:
            return False, f"Error stopping service: {str(e)}"

    @staticmethod
    def get_service_startup_type(
        client: paramiko.SSHClient,
    ) -> Tuple[Optional[str], str]:
        """
        Get the startup type of the usbipd service.

        Args:
            client: Active SSH client connection to Windows system

        Returns:
            Tuple of (startup_type, message) where startup_type is 'auto', 'manual', 'disabled', or None
        """
        try:
            # Get service configuration
            stdin, stdout, stderr = client.exec_command("sc qc usbipd", timeout=10)
            output = stdout.read().decode() + stderr.read().decode()

            if "AUTO_START" in output:
                return "auto", "Service is set to start automatically"
            elif "DEMAND_START" in output:
                return "manual", "Service is set to manual start"
            elif "DISABLED" in output:
                return "disabled", "Service is disabled"
            else:
                return None, f"Could not determine startup type: {output.strip()}"

        except Exception as e:
            return None, f"Error checking startup type: {str(e)}"

    @staticmethod
    def set_service_startup_auto(client: paramiko.SSHClient) -> Tuple[bool, str]:
        """
        Set the usbipd service to start automatically.

        Args:
            client: Active SSH client connection to Windows system

        Returns:
            Tuple of (success, message)
        """
        try:
            # Set service to automatic startup
            stdin, stdout, stderr = client.exec_command(
                "sc config usbipd start= auto", timeout=10
            )
            output = stdout.read().decode() + stderr.read().decode()

            if "SUCCESS" in output:
                return True, "usbipd service set to automatic startup"
            elif "Access is denied" in output:
                return False, "Access denied - administrator privileges required"
            else:
                return False, f"Failed to configure service: {output.strip()}"

        except Exception as e:
            return False, f"Error configuring service: {str(e)}"

    @staticmethod
    def install_usbipd_check(
        client: paramiko.SSHClient,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Check if usbipd is installed and get version information.

        Args:
            client: Active SSH client connection to Windows system

        Returns:
            Tuple of (is_installed, message, version)
        """
        try:
            # Try multiple ways to find and check usbipd
            commands_to_try = [
                "usbipd --version",
                '"C:\\Program Files\\usbipd-win\\usbipd.exe" --version',
                "where usbipd 2>$null; if ($?) { usbipd --version }",
                "Get-Command usbipd -ErrorAction SilentlyContinue | ForEach-Object { & $_.Source --version }",
            ]

            for cmd in commands_to_try:
                try:
                    stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
                    output = stdout.read().decode().strip()
                    error = stderr.read().decode().strip()

                    if output and "usbipd" in output.lower():
                        # Extract version from output
                        lines = output.splitlines()
                        version = lines[0] if lines else "Unknown version"
                        return True, f"usbipd is installed: {version}", version

                except Exception:
                    continue

            # If none of the commands worked, usbipd is not found
            return False, "usbipd is not installed or not accessible", None

        except Exception as e:
            return False, f"Error checking usbipd installation: {str(e)}", None
