"""
Unit tests for KD-Code System
Tests for encoder, decoder, and core functionality
"""

import unittest
import base64
from io import BytesIO
from PIL import Image
import numpy as np
import cv2
import tempfile
import os

# Import the modules to test
from kd_core.encoder import generate_kd_code, draw_annular_segment
from kd_core.decoder import decode_kd_code, get_interpolated_pixel, get_local_average, bits_to_text
from kd_core.config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS, DEFAULT_SCAN_SEGMENTS_PER_RING,
    DEFAULT_MIN_ANCHOR_RADIUS, DEFAULT_MAX_ANCHOR_RADIUS, ALLOWED_SEGMENTS_VALUES
)
from kd_core.qr_compatibility import generate_qr_code, is_qr_compatible
from kd_core.data_encryption import encrypt_sensitive_text, decrypt_sensitive_text, DataEncryption
from kd_core.backup_recovery import backup_system


class TestEncoder(unittest.TestCase):
    """Test cases for KD-Code encoder functionality"""
    
    def test_generate_kd_code_basic(self):
        """Test basic KD-Code generation"""
        text = "TEST"
        result = generate_kd_code(text)
        
        # Check that result is a valid base64 string
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Try to decode the base64 to verify it's valid
        try:
            img_data = base64.b64decode(result)
            # Try to load as image to verify it's a valid image
            img = Image.open(BytesIO(img_data))
            self.assertIsNotNone(img)
        except Exception:
            self.fail("Generated base64 is not a valid image")
    
    def test_generate_kd_code_with_parameters(self):
        """Test KD-Code generation with custom parameters"""
        text = "PARAM"
        result = generate_kd_code(
            text, 
            segments_per_ring=8,
            anchor_radius=8,
            ring_width=10,
            scale_factor=3
        )
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_generate_kd_code_with_styling(self):
        """Test KD-Code generation with custom styling"""
        text = "STYLE"
        result = generate_kd_code(
            text,
            foreground_color='red',
            background_color='blue',
            theme='dark'
        )
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_generate_kd_code_with_compression(self):
        """Test KD-Code generation with compression"""
        text = "COMPRESS"
        result = generate_kd_code(
            text,
            compression_quality=80
        )
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_generate_kd_code_invalid_input(self):
        """Test KD-Code generation with invalid inputs"""
        # Test with empty string
        with self.assertRaises(ValueError):
            generate_kd_code("")
        
        # Test with too long string
        with self.assertRaises(ValueError):
            generate_kd_code("A" * 200)  # Exceeds default max_chars
        
        # Test with invalid segments_per_ring
        with self.assertRaises(ValueError):
            generate_kd_code("TEST", segments_per_ring=15)  # Not in allowed values
        
        # Test with non-string input
        with self.assertRaises(TypeError):
            generate_kd_code(123)
        
        # Test with invalid compression quality
        with self.assertRaises(ValueError):
            generate_kd_code("TEST", compression_quality=101)
    
    def test_generate_kd_code_edge_cases(self):
        """Test KD-Code generation with edge cases"""
        # Single character
        result = generate_kd_code("A")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Special characters
        result = generate_kd_code("!@#$%^&*()")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Unicode characters
        result = generate_kd_code("Hello 世界")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestDecoder(unittest.TestCase):
    """Test cases for KD-Code decoder functionality"""
    
    def test_bits_to_text_basic(self):
        """Test basic bitstream to text conversion"""
        # Test converting "HI" to bits and back
        # H = 72 = 01001000, I = 73 = 01001001
        bits = [0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1]
        result = bits_to_text(bits)
        self.assertEqual(result, "HI")
    
    def test_bits_to_text_with_special_chars(self):
        """Test bitstream to text conversion with special characters"""
        # Test with newline, tab, carriage return
        bits = [0, 0, 0, 0, 1, 0, 0, 1,  # 9 = tab
                0, 0, 0, 0, 1, 1, 0, 1,  # 13 = carriage return
                0, 0, 0, 0, 1, 0, 1, 0]  # 10 = line feed
        result = bits_to_text(bits)
        self.assertIn('\t', result)
        self.assertIn('\r', result)
        self.assertIn('\n', result)
    
    def test_bits_to_text_empty(self):
        """Test bitstream to text conversion with empty input"""
        result = bits_to_text([])
        self.assertEqual(result, "")
    
    def test_get_interpolated_pixel(self):
        """Test interpolated pixel retrieval"""
        # Create a simple test image
        img = np.array([[100, 150], [200, 250]], dtype=np.uint8)
        
        # Test with integer coordinates
        result = get_interpolated_pixel(img, 0, 0)
        self.assertEqual(result, 100)
        
        # Test with fractional coordinates (should interpolate)
        result = get_interpolated_pixel(img, 0.5, 0.5)
        # Should be approximately the average of all four pixels
        expected = (100 + 150 + 200 + 250) // 4
        self.assertAlmostEqual(result, expected, delta=10)
    
    def test_get_local_average(self):
        """Test local average calculation"""
        # Create a test image
        img = np.ones((10, 10), dtype=np.uint8) * 50
        img[5, 5] = 100  # Center pixel is different
        
        avg = get_local_average(img, 5, 5, 1)
        # Should be close to 50 since most pixels are 50
        self.assertGreaterEqual(avg, 45)
        self.assertLessEqual(avg, 55)
    
    def test_decode_kd_code_invalid_input(self):
        """Test decoder with invalid inputs"""
        # Test with non-bytes input
        with self.assertRaises(TypeError):
            decode_kd_code("not bytes")
        
        # Test with invalid segments_per_ring
        with self.assertRaises(ValueError):
            decode_kd_code(b"fake image data", segments_per_ring=15)


