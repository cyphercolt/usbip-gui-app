#!/usr/bin/env python3
"""Test script to verify IPD Reset (systemctl) functionality for SSH remote execution"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_ipd_reset_commands():
    """Test that IPD Reset commands work correctly for remote SSH execution"""
    print("🔄 Testing IPD Reset (systemctl) Commands")
    print("=" * 50)
    
    from security.validator import SecureCommandBuilder
    import platform
    
    print(f"🖥️  Local platform: {platform.system()}")
    
    # Test local execution (should be None on Windows for systemctl)
    local_restart_cmd = SecureCommandBuilder.build_systemctl_command(
        "restart", "usbipd", "test_password", remote_execution=False
    )
    local_status_cmd = SecureCommandBuilder.build_systemctl_command(
        "status", "usbipd", "test_password", remote_execution=False
    )
    
    print(f"🏠 Local restart command: {local_restart_cmd}")
    print(f"🏠 Local status command: {local_status_cmd}")
    
    # Test remote execution (should always work regardless of local platform)
    remote_restart_cmd = SecureCommandBuilder.build_systemctl_command(
        "restart", "usbipd", "test_password", remote_execution=True
    )
    remote_status_cmd = SecureCommandBuilder.build_systemctl_command(
        "status", "usbipd", "test_password", remote_execution=True
    )
    
    print(f"🌐 Remote restart command: {remote_restart_cmd}")
    print(f"🌐 Remote status command: {remote_status_cmd}")
    
    # Verify the commands are correct
    print(f"\n📋 Verification:")
    
    if platform.system() == "Windows":
        if local_restart_cmd is None and local_status_cmd is None:
            print("✅ Local commands correctly disabled on Windows")
        else:
            print("❌ Local commands should be None on Windows")
    else:
        if local_restart_cmd and local_status_cmd:
            print("✅ Local commands available on Unix-like system")
        else:
            print("❌ Local commands should be available on Unix-like systems")
    
    if remote_restart_cmd and remote_status_cmd:
        print("✅ Remote commands available for SSH execution")
        
        # Verify command format
        if "sudo -S systemctl restart usbipd" in remote_restart_cmd:
            print("✅ Remote restart command format correct")
        else:
            print("❌ Remote restart command format incorrect")
            
        if "sudo -S systemctl status usbipd" in remote_status_cmd:
            print("✅ Remote status command format correct")
        else:
            print("❌ Remote status command format incorrect")
    else:
        print("❌ Remote commands should always be available")
    
    print(f"\n🎯 IPD Reset Button Status:")
    if platform.system() == "Windows":
        print("✅ Should work when SSH'd into Linux system")
        print("✅ Commands will execute on remote Linux machine")
        print("⚠️  Will not work for local Windows operations (systemctl not available)")
    else:
        print("✅ Should work for both local and remote operations")

if __name__ == "__main__":
    test_ipd_reset_commands()
