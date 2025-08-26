import base64
import hashlib
import json
import os
import platform
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class FileEncryption:
    """Simple file encryption for app state files"""
    
    def __init__(self):
        self._key = None
    
    def _get_system_key(self):
        """Generate a key based on system characteristics"""
        if self._key is not None:
            return self._key
            
        # Combine various system identifiers to create a unique key
        system_info = {
            'hostname': platform.node(),
            'system': platform.system(),
            'machine': platform.machine(),
            'processor': platform.processor()[:50],  # Limit length
        }
        
        # Add some file system info for uniqueness
        try:
            stat = os.stat('/')
            system_info['fs_id'] = str(stat.st_dev)
        except:
            system_info['fs_id'] = 'unknown'
        
        # Create a deterministic string from system info
        key_string = json.dumps(system_info, sort_keys=True)
        
        # Derive encryption key using PBKDF2
        salt = b"usbip_gui_salt_v1"  # Static salt for consistency
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_string.encode()))
        self._key = key
        return key
    
    def encrypt_data(self, data):
        """Encrypt a dictionary to base64 string"""
        try:
            json_str = json.dumps(data)
            fernet = Fernet(self._get_system_key())
            encrypted_bytes = fernet.encrypt(json_str.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            print(f"Encryption error: {e}")
            return None
    
    def decrypt_data(self, encrypted_str):
        """Decrypt base64 string to dictionary"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_str.encode())
            fernet = Fernet(self._get_system_key())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def save_encrypted_file(self, filepath, data):
        """Save data to encrypted file"""
        encrypted_str = self.encrypt_data(data)
        if encrypted_str:
            with open(filepath, 'w') as f:
                f.write(encrypted_str)
            return True
        return False
    
    def load_encrypted_file(self, filepath):
        """Load data from encrypted file"""
        try:
            if not os.path.exists(filepath):
                return {}
            
            with open(filepath, 'r') as f:
                encrypted_str = f.read().strip()
            
            if not encrypted_str:
                return {}
                
            return self.decrypt_data(encrypted_str) or {}
        except Exception as e:
            print(f"Error loading encrypted file {filepath}: {e}")
            return {}


class MemoryProtection:
    """Simple memory protection for sensitive data"""
    
    @staticmethod
    def obfuscate_string(text, key="usbip_memory_key"):
        """Simple XOR obfuscation for in-memory strings"""
        if not text:
            return ""
        
        key_bytes = (key * ((len(text) // len(key)) + 1))[:len(text)]
        return ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(text, key_bytes))
    
    @staticmethod
    def deobfuscate_string(obfuscated, key="usbip_memory_key"):
        """Reverse XOR obfuscation"""
        return MemoryProtection.obfuscate_string(obfuscated, key)  # XOR is reversible
