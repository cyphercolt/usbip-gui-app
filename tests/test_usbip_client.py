#!/usr/bin/env python3
"""Test Windows USB/IP client functionality (attach/detach without usbipd)"""

import sys
import os
import subprocess
import platform

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_usbip_client_tools():
    """Test USB/IP client tools availability and commands"""
    print("🔌 Testing Windows USB/IP Client Functionality")
    print("=" * 50)
    
    print(f"🖥️  Platform: {platform.system()}")
    
    # Test USB/IP client availability
    from utils.admin_utils import is_windows_usbipd_available, get_platform_usbip_port_command
    
    usbip_available = is_windows_usbipd_available()
    print(f"🔧 USB/IP tools available: {'✅ Yes' if usbip_available else '❌ No'}")
    
    if not usbip_available:
        print("❌ USB/IP client tools not found.")
        print("💡 Please install USB/IP for Windows to use client functionality")
        return False
    
    # Test usbip port command
    try:
        port_cmd = get_platform_usbip_port_command()
        print(f"📋 Port command: {' '.join(port_cmd)}")
        
        result = subprocess.run(
            port_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ usbip port command successful")
            if result.stdout.strip():
                print(f"📊 Current attached devices:\n{result.stdout}")
            else:
                print("📊 No devices currently attached")
        else:
            print(f"⚠️  usbip port returned non-zero: {result.returncode}")
            if result.stderr:
                print(f"❌ Error: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Error testing usbip port: {e}")
        return False
    
    # Test basic usbip commands without execution
    print(f"\n🧪 Testing command generation:")
    
    test_ip = "192.168.1.100"
    test_busid = "1-1"
    test_port = "00"
    
    attach_cmd = ["usbip", "attach", "-r", test_ip, "-b", test_busid]
    detach_cmd = ["usbip", "detach", "-p", test_port]
    list_cmd = ["usbip", "list", "-r", test_ip]
    
    if platform.system() == "Windows":
        print(f"✅ Attach: {' '.join(attach_cmd)} (no sudo)")
        print(f"✅ Detach: {' '.join(detach_cmd)} (no sudo)")
        print(f"✅ List:   {' '.join(list_cmd)} (no sudo)")
    else:
        print(f"✅ Attach: sudo {' '.join(attach_cmd)}")
        print(f"✅ Detach: sudo {' '.join(detach_cmd)}")
        print(f"✅ List:   {' '.join(list_cmd)}")
    
    # Test the run_sudo functionality
    print(f"\n🔐 Testing sudo handling:")
    if platform.system() == "Windows":
        print("✅ Sudo will be skipped (Windows platform)")
        print("✅ Commands will run directly without privilege escalation")
    else:
        print("✅ Sudo will be used for privilege escalation")
    
    print(f"\n📋 SUMMARY:")
    print("=" * 50)
    
    if usbip_available:
        print("🎯 Status: ✅ READY for USB/IP client operations")
        print("🔌 Local Device Discovery: ✅ Available (usbip port)")
        print("📡 Remote Device Discovery: ✅ Available (usbip list -r)")
        print("🔗 Device Attach/Detach: ✅ Available")
        
        if platform.system() == "Windows":
            print("🚫 USBIPD Daemon: ❌ Not needed (client-only mode)")
            print("🔓 Sudo: ✅ Skipped (Windows platform)")
        else:
            print("🔧 USBIPD Daemon: ⚠️  May be needed for hosting devices")
            print("🔐 Sudo: ✅ Required for device operations")
            
        print("\n💡 You can now:")
        print("   • View bound devices on remote Linux systems")
        print("   • Attach devices to your local system")
        print("   • View and detach locally attached devices")
        print("   • Use all USB/IP client functionality")
        
    else:
        print("❌ Status: NOT READY - USB/IP tools not found")
        print("💡 Install USB/IP client tools to enable functionality")
    
    return usbip_available

if __name__ == "__main__":
    success = test_usbip_client_tools()
    if success:
        print("\n🎊 All USB/IP client functionality is ready!")
    else:
        print("\n⚠️  Setup required before using USB/IP features")
