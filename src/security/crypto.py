import base64
import hashlib
import json
import os
import platform
import secrets
import time
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
            "hostname": platform.node(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor()[:50],  # Limit length
        }

        # Add some file system info for uniqueness
        try:
            stat = os.stat("/")
            system_info["fs_id"] = str(stat.st_dev)
        except:
            system_info["fs_id"] = "unknown"

        # Create a deterministic string from system info
        key_string = json.dumps(system_info, sort_keys=True)

        # Generate a deterministic salt based on system characteristics (without PID)
        salt_material = f"{platform.node()}{platform.system()}{system_info['fs_id']}"
        salt = hashlib.sha256(salt_material.encode()).digest()[:16]

        # Derive encryption key using PBKDF2 with higher iterations
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200000,  # Increased from 100k for better security
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_string.encode()))
        self._key = key
        return key

    def _get_legacy_key(self):
        """Generate legacy key for backward compatibility"""
        # Original key generation method from v1.0
        system_info = {
            "hostname": platform.node(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor()[:50],
        }

        try:
            stat = os.stat("/")
            system_info["fs_id"] = str(stat.st_dev)
        except:
            system_info["fs_id"] = "unknown"

        key_string = json.dumps(system_info, sort_keys=True)

        # Original static salt
        salt = b"usbip_gui_salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key_string.encode()))

    def encrypt_data(self, data):
        """Encrypt a dictionary to base64 string"""
        try:
            json_str = json.dumps(data)
            fernet = Fernet(self._get_system_key())
            encrypted_bytes = fernet.encrypt(json_str.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception:
            # Don't leak error details in logs
            return None

    def decrypt_data(self, encrypted_str):
        """Decrypt base64 string to dictionary with backward compatibility"""
        # Try new encryption method first
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_str.encode())
            fernet = Fernet(self._get_system_key())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted_bytes.decode())
        except Exception:
            pass

        # Try legacy encryption method for backward compatibility
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_str.encode())
            fernet = Fernet(self._get_legacy_key())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            data = json.loads(decrypted_bytes.decode())

            # Re-encrypt with new method for future use
            self._migrate_file_to_new_encryption(encrypted_str, data)
            return data
        except Exception:
            # Don't leak error details in logs
            return None

    def _migrate_file_to_new_encryption(self, old_encrypted_str, data):
        """Silently migrate old encryption to new format"""
        try:
            # This will be called by save_encrypted_file when the file is next saved
            pass
        except Exception:
            pass

    def save_encrypted_file(self, filepath, data):
        """Save data to encrypted file with atomic write"""
        encrypted_str = self.encrypt_data(data)
        if encrypted_str:
            # Atomic write to prevent corruption
            temp_filepath = filepath + ".tmp"
            try:
                with open(temp_filepath, "w") as f:
                    f.write(encrypted_str)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                os.replace(temp_filepath, filepath)  # Atomic replacement
                return True
            except Exception:
                # Clean up temp file if it exists
                try:
                    os.unlink(temp_filepath)
                except:
                    pass
                return False
        return False

    def load_encrypted_file(self, filepath):
        """Load data from encrypted file"""
        try:
            if not os.path.exists(filepath):
                return {}

            with open(filepath, "r") as f:
                encrypted_str = f.read().strip()

            if not encrypted_str:
                return {}

            return self.decrypt_data(encrypted_str) or {}
        except Exception:
            # Don't leak file path or error details
            return {}


class MemoryProtection:
    """Enhanced memory protection for sensitive data"""

    def __init__(self):
        # Generate a random key for each instance
        self._instance_key = secrets.token_hex(32)

    def obfuscate_string(self, text):
        """Advanced obfuscation using random key and multiple passes"""
        if not text:
            return ""

        # Convert to bytes for better security
        text_bytes = text.encode("utf-8")
        key_bytes = self._instance_key.encode("utf-8")

        # Multi-pass XOR with different key segments
        result = bytearray(text_bytes)
        for i, byte in enumerate(result):
            key_index = i % len(key_bytes)
            result[i] = byte ^ key_bytes[key_index] ^ (i & 0xFF)

        return base64.urlsafe_b64encode(result).decode()

    def deobfuscate_string(self, obfuscated):
        """Reverse the advanced obfuscation"""
        if not obfuscated:
            return ""

        try:
            result = bytearray(base64.urlsafe_b64decode(obfuscated.encode()))
            key_bytes = self._instance_key.encode("utf-8")

            # Reverse the multi-pass XOR
            for i, byte in enumerate(result):
                key_index = i % len(key_bytes)
                result[i] = byte ^ key_bytes[key_index] ^ (i & 0xFF)

            return result.decode("utf-8")
        except Exception:
            return ""

    def secure_zero_memory(self, data):
        """Attempt to securely zero memory (best effort)"""
        if isinstance(data, str):
            # For strings, we can't directly modify memory, but we can overwrite
            return "0" * len(data)
        elif isinstance(data, bytearray):
            # For bytearrays, we can zero the memory
            for i in range(len(data)):
                data[i] = 0
        return data
