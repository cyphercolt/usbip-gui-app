"""Input validation and sanitization for security"""
import re
import ipaddress
import shlex
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
    def build_usbip_bind_command(busid: str, password: str) -> Optional[str]:
        """Build a secure usbip bind command"""
        if not SecurityValidator.validate_busid(busid):
            return None
        
        # Use proper shell escaping
        safe_busid = SecurityValidator.sanitize_for_shell(busid)
        safe_password = SecurityValidator.sanitize_for_shell(password)
        
        return f"echo {safe_password} | sudo -S usbip bind -b {safe_busid}"
    
    @staticmethod
    def build_usbip_unbind_command(busid: str, password: str) -> Optional[str]:
        """Build a secure usbip unbind command"""
        if not SecurityValidator.validate_busid(busid):
            return None
        
        # Use proper shell escaping
        safe_busid = SecurityValidator.sanitize_for_shell(busid)
        safe_password = SecurityValidator.sanitize_for_shell(password)
        
        return f"echo {safe_password} | sudo -S usbip unbind -b {safe_busid}"
    
    @staticmethod
    def build_systemctl_command(action: str, service: str, password: str) -> Optional[str]:
        """Build a secure systemctl command"""
        allowed_actions = {'start', 'stop', 'restart', 'status'}
        allowed_services = {'usbipd'}
        
        if action not in allowed_actions or service not in allowed_services:
            return None
        
        safe_password = SecurityValidator.sanitize_for_shell(password)
        
        return f"echo {safe_password} | sudo -S systemctl {action} {service}"
