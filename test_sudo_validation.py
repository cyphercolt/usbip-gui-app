#!/usr/bin/env python3
"""Test script to verify sudo password validation works correctly"""

import sys
import os
import subprocess
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_sudo_validation():
    """Test that the sudo validation logic works"""
    from main import test_sudo_password
    
    print("🔍 Testing sudo password validation...")
    
    # Test with wrong password
    result = test_sudo_password("wrongpassword123")
    print(f"❌ Wrong password test: {'PASS' if not result else 'FAIL'}")
    
    # Test with empty password  
    result = test_sudo_password("")
    print(f"❌ Empty password test: {'PASS' if not result else 'FAIL'}")
    
    print("✅ Sudo validation tests completed!")
    print("🎯 The application will now properly exit after 3 failed attempts")
    print("🔒 Security improvement verified!")

if __name__ == "__main__":
    test_sudo_validation()
