"""
Data Encryption Module for KD-Code System
Provides encryption for sensitive data stored in KD-Codes
"""

from cryptography.fernet import Fernet
import base64
import os


class DataEncryption:
    """Handles encryption and decryption of sensitive data"""
    
    def __init__(self, key=None):
        """
        Initialize the encryption handler
        
        Args:
            key (bytes, optional): Encryption key. If not provided, generates a new one.
        """
        if key:
            self.key = key
        else:
            # In production, store this key securely (e.g., environment variable)
            self.key = os.environ.get('ENCRYPTION_KEY', '').encode() or Fernet.generate_key()
        
        self.cipher_suite = Fernet(self.key)
    
    def encrypt_data(self, data):
        """
        Encrypt sensitive data
        
        Args:
            data (str): Data to encrypt
        
        Returns:
            str: Base64 encoded encrypted data
        """
        if not isinstance(data, str):
            raise TypeError("Data must be a string")
        
        # Encode the string to bytes
        data_bytes = data.encode('utf-8')
        
        # Encrypt the data
        encrypted_data = self.cipher_suite.encrypt(data_bytes)
        
        # Return as base64 string for easy transmission/storage
        return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
    
    def decrypt_data(self, encrypted_data):
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data (str): Base64 encoded encrypted data
        
        Returns:
            str: Decrypted data
        """
        if not isinstance(encrypted_data, str):
            raise TypeError("Encrypted data must be a string")
        
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt the data
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            
            # Return as string
            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def is_encrypted(self, data):
        """
        Check if data appears to be encrypted
        
        Args:
            data (str): Data to check
        
        Returns:
            bool: True if data appears to be encrypted
        """
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(data.encode('utf-8'))
            # If it's valid base64, it might be encrypted
            return True
        except Exception:
            return False


# Global encryption instance
encryption_handler = DataEncryption()


def encrypt_sensitive_text(text, custom_key=None):
    """
    Convenience function to encrypt sensitive text before encoding in KD-Code
    
    Args:
        text (str): Text to encrypt
        custom_key (bytes, optional): Custom encryption key
    
    Returns:
        str: Encrypted text
    """
    if custom_key:
        handler = DataEncryption(custom_key)
        return handler.encrypt_data(text)
    else:
        return encryption_handler.encrypt_data(text)


def decrypt_sensitive_text(encrypted_text, custom_key=None):
    """
    Convenience function to decrypt sensitive text after decoding from KD-Code
    
    Args:
        encrypted_text (str): Encrypted text to decrypt
        custom_key (bytes, optional): Custom encryption key
    
    Returns:
        str: Decrypted text
    """
    if custom_key:
        handler = DataEncryption(custom_key)
        return handler.decrypt_data(encrypted_text)
    else:
        return encryption_handler.decrypt_data(encrypted_text)


# Example usage
if __name__ == "__main__":
    # Example of encrypting and decrypting sensitive data
    sensitive_info = "This is confidential information"
    
    print(f"Original: {sensitive_info}")
    
    # Encrypt the data
    encrypted = encrypt_sensitive_text(sensitive_info)
    print(f"Encrypted: {encrypted}")
    
    # Decrypt the data
    decrypted = decrypt_sensitive_text(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # Verify they match
    print(f"Match: {sensitive_info == decrypted}")