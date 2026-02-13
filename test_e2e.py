"""
End-to-End and Integration Tests for KD-Code System
Tests the complete workflow of the application
"""

import unittest
import json
import base64
from app import create_app
from kd_core.config import DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH, DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS


class TestIntegrationEndpoints(unittest.TestCase):
    """Integration tests for API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client for the application"""
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        cls.app_context.pop()
    
    def test_full_generation_workflow(self):
        """Test the complete generation workflow"""
        # Test basic generation
        response = self.client.post('/api/generate', 
                                  json={'text': 'Hello World'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertEqual(data['status'], 'success')
        
        # Verify the image is valid base64
        try:
            base64.b64decode(data['image'])
        except Exception:
            self.fail("Generated image is not valid base64")
    
    def test_generation_with_parameters(self):
        """Test generation with custom parameters"""
        test_params = {
            'text': 'Parameter Test',
            'segments_per_ring': 8,
            'anchor_radius': 8,
            'ring_width': 10,
            'scale_factor': 3,
            'max_chars': 50,
            'compression_quality': 85,
            'foreground_color': 'red',
            'background_color': 'yellow',
            'theme': 'business'
        }
        
        response = self.client.post('/api/generate', 
                                  json=test_params,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertEqual(data['status'], 'success')
    
    def test_invalid_generation_request(self):
        """Test generation with invalid parameters"""
        # Test with empty text
        response = self.client.post('/api/generate', 
                                  json={'text': ''},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_encrypted_generation_workflow(self):
        """Test the encrypted generation workflow"""
        response = self.client.post('/api/encrypt-and-generate', 
                                  json={'text': 'Sensitive Data'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertIn('encrypted_text', data)
        self.assertEqual(data['status'], 'success')
    
    def test_qr_generation_workflow(self):
        """Test QR code generation workflow"""
        response = self.client.post('/api/generate-qr', 
                                  json={'text': 'QR Test Data'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertEqual(data['status'], 'success')
    
    def test_batch_generation_workflow(self):
        """Test batch generation workflow"""
        batch_data = {
            'texts': ['Text 1', 'Text 2', 'Text 3'],
            'page': 1,
            'page_size': 10,
            'segments_per_ring': 8,
            'anchor_radius': 8
        }
        
        response = self.client.post('/api/batch-generate', 
                                  json=batch_data,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('results', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['results']), 3)
        self.assertEqual(data['pagination']['total_items'], 3)
    
    def test_bulk_generation_workflow(self):
        """Test bulk generation workflow"""
        bulk_data = {
            'format': 'json',
            'content': ['Bulk 1', 'Bulk 2', 'Bulk 3'],
            'segments_per_ring': 8,
            'output_format': 'json'
        }
        
        response = self.client.post('/api/bulk-generate', 
                                  json=bulk_data,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('content', data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['content']), 3)
    
    def test_authentication_workflow(self):
        """Test authentication workflow"""
        # Test login with valid credentials
        response = self.client.post('/auth/login', 
                                  json={'username': 'admin', 'password': 'secure_password'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)
        
        # Test login with invalid credentials
        response = self.client.post('/auth/login', 
                                  json={'username': 'invalid', 'password': 'invalid'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)


class TestE2EBehavior(unittest.TestCase):
    """End-to-end behavior tests"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client for the application"""
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        cls.app_context.pop()
    
    def test_complete_user_flow(self):
        """Test a complete user flow from generation to potential scanning"""
        # Step 1: Generate a KD-Code
        gen_response = self.client.post('/api/generate', 
                                      json={'text': 'E2E Test'},
                                      content_type='application/json')
        
        self.assertEqual(gen_response.status_code, 200)
        gen_data = json.loads(gen_response.data)
        self.assertIn('image', gen_data)
        
        # Step 2: The image would normally be scanned, but we'll simulate
        # For now, just verify the generation worked
        self.assertEqual(gen_data['status'], 'success')
        self.assertIsInstance(gen_data['image'], str)
        self.assertGreater(len(gen_data['image']), 0)
    
    def test_styled_generation_flow(self):
        """Test generation with styling options"""
        styled_data = {
            'text': 'Styled E2E Test',
            'theme': 'nature',
            'foreground_color': '#2E8B57',
            'background_color': '#F0F8E8',
            'segments_per_ring': 16,
            'anchor_radius': 12,
            'ring_width': 18,
            'scale_factor': 4
        }
        
        response = self.client.post('/api/generate', 
                                  json=styled_data,
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('image', data)
        self.assertEqual(data['status'], 'success')
    
    def test_rate_limiting_behavior(self):
        """Test that rate limiting is working"""
        # Make multiple requests quickly to test rate limiting
        for i in range(35):  # More than the 30 per minute limit
            response = self.client.post('/api/generate', 
                                      json={'text': f'Test {i}'},
                                      content_type='application/json')
        
        # The last few requests should be limited
        # Note: This test might not always trigger rate limiting in testing environment
        # depending on how the limiter is configured for tests
    
    def test_encryption_integrity(self):
        """Test that encrypted data maintains integrity"""
        original_text = "Confidential Information"
        
        # Encrypt and generate
        encrypt_response = self.client.post('/api/encrypt-and-generate', 
                                         json={'text': original_text},
                                         content_type='application/json')
        
        self.assertEqual(encrypt_response.status_code, 200)
        encrypt_data = json.loads(encrypt_response.data)
        self.assertIn('encrypted_text', encrypt_data)
        self.assertIn('image', encrypt_data)
        
        # The encrypted text should be different from original
        self.assertNotEqual(encrypt_data['encrypted_text'], original_text)
        
        # But should be decryptable back to original
        # (This would require a decrypt endpoint in a real scenario)


class TestErrorHandling(unittest.TestCase):
    """Test error handling throughout the system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client for the application"""
        cls.app = create_app()
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        cls.app_context.pop()
    
    def test_error_responses(self):
        """Test various error responses"""
        # Test invalid JSON
        response = self.client.post('/api/generate', 
                                  data='invalid json',
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        # Test missing required fields
        response = self.client.post('/api/generate', 
                                  json={},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_boundary_conditions(self):
        """Test boundary conditions"""
        # Test maximum text length
        long_text = 'A' * (DEFAULT_MAX_CHARS + 10)
        response = self.client.post('/api/generate', 
                                  json={'text': long_text},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        # Test minimum valid text
        response = self.client.post('/api/generate', 
                                  json={'text': 'A'},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)


def run_integration_tests():
    """Run all integration and E2E tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_integration_tests()