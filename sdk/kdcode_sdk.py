"""
KD-Code SDK for Third-Party Integrations

This SDK provides a simple interface for integrating KD-Code functionality
into third-party applications.
"""

import requests
import base64
import json


class KDCodeSDK:
    """
    SDK for integrating KD-Code functionality into third-party applications.
    """
    
    def __init__(self, base_url="http://localhost:5000", api_key=None):
        """
        Initialize the SDK with the base URL of the KD-Code service.
        
        Args:
            base_url (str): Base URL of the KD-Code service
            api_key (str, optional): API key for authenticated requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def generate_kd_code(self, text, **options):
        """
        Generate a KD-Code from text.
        
        Args:
            text (str): Text to encode in the KD-Code
            **options: Additional options for KD-Code generation
                - segments_per_ring (int): Number of segments per ring
                - anchor_radius (int): Radius of the anchor circle
                - ring_width (int): Width of each ring
                - scale_factor (int): Scale factor for the image
                - max_chars (int): Maximum number of characters
                - compression_quality (int): Compression quality (1-100)
                - foreground_color (str): Color for the foreground
                - background_color (str): Color for the background
                - theme (str): Predefined theme
        
        Returns:
            dict: Response from the API with the generated KD-Code
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {"text": text}
        payload.update(options)
        
        response = self.session.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to generate KD-Code: {response.status_code} - {response.text}")
    
    def scan_kd_code(self, image_data, **options):
        """
        Scan a KD-Code from an image.
        
        Args:
            image_data (str or bytes): Image data as base64 string or bytes
            **options: Additional options for scanning
                - segments_per_ring (int): Expected number of segments per ring
                - min_anchor_radius (int): Minimum expected anchor radius
                - max_anchor_radius (int): Maximum expected anchor radius
        
        Returns:
            dict: Response from the API with the decoded text
        """
        url = f"{self.base_url}/api/scan"
        
        if isinstance(image_data, bytes):
            image_data = base64.b64encode(image_data).decode('utf-8')
        
        payload = {"image": f"data:image/png;base64,{image_data}"}
        payload.update(options)
        
        response = self.session.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to scan KD-Code: {response.status_code} - {response.text}")
    
    def batch_generate(self, texts, **options):
        """
        Generate multiple KD-Codes in a single request.
        
        Args:
            texts (list): List of texts to encode
            **options: Additional options for batch generation
        
        Returns:
            dict: Response from the API with the generated KD-Codes
        """
        url = f"{self.base_url}/api/batch-generate"
        
        payload = {"texts": texts}
        payload.update(options)
        
        response = self.session.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to batch generate KD-Codes: {response.status_code} - {response.text}")
    
    def encrypt_and_generate(self, text, **options):
        """
        Encrypt text and generate a KD-Code.
        
        Args:
            text (str): Text to encrypt and encode
            **options: Additional options for encrypted generation
        
        Returns:
            dict: Response from the API with the encrypted KD-Code
        """
        url = f"{self.base_url}/api/encrypt-and-generate"
        
        payload = {"text": text}
        payload.update(options)
        
        response = self.session.post(url, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to encrypt and generate KD-Code: {response.status_code} - {response.text}")
    
    def get_health(self):
        """
        Check the health status of the KD-Code service.
        
        Returns:
            dict: Health status of the service
        """
        url = f"{self.base_url}/health"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get health status: {response.status_code} - {response.text}")
    
    def get_analytics(self, start_date=None, end_date=None):
        """
        Get usage analytics for the KD-Code service.
        
        Args:
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
        
        Returns:
            dict: Analytics data
        """
        url = f"{self.base_url}/analytics/report"
        
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        response = self.session.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get analytics: {response.status_code} - {response.text}")


# Example usage
if __name__ == "__main__":
    # Initialize the SDK
    sdk = KDCodeSDK(base_url="http://localhost:5000")
    
    # Generate a KD-Code
    try:
        result = sdk.generate_kd_code("Hello, World!", segments_per_ring=16)
        print("Generated KD-Code:", result['status'])
        
        # Get health status
        health = sdk.get_health()
        print("Service health:", health['status'])
        
    except Exception as e:
        print(f"Error: {e}")