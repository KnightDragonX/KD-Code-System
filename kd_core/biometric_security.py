"""
Biometric-Enhanced Security Module for KD-Code System
Implements biometric authentication for enhanced security
"""

import hashlib
import hmac
import secrets
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging
import os
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class BiometricAuthenticator:
    """
    Provides biometric-enhanced security for KD-Code system
    """
    
    def __init__(self, secret_key: Optional[bytes] = None):
        """
        Initialize the biometric authenticator
        
        Args:
            secret_key: Secret key for encryption (if None, generates a new one)
        """
        if secret_key is None:
            self.secret_key = Fernet.generate_key()
        else:
            self.secret_key = secret_key
        
        self.cipher_suite = Fernet(self.secret_key)
        self.biometric_templates = {}  # In production, use a secure database
        self.authenticated_sessions = {}  # Store authenticated sessions
        self.max_attempts = 3  # Max authentication attempts before lockout
        self.lockout_duration = 300  # Lockout duration in seconds (5 minutes)
    
    def enroll_biometric_template(self, user_id: str, biometric_data: str) -> str:
        """
        Enroll a new biometric template for a user
        
        Args:
            user_id: Unique identifier for the user
            biometric_data: Biometric data (e.g., fingerprint hash, facial features)
        
        Returns:
            Enrollment ID for the biometric template
        """
        enrollment_id = secrets.token_hex(16)
        
        # Create a secure hash of the biometric data
        salt = secrets.token_bytes(16)
        biometric_hash = self._hash_biometric_data(biometric_data, salt)
        
        # Store the biometric template securely
        self.biometric_templates[user_id] = {
            'enrollment_id': enrollment_id,
            'biometric_hash': biometric_hash,
            'salt': base64.b64encode(salt).decode(),
            'created_at': datetime.utcnow().isoformat(),
            'failed_attempts': 0,
            'locked_until': None
        }
        
        return enrollment_id
    
    def authenticate_with_biometrics(self, user_id: str, biometric_data: str) -> Tuple[bool, Optional[str]]:
        """
        Authenticate a user using biometric data
        
        Args:
            user_id: User identifier
            biometric_data: Biometric data to verify
        
        Returns:
            Tuple of (is_authenticated, session_token)
        """
        if user_id not in self.biometric_templates:
            return False, None
        
        template = self.biometric_templates[user_id]
        
        # Check if account is locked
        if template['locked_until']:
            locked_until = datetime.fromisoformat(template['locked_until'])
            if datetime.utcnow() < locked_until:
                return False, "Account temporarily locked due to failed attempts"
        
        # Hash the provided biometric data with the stored salt
        salt = base64.b64decode(template['salt'].encode())
        provided_hash = self._hash_biometric_data(biometric_data, salt)
        
        # Compare hashes securely
        if hmac.compare_digest(template['biometric_hash'], provided_hash):
            # Reset failed attempts on successful authentication
            template['failed_attempts'] = 0
            template['locked_until'] = None
            
            # Generate a session token
            session_token = self._generate_session_token(user_id)
            self.authenticated_sessions[session_token] = {
                'user_id': user_id,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(hours=2)  # 2-hour session
            }
            
            return True, session_token
        else:
            # Increment failed attempts
            template['failed_attempts'] += 1
            
            # Lock account if too many failed attempts
            if template['failed_attempts'] >= self.max_attempts:
                template['locked_until'] = (
                    datetime.utcnow() + timedelta(seconds=self.lockout_duration)
                ).isoformat()
            
            return False, "Biometric authentication failed"
    
    def verify_session_token(self, session_token: str) -> bool:
        """
        Verify if a session token is valid
        
        Args:
            session_token: Session token to verify
        
        Returns:
            True if token is valid, False otherwise
        """
        if session_token not in self.authenticated_sessions:
            return False
        
        session = self.authenticated_sessions[session_token]
        
        # Check if session has expired
        if datetime.utcnow() > session['expires_at']:
            del self.authenticated_sessions[session_token]
            return False
        
        return True
    
    def get_user_from_session(self, session_token: str) -> Optional[str]:
        """
        Get user ID from a session token
        
        Args:
            session_token: Session token to look up
        
        Returns:
            User ID if token is valid, None otherwise
        """
        if not self.verify_session_token(session_token):
            return None
        
        return self.authenticated_sessions[session_token]['user_id']
    
    def _hash_biometric_data(self, biometric_data: str, salt: bytes) -> str:
        """
        Securely hash biometric data with salt
        
        Args:
            biometric_data: Raw biometric data
            salt: Salt for hashing
        
        Returns:
            Hashed biometric data as hex string
        """
        # Combine biometric data with salt
        combined_data = biometric_data.encode() + salt
        
        # Create hash
        hash_obj = hashlib.sha256(combined_data)
        return hash_obj.hexdigest()
    
    def _generate_session_token(self, user_id: str) -> str:
        """
        Generate a secure session token
        
        Args:
            user_id: User ID for the session
        
        Returns:
            Session token
        """
        token_data = f"{user_id}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
        return self.cipher_suite.encrypt(token_data.encode()).decode()
    
    def encrypt_sensitive_data(self, data: str, user_id: str) -> str:
        """
        Encrypt sensitive data using biometric-enhanced security
        
        Args:
            data: Data to encrypt
            user_id: User ID for context
        
        Returns:
            Encrypted data as base64 string
        """
        # Create a key derived from user's biometric template (if enrolled)
        if user_id in self.biometric_templates:
            salt = base64.b64decode(self.biometric_templates[user_id]['salt'].encode())
            # Derive a key from the biometric template
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(user_id.encode()))
            cipher = Fernet(key)
            encrypted_data = cipher.encrypt(data.encode())
        else:
            # Fallback to standard encryption
            encrypted_data = self.cipher_suite.encrypt(data.encode())
        
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str, user_id: str) -> Optional[str]:
        """
        Decrypt sensitive data using biometric-enhanced security
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            user_id: User ID for context
        
        Returns:
            Decrypted data or None if decryption fails
        """
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            
            # Try to decrypt using biometric-derived key first
            if user_id in self.biometric_templates:
                salt = base64.b64decode(self.biometric_templates[user_id]['salt'].encode())
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(user_id.encode()))
                cipher = Fernet(key)
                decrypted_data = cipher.decrypt(encrypted_bytes)
            else:
                # Fallback to standard decryption
                decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            
            return decrypted_data.decode()
        except Exception:
            return None
    
    def generate_secure_kd_code(self, text: str, user_id: str, require_biometric: bool = False) -> Optional[str]:
        """
        Generate a KD-Code with biometric-enhanced security
        
        Args:
            text: Text to encode
            user_id: User ID requesting generation
            require_biometric: Whether biometric authentication is required
        
        Returns:
            Secure KD-Code or None if authentication fails
        """
        if require_biometric:
            # In a real implementation, you would check for an active biometric session
            # For this example, we'll just check if the user has a biometric template
            if user_id not in self.biometric_templates:
                return None  # Biometric authentication required but not enrolled
        
        # In a real implementation, you might embed user-specific information
        # or apply additional security measures based on biometric verification
        from kd_core.encoder import generate_kd_code
        
        # Add a biometric security marker to the text if needed
        if require_biometric:
            secure_text = f"[SECURE:{user_id[:8]}]{text}"
        else:
            secure_text = text
        
        return generate_kd_code(secure_text)
    
    def validate_secure_kd_code(self, kd_code_image: bytes, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a KD-Code with biometric-enhanced security
        
        Args:
            kd_code_image: KD-Code image data
            user_id: User ID attempting validation
        
        Returns:
            Tuple of (is_valid, decoded_text)
        """
        from kd_core.decoder import decode_kd_code
        
        decoded_text = decode_kd_code(kd_code_image)
        
        if decoded_text and decoded_text.startswith("[SECURE:"):
            # This is a secure code that requires biometric validation
            if user_id not in self.biometric_templates:
                return False, "Biometric authentication required for this code"
            
            # Extract the user ID from the secure marker
            try:
                end_marker = decoded_text.find(']')
                if end_marker != -1:
                    embedded_user = decoded_text[9:end_marker]  # Extract user ID after "[SECURE:"
                    actual_text = decoded_text[end_marker+1:]  # Remaining text after marker
                    
                    # Verify that the requesting user matches the embedded user
                    if user_id in self.biometric_templates:
                        # In a real system, you would verify the biometric authentication
                        # For this example, we'll just return the actual text
                        return True, actual_text
            except:
                pass
            
            return False, "Unauthorized access to secure code"
        
        # Regular KD-Code, no biometric validation needed
        return True, decoded_text


# Global biometric authenticator instance
biometric_auth = BiometricAuthenticator()


def initialize_biometric_security(secret_key: Optional[bytes] = None):
    """
    Initialize the biometric security system
    
    Args:
        secret_key: Optional secret key for encryption
    """
    global biometric_auth
    biometric_auth = BiometricAuthenticator(secret_key)


def enroll_user_biometric(user_id: str, biometric_data: str) -> str:
    """
    Enroll a user's biometric template
    
    Args:
        user_id: User identifier
        biometric_data: Biometric data (fingerprint, facial features, etc.)
    
    Returns:
        Enrollment ID
    """
    return biometric_auth.enroll_biometric_template(user_id, biometric_data)


def authenticate_user_with_biometrics(user_id: str, biometric_data: str) -> Tuple[bool, Optional[str]]:
    """
    Authenticate a user using biometric data
    
    Args:
        user_id: User identifier
        biometric_data: Biometric data to verify
    
    Returns:
        Tuple of (is_authenticated, session_token)
    """
    return biometric_auth.authenticate_with_biometrics(user_id, biometric_data)


def verify_biometric_session(session_token: str) -> bool:
    """
    Verify a biometric-authenticated session
    
    Args:
        session_token: Session token to verify
    
    Returns:
        True if session is valid, False otherwise
    """
    return biometric_auth.verify_session_token(session_token)


def get_user_from_biometric_session(session_token: str) -> Optional[str]:
    """
    Get user ID from a biometric-authenticated session
    
    Args:
        session_token: Session token to look up
    
    Returns:
        User ID if token is valid, None otherwise
    """
    return biometric_auth.get_user_from_session(session_token)


def encrypt_with_biometric_protection(data: str, user_id: str) -> str:
    """
    Encrypt data with biometric-enhanced protection
    
    Args:
        data: Data to encrypt
        user_id: User ID for context
    
    Returns:
        Encrypted data as base64 string
    """
    return biometric_auth.encrypt_sensitive_data(data, user_id)


def decrypt_with_biometric_protection(encrypted_data: str, user_id: str) -> Optional[str]:
    """
    Decrypt data with biometric-enhanced protection
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        user_id: User ID for context
    
    Returns:
        Decrypted data or None if decryption fails
    """
    return biometric_auth.decrypt_sensitive_data(encrypted_data, user_id)


def generate_secure_kd_code_with_biometrics(text: str, user_id: str, require_biometric: bool = False) -> Optional[str]:
    """
    Generate a KD-Code with biometric-enhanced security
    
    Args:
        text: Text to encode
        user_id: User ID requesting generation
        require_biometric: Whether biometric authentication is required
    
    Returns:
        Secure KD-Code or None if authentication fails
    """
    return biometric_auth.generate_secure_kd_code(text, user_id, require_biometric)


def validate_secure_kd_code_with_biometrics(kd_code_image: bytes, user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a KD-Code with biometric-enhanced security
    
    Args:
        kd_code_image: KD-Code image data
        user_id: User ID attempting validation
    
    Returns:
        Tuple of (is_valid, decoded_text)
    """
    return biometric_auth.validate_secure_kd_code(kd_code_image, user_id)


# Example usage
if __name__ == "__main__":
    # Example of enrolling a user
    user_id = "user123"
    fake_biometric_data = "fingerprint_pattern_abc123"  # In reality, this would be actual biometric data
    
    enrollment_id = enroll_user_biometric(user_id, fake_biometric_data)
    print(f"Enrolled user {user_id} with enrollment ID: {enrollment_id}")
    
    # Example of authenticating with biometric data
    is_authenticated, session_token = authenticate_user_with_biometrics(user_id, fake_biometric_data)
    print(f"Authentication result: {is_authenticated}, Session token: {session_token is not None}")
    
    # Example of generating a secure KD-Code
    if is_authenticated:
        secure_kd_code = generate_secure_kd_code_with_biometrics(
            "This is a secure message", 
            user_id, 
            require_biometric=True
        )
        print(f"Generated secure KD-Code: {secure_kd_code[:50]}..." if secure_kd_code else "Failed to generate secure KD-Code")
    
    # Example of encrypting sensitive data
    sensitive_data = "This is sensitive information"
    encrypted = encrypt_with_biometric_protection(sensitive_data, user_id)
    print(f"Encrypted data: {encrypted[:50]}...")
    
    # Example of decrypting sensitive data
    decrypted = decrypt_with_biometric_protection(encrypted, user_id)
    print(f"Decrypted data: {decrypted}")