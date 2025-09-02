"""Input validation and sanitization for security"""
import re
import ipaddress
import shlex
import platform
from typing import Optional


class SecurityValidator:
    """Validates and sanitizes user inputs to prevent injection attacks"""
    
    # Allowed patterns for different input types
    BUSID_PATTERN = re.compile(r'^[0-9]+-[0-9]+(\.[0-9]+)*$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+$')
    HOSTNAME_PATTERN = re.compile(r'^[a-zA-Z0-9.-]+$')
    
    @staticmethod
    def validate_busid(busid: str) -> bool:
        """Validate USB bus ID format"""
        if not busid or len(busid) > 20:
            return False
        return bool(SecurityValidator.BUSID_PATTERN.match(busid))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate SSH username format"""
        if not username or len(username) > 32:
            return False
        return bool(SecurityValidator.USERNAME_PATTERN.match(username))
    
    @staticmethod
    def validate_ip_or_hostname(address: str) -> bool:
        """Validate IP address or hostname format"""
        if not address or len(address) > 253:
            return False
        
        # Try to parse as IP address first
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            pass
        
        # Validate as hostname
        if not SecurityValidator.HOSTNAME_PATTERN.match(address):
            return False
        
        # Additional hostname checks
        if address.startswith('-') or address.endswith('-'):
            return False
        
        # Check each label
        labels = address.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
        
        return True
    
    @staticmethod
    def sanitize_for_shell(input_str: str) -> str:
        """Safely quote string for shell command"""
        return shlex.quote(input_str)
    
    @staticmethod
    def validate_port_number(port: str) -> bool:
        """Validate port number format"""
        try:
            port_num = int(port)
            return 0 <= port_num <= 65535
        except ValueError:
            return False
    
    @staticmethod
    def sanitize_console_output(output: str) -> str:
        """Remove potentially sensitive information from console output"""
        if not output:
            return ""
        
        # Remove sudo password prompts
        lines = []
        for line in output.split('\n'):
            if '[sudo] password for' not in line.lower():
                lines.append(line)
        
        return '\n'.join(lines)


class SecureCommandBuilder:
    """Builds secure shell commands with proper escaping"""
    
    @staticmethod
    def build_usbip_bind_command(busid: str, password: str, remote_execution: bool = False) -> Optional[str]:
        """Build a secure usbip bind command
        
        Args:
            busid: The USB device bus ID
            password: The sudo password
            remote_execution: If True, always use sudo (for SSH execution on remote Linux)
                            If False, check local platform to determine sudo usage
        """
        if not SecurityValidator.validate_busid(busid):
            return None
        
        # Use proper shell escaping
        safe_busid = SecurityValidator.sanitize_for_shell(busid)
        
        # For remote execution (SSH), always use sudo regardless of local platform
        # For local execution, only use sudo on non-Windows platforms
        if remote_execution or platform.system() != "Windows":
            safe_password = SecurityValidator.sanitize_for_shell(password)
            return f"echo {safe_password} | sudo -S usbip bind -b {safe_busid}"
        else:
            # Local Windows execution - no sudo needed
            return f"usbip bind -b {safe_busid}"
    
    @staticmethod
    def build_usbip_unbind_command(busid: str, password: str, remote_execution: bool = False) -> Optional[str]:
        """Build a secure usbip unbind command
        
        Args:
            busid: The USB device bus ID
            password: The sudo password
            remote_execution: If True, always use sudo (for SSH execution on remote Linux)
                            If False, check local platform to determine sudo usage
        """
        if not SecurityValidator.validate_busid(busid):
            return None
        
        # Use proper shell escaping
        safe_busid = SecurityValidator.sanitize_for_shell(busid)
        
        # For remote execution (SSH), always use sudo regardless of local platform
        # For local execution, only use sudo on non-Windows platforms
        if remote_execution or platform.system() != "Windows":
            safe_password = SecurityValidator.sanitize_for_shell(password)
            return f"echo {safe_password} | sudo -S usbip unbind -b {safe_busid}"
        else:
            # Local Windows execution - no sudo needed
            return f"usbip unbind -b {safe_busid}"
    
    @staticmethod
    def build_systemctl_command(action: str, service: str, password: str, remote_execution: bool = False) -> Optional[str]:
        """Build a secure systemctl command
        
        Args:
            action: The systemctl action (start, stop, restart, status)
            service: The service name (usbipd)
            password: The sudo password
            remote_execution: If True, always build the command (for SSH execution on remote Linux)
                            If False, check local platform compatibility
        """
        allowed_actions = {'start', 'stop', 'restart', 'status'}
        allowed_services = {'usbipd'}
        
        if action not in allowed_actions or service not in allowed_services:
            return None
        
        # For remote execution (SSH), always build the command regardless of local platform
        # For local execution, check if systemctl is available (not on Windows)
        if not remote_execution and platform.system() == "Windows":
            # Local Windows execution - systemctl not available
            return None
        else:
            # Remote execution or local Unix - build systemctl command
            safe_password = SecurityValidator.sanitize_for_shell(password)
            return f"echo {safe_password} | sudo -S systemctl {action} {service}"

    @staticmethod
    def build_modprobe_command(modules: str, password: str, remote_execution: bool = False) -> Optional[str]:
        """Build a secure modprobe command
        
        Args:
            modules: The kernel modules to load (space-separated)
            password: The sudo password
            remote_execution: If True, always build the command (for SSH execution on remote Linux)
                            If False, check local platform compatibility
        """
        # Validate modules - only allow specific USB/IP modules
        allowed_modules = {'usbip_host', 'usbip_core', 'vhci_hcd'}
        module_list = modules.split()
        
        for module in module_list:
            if module not in allowed_modules:
                return None
        
        # Sanitize module names for shell
        safe_modules = ' '.join(SecurityValidator.sanitize_for_shell(module) for module in module_list)
        
        # For remote execution (SSH), always build the command regardless of local platform
        # For local execution, check if modprobe is available (not on Windows)
        if not remote_execution and platform.system() == "Windows":
            # Local Windows execution - modprobe not available
            return None
        else:
            # Remote execution or local Unix - build modprobe command
            safe_password = SecurityValidator.sanitize_for_shell(password)
            return f"echo {safe_password} | sudo -S modprobe {safe_modules}"
