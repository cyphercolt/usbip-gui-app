"""
Admin privilege utilities for Windows platform
"""

import sys
import os
import platform
import subprocess
import ctypes


def is_admin():
    """Check if the current process is running with administrator privileges"""
    if platform.system() != "Windows":
        # On Unix-like systems, check if running as root
        return os.geteuid() == 0
    
    try:
        # Check if running as admin on Windows
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """Re-launch the current script with administrator privileges on Windows"""
    if platform.system() != "Windows":
        print("Admin elevation is only supported on Windows")
        return False
    
    if is_admin():
        # Already running as admin
        return True
    
    try:
        # Re-run the current script with admin privileges
        script = sys.argv[0]
        params = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
        
        # Use ShellExecute to run with elevated privileges
        result = ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            sys.executable, 
            f'"{script}" {params}', 
            None, 
            1  # SW_SHOWNORMAL
        )
        
        # If successful, exit the current process
        if result > 32:  # Success
            return True
        else:
            print(f"Failed to elevate privileges. Error code: {result}")
            return False
            
    except Exception as e:
        print(f"Error elevating privileges: {e}")
        return False


def check_and_elevate():
    """Check if admin privileges are needed and elevate if necessary"""
    if platform.system() != "Windows":
        # On Unix-like systems, don't need to elevate here
        return True
    
    if not is_admin():
        print("🔒 Administrator privileges required for network operations on Windows")
        print("🚀 Attempting to elevate privileges...")
        
        if run_as_admin():
            # The process has been re-launched with admin privileges
            # Exit the current non-admin process
            sys.exit(0)
        else:
            print("❌ Failed to obtain administrator privileges")
            print("⚠️  Some network operations may not work correctly")
            return False
    
    print("✅ Running with administrator privileges")
    return True


def get_platform_ping_command(ip_address, count=1, timeout=5):
    """Get the appropriate ping command for the current platform"""
    if platform.system() == "Windows":
        # Windows ping syntax: ping -n count -w timeout_ms ip
        timeout_ms = timeout * 1000
        return ["ping", "-n", str(count), "-w", str(timeout_ms), ip_address]
    else:
        # Unix-like ping syntax: ping -c count -W timeout ip
        return ["ping", "-c", str(count), "-W", str(timeout), ip_address]


def format_ping_output_message(ip_address, count=1, timeout=5):
    """Get the appropriate ping command string for display purposes"""
    if platform.system() == "Windows":
        timeout_ms = timeout * 1000
        return f"$ ping -n {count} -w {timeout_ms} {ip_address}"
    else:
        return f"$ ping -c {count} -W {timeout} {ip_address}"


def get_platform_usbip_port_command():
    """Get the appropriate usbip port command for the current platform"""
    # Both Windows and Unix use the same usbip port command
    return ["usbip", "port"]


def is_windows_usbipd_available():
    """Check if Windows USB/IP client tools are available (not the daemon)"""
    if platform.system() != "Windows":
        return True  # On Unix-like systems, assume standard usbip tools
    
    try:
        result = subprocess.run(
            ["usbip", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_platform_usbip_list_command(ip_address):
    """Get the appropriate command to list remote USB/IP devices for the current platform"""
    # Both Windows client and Unix use standard usbip syntax
    return ["usbip", "list", "-r", ip_address]


def get_platform_usbip_attach_command(ip_address, busid):
    """Get the appropriate command to attach a USB/IP device for the current platform"""
    # Both Windows client and Unix use standard usbip syntax
    return ["usbip", "attach", "-r", ip_address, "-b", busid]


def get_platform_usbip_detach_command(port_or_busid):
    """Get the appropriate command to detach a USB/IP device for the current platform"""
    # Both Windows client and Unix use standard usbip syntax with port number
    return ["usbip", "detach", "-p", port_or_busid]
