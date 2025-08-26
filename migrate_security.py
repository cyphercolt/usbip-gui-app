#!/usr/bin/env python3
"""
Migration script to convert existing JSON files to encrypted format
"""

import json
import os
import sys
sys.path.append('src')

from security.crypto import FileEncryption

def migrate_files():
    crypto = FileEncryption()
    
    # Migration mappings: old_file -> new_file
    migrations = {
        'ips.json': 'ips.enc',
        'usbip_state.json': 'usbip_state.enc', 
        'ssh_state.json': 'ssh_state.enc'
    }
    
    for old_file, new_file in migrations.items():
        if os.path.exists(old_file) and not os.path.exists(new_file):
            print(f"Migrating {old_file} to {new_file}...")
            
            try:
                with open(old_file, 'r') as f:
                    data = json.load(f)
                
                # Handle different file formats
                if old_file == 'ips.json':
                    # ips.json contains a list, wrap it in a dict
                    data = {'ips': data}
                
                # Save as encrypted
                if crypto.save_encrypted_file(new_file, data):
                    print(f"✅ Successfully migrated {old_file}")
                    # Backup the old file
                    os.rename(old_file, old_file + '.backup')
                    print(f"📦 Original file backed up as {old_file}.backup")
                else:
                    print(f"❌ Failed to migrate {old_file}")
                    
            except Exception as e:
                print(f"❌ Error migrating {old_file}: {e}")
        
        elif os.path.exists(new_file):
            print(f"ℹ️  {new_file} already exists, skipping migration")
        else:
            print(f"ℹ️  {old_file} not found, nothing to migrate")

if __name__ == "__main__":
    print("🔐 USBIP GUI Security Migration")
    print("Converting JSON files to encrypted format...")
    migrate_files()
    print("✨ Migration complete!")