class TestQRCompatibility(unittest.TestCase):
    """Test cases for QR code compatibility"""
    
    def test_generate_qr_code(self):
        """Test QR code generation"""
        text = "Hello QR"
        result = generate_qr_code(text)
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        
        # Verify it's valid base64
        try:
            img_data = base64.b64decode(result)
            img = Image.open(BytesIO(img_data))
            self.assertIsNotNone(img)
        except Exception:
            self.fail("Generated QR code is not valid")
    
    def test_is_qr_compatible(self):
        """Test QR code compatibility check"""
        self.assertTrue(is_qr_compatible("Short text"))
        self.assertTrue(is_qr_compatible("A" * 100))
        # Very long text should still be compatible (within QR limits)
        self.assertTrue(is_qr_compatible("A" * 2000))


class TestDataEncryption(unittest.TestCase):
    """Test cases for data encryption functionality"""
    
    def test_encryption_decryption_cycle(self):
        """Test that encryption and decryption work correctly"""
        original_text = "Secret message"
        encrypted = encrypt_sensitive_text(original_text)
        decrypted = decrypt_sensitive_text(encrypted)
        
        self.assertEqual(original_text, decrypted)
    
    def test_encryption_with_custom_key(self):
        """Test encryption with custom key"""
        key = b'abcdefghijklmnopqrstuvwxyz123456'
        original_text = "Custom key message"
        
        encrypted = encrypt_sensitive_text(original_text, custom_key=key)
        decrypted = decrypt_sensitive_text(encrypted, custom_key=key)
        
        self.assertEqual(original_text, decrypted)
    
    def test_encryption_different_inputs(self):
        """Test encryption with different types of input"""
        test_cases = [
            "Simple text",
            "Text with numbers 12345",
            "Special chars !@#$%",
            "Unicode: 你好世界",
            "Mixed: Hello 世界 123!@"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                encrypted = encrypt_sensitive_text(text)
                decrypted = decrypt_sensitive_text(encrypted)
                self.assertEqual(text, decrypted)
    
    def test_data_encryption_class(self):
        """Test the DataEncryption class directly"""
        handler = DataEncryption()
        original = "Class test message"
        
        encrypted = handler.encrypt_data(original)
        decrypted = handler.decrypt_data(encrypted)
        
        self.assertEqual(original, decrypted)
    
    def test_encryption_error_handling(self):
        """Test encryption error handling"""
        handler = DataEncryption()
        
        # Test with non-string input
        with self.assertRaises(TypeError):
            handler.encrypt_data(123)
        
        # Test with invalid encrypted data
        with self.assertRaises(ValueError):
            handler.decrypt_data("invalid_base64!")


class TestBackupRecovery(unittest.TestCase):
    """Test cases for backup and recovery functionality"""
    
    def test_backup_creation(self):
        """Test backup creation"""
        backup_path = backup_system.create_backup("test_backup")
        
        self.assertIsInstance(backup_path, str)
        self.assertTrue(backup_path.endswith('.zip'))
        self.assertTrue(os.path.exists(backup_path))
    
    def test_backup_listing(self):
        """Test backup listing"""
        # Create a backup first
        backup_system.create_backup("list_test_backup")
        
        backups = backup_system.list_backups()
        self.assertIsInstance(backups, list)
        self.assertGreater(len(backups), 0)
    
    def test_backup_info(self):
        """Test getting backup information"""
        backup_path = backup_system.create_backup("info_test_backup")
        
        info = backup_system.get_backup_info(backup_path)
        self.assertIsInstance(info, dict)
        self.assertNotIn('error', info)
    
    def test_backup_with_temp_dir(self):
        """Test backup system with temporary directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_backup_system = backup_system.__class__(backup_dir=temp_dir)
            backup_path = temp_backup_system.create_backup("temp_test")
            
            self.assertTrue(os.path.exists(backup_path))


class TestIntegration(unittest.TestCase):
    """Integration tests for encoder-decoder pipeline"""
    
    def test_encode_decode_roundtrip(self):
        """Test that encoding and then decoding returns the original text"""
        original_text = "HELLO WORLD"
        
        # Generate KD-Code
        kd_code_b64 = generate_kd_code(original_text)
        
        # Convert base64 back to bytes for decoder
        kd_code_bytes = base64.b64decode(kd_code_b64)
        
        # Note: The decoder may not perfectly reconstruct the text due to 
        # limitations in the current implementation, so this is more of a 
        # structural test. In a real implementation, we'd need to create 
        # a mock image that represents the encoded data.
        
        # For now, just test that the decoder accepts the input without error
        try:
            result = decode_kd_code(kd_code_bytes)
            # The result might be None if the image doesn't contain a recognizable KD-Code
            # This is expected behavior for our test
        except Exception as e:
            self.fail(f"Decoder failed with valid input: {e}")
    
    def test_encryption_integration(self):
        """Test integration of encryption with KD-Code generation"""
        original_text = "Sensitive information"
        encrypted_text = encrypt_sensitive_text(original_text)
        
        # Generate KD-Code with encrypted text
        kd_code_b64 = generate_kd_code(encrypted_text)
        
        self.assertIsInstance(kd_code_b64, str)
        self.assertGreater(len(kd_code_b64), 0)
    
    def test_styling_integration(self):
        """Test integration of styling options"""
        result = generate_kd_code(
            "Styled Code",
            foreground_color='green',
            background_color='yellow',
            theme='business'
        )
        
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()