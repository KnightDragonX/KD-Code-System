"""
Bulk Import/Export Module for KD-Code System
Handles importing and exporting of KD-Codes in various formats
"""

import json
import csv
import base64
from io import StringIO
from kd_core.encoder import generate_kd_code
from kd_core.decoder import decode_kd_code
from kd_core.config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS
)


class BulkProcessor:
    """Handles bulk import and export operations for KD-Codes"""
    
    def __init__(self):
        pass
    
    def import_from_csv(self, csv_content, text_column='text'):
        """
        Import texts from CSV content for KD-Code generation
        
        Args:
            csv_content (str): CSV formatted string
            text_column (str): Name of the column containing text to encode
        
        Returns:
            list: List of texts extracted from CSV
        """
        # Parse CSV content
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        texts = []
        for row in reader:
            if text_column in row:
                text = row[text_column].strip()
                if text:  # Only add non-empty texts
                    texts.append(text)
        
        return texts
    
    def import_from_json(self, json_content, text_key='text'):
        """
        Import texts from JSON content for KD-Code generation
        
        Args:
            json_content (str or list): JSON string or list of objects
            text_key (str): Key containing the text to encode
        
        Returns:
            list: List of texts extracted from JSON
        """
        if isinstance(json_content, str):
            data = json.loads(json_content)
        else:
            data = json_content
        
        texts = []
        if isinstance(data, list):
            # If it's a list of objects
            for item in data:
                if isinstance(item, dict) and text_key in item:
                    text = item[text_key]
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
                elif isinstance(item, str):
                    # If it's a list of strings
                    if item.strip():
                        texts.append(item.strip())
        elif isinstance(data, dict):
            # If it's a single object
            if text_key in data:
                text = data[text_key]
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
        
        return texts
    
    def export_to_csv(self, results, filename_prefix='kd_codes'):
        """
        Export KD-Code results to CSV format
        
        Args:
            results (list): List of KD-Code generation results
            filename_prefix (str): Prefix for the exported filename
        
        Returns:
            tuple: (CSV content as string, suggested filename)
        """
        output = StringIO()
        fieldnames = ['text', 'image', 'status', 'error']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow({
                'text': result.get('text', ''),
                'image': result.get('image', ''),
                'status': result.get('status', ''),
                'error': result.get('error', '')
            })
        
        csv_content = output.getvalue()
        filename = f"{filename_prefix}_{len(results)}_codes.csv"
        
        return csv_content, filename
    
    def export_to_json(self, results, filename_prefix='kd_codes'):
        """
        Export KD-Code results to JSON format
        
        Args:
            results (list): List of KD-Code generation results
            filename_prefix (str): Prefix for the exported filename
        
        Returns:
            tuple: (JSON content as string, suggested filename)
        """
        json_content = json.dumps(results, indent=2)
        filename = f"{filename_prefix}_{len(results)}_codes.json"
        
        return json_content, filename
    
    def process_bulk_generation(self, texts, **kwargs):
        """
        Process bulk generation of KD-Codes
        
        Args:
            texts (list): List of texts to encode
            **kwargs: Additional parameters for KD-Code generation
        
        Returns:
            list: List of generation results
        """
        results = []
        for text in texts:
            try:
                # Generate KD-Code for each text
                image_base64 = generate_kd_code(text, **kwargs)
                results.append({
                    'text': text,
                    'image': image_base64,
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'text': text,
                    'error': str(e),
                    'status': 'error'
                })
        
        return results
    
    def process_bulk_decoding(self, images):
        """
        Process bulk decoding of KD-Codes
        
        Args:
            images (list): List of image data (base64 strings or bytes)
        
        Returns:
            list: List of decoding results
        """
        results = []
        for idx, image_data in enumerate(images):
            try:
                # Decode KD-Code from image
                if isinstance(image_data, str):
                    # If it's a base64 string, decode it first
                    if image_data.startswith('data:image'):
                        header, encoded = image_data.split(',', 1)
                        image_bytes = base64.b64decode(encoded)
                    else:
                        image_bytes = base64.b64decode(image_data)
                else:
                    image_bytes = image_data
                
                decoded_text = decode_kd_code(image_bytes)
                
                if decoded_text is None:
                    results.append({
                        'index': idx,
                        'error': 'No KD-Code detected in image',
                        'status': 'error'
                    })
                else:
                    results.append({
                        'index': idx,
                        'decoded_text': decoded_text,
                        'status': 'success'
                    })
            except Exception as e:
                results.append({
                    'index': idx,
                    'error': str(e),
                    'status': 'error'
                })
        
        return results


# Global bulk processor instance
bulk_processor = BulkProcessor()