"""
Remote OS Detection Utility

Detects the operating system of remote SSH servers to determine
the appropriate USB/IP commands and execution methods.
"""

import paramiko
import platform
from typing import Optional, Tuple
from security.validator import SecurityValidator


class RemoteOSDetector:
    """Utility class for detecting remote operating system via SSH"""

    @staticmethod
    def detect_remote_os(
        ip: str, username: str, password: str, accept_fingerprint: bool = True
    ) -> Tuple[Optional[str], bool]:
        """
        Detect the operating system of a remote SSH server.

        Args:
            ip: Remote server IP address
            username: SSH username
            password: SSH password
            accept_fingerprint: Whether to accept unknown host keys

        Returns:
            Tuple of (os_type, has_usbipd_service) where:
            - os_type: 'windows', 'linux', 'darwin', or None if detection failed
            - has_usbipd_service: True if Windows usbipd service is running
        """
        try:
            client = paramiko.SSHClient()
            if accept_fingerprint:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.RejectPolicy())

            client.connect(ip, username=username, password=password, timeout=10)

            # Try Windows detection first
            windows_result = RemoteOSDetector._check_windows_os(client)
            if windows_result[0] == "windows":
                client.close()
                return windows_result

            # Try Unix-like detection
            unix_result = RemoteOSDetector._check_unix_os(client)
            client.close()
            return unix_result

        except Exception as e:
            return None, False

    @staticmethod
    def _check_windows_os(client: paramiko.SSHClient) -> Tuple[Optional[str], bool]:
        """Check if remote system is Windows and if usbipd service is available"""
        try:
            # Check if this is Windows by looking for Windows-specific commands
            stdin, stdout, stderr = client.exec_command("ver", timeout=5)
            output = stdout.read().decode().strip()

            if "Windows" in output or "Microsoft" in output:
                # This is Windows, now check for usbipd service
                usbipd_available = RemoteOSDetector._check_usbipd_service(client)
                return "windows", usbipd_available

        except Exception:
            pass

        return None, False

    @staticmethod
    def _check_unix_os(client: paramiko.SSHClient) -> Tuple[Optional[str], bool]:
        """Check if remote system is Unix-like (Linux/macOS)"""
        try:
            # Check for uname command (Unix-like systems)
            stdin, stdout, stderr = client.exec_command("uname -s", timeout=5)
            output = stdout.read().decode().strip().lower()

            if "linux" in output:
                return "linux", False  # Linux systems use traditional usbip daemon
            elif "darwin" in output:
                return "darwin", False  # macOS
            elif output:  # Some other Unix-like system
                return "linux", False  # Treat as Linux for USB/IP purposes

        except Exception:
            pass

        return None, False

    @staticmethod
    def _check_usbipd_service(client: paramiko.SSHClient) -> bool:
        """Check if usbipd-win service is running on Windows"""
        try:
            # Try multiple ways to check for usbipd
            commands_to_try = [
                "usbipd --version",
                '"C:\\Program Files\\usbipd-win\\usbipd.exe" --version',
                "where usbipd",
                "Get-Command usbipd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source",
            ]

            usbipd_found = False
            for cmd in commands_to_try:
                try:
                    stdin, stdout, stderr = client.exec_command(cmd, timeout=5)
                    output = stdout.read().decode().strip()
                    error = stderr.read().decode().strip()

                    if output and (
                        "usbipd" in output.lower() or "version" in output.lower()
                    ):
                        usbipd_found = True
                        break
                except:
                    continue

            if not usbipd_found:
                return False

            # Now check if service is running
            stdin, stdout, stderr = client.exec_command("sc query usbipd", timeout=5)
            service_output = stdout.read().decode().strip()

            if "RUNNING" in service_output:
                return True
            elif "STOPPED" in service_output:
                # Service exists but is stopped
                return False

            return False

        except Exception:
            return False

    @staticmethod
    def get_remote_usbip_list_command(os_type: str, has_usbipd: bool = False) -> str:
        """
        Get the appropriate command for listing USB devices on remote system.

        Args:
            os_type: Operating system type ('windows', 'linux', 'darwin')
            has_usbipd: Whether Windows usbipd service is available

        Returns:
            Command string for listing USB devices
        """
        if os_type == "windows" and has_usbipd:
            return "usbipd list"
        else:
            # Linux, macOS, or Windows without usbipd
            return "usbip list -l"

    @staticmethod
    def get_remote_usbip_bind_command(
        os_type: str, busid: str, has_usbipd: bool = False
    ) -> str:
        """
        Get the appropriate command for binding USB devices on remote system.

        Args:
            os_type: Operating system type ('windows', 'linux', 'darwin')
            busid: USB device bus ID
            has_usbipd: Whether Windows usbipd service is available

        Returns:
            Command string for binding USB device
        """
        if os_type == "windows" and has_usbipd:
            return f"usbipd bind --busid {SecurityValidator.sanitize_for_shell(busid)}"
        else:
            # Linux, macOS, or Windows without usbipd - requires sudo
            return f"usbip bind -b {SecurityValidator.sanitize_for_shell(busid)}"

    @staticmethod
    def get_remote_usbip_unbind_command(
        os_type: str, busid: str, has_usbipd: bool = False
    ) -> str:
        """
        Get the appropriate command for unbinding USB devices on remote system.

        Args:
            os_type: Operating system type ('windows', 'linux', 'darwin')
            busid: USB device bus ID
            has_usbipd: Whether Windows usbipd service is available

        Returns:
            Command string for unbinding USB device
        """
        if os_type == "windows" and has_usbipd:
            return (
                f"usbipd unbind --busid {SecurityValidator.sanitize_for_shell(busid)}"
            )
        else:
            # Linux, macOS, or Windows without usbipd - requires sudo
            return f"usbip unbind -b {SecurityValidator.sanitize_for_shell(busid)}"

    @staticmethod
    def requires_admin_privileges(os_type: str, has_usbipd: bool = False) -> bool:
        """
        Check if the remote system requires admin privileges for USB/IP operations.

        Args:
            os_type: Operating system type ('windows', 'linux', 'darwin')
            has_usbipd: Whether Windows usbipd service is available

        Returns:
            True if admin privileges (sudo/administrator) are required
        """
        if os_type == "windows" and has_usbipd:
            # Windows usbipd requires administrator privileges
            return True
        else:
            # Linux/Unix systems require sudo for usbip commands
            return True

    @staticmethod
    def start_usbipd_service(client: paramiko.SSHClient) -> bool:
        """
        Attempt to start the usbipd service on Windows.

        Args:
            client: Active SSH client connection

        Returns:
            True if service was started successfully
        """
        try:
            # Try to start the service
            stdin, stdout, stderr = client.exec_command("sc start usbipd", timeout=10)
            output = stdout.read().decode() + stderr.read().decode()

            # Check if service started successfully
            if "START_PENDING" in output or "RUNNING" in output:
                return True

            return False

        except Exception:
            return False
