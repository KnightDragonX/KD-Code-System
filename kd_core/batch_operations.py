"""
Batch Operations Module for KD-Code System
Handles batch generation and processing of multiple KD-Codes
"""

from kd_core.encoder import generate_kd_code
from kd_core.config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS
)
import hashlib


class BatchProcessor:
    """Handles batch operations for KD-Codes"""
    
    def __init__(self):
        self.batch_cache = {}
    
    def generate_batch(self, texts, page=1, page_size=10, **kwargs):
        """
        Generate KD-Codes for a batch of texts with pagination support
        
        Args:
            texts (list): List of texts to encode
            page (int): Page number (1-indexed)
            page_size (int): Number of items per page
            **kwargs: Additional parameters for KD-Code generation
        
        Returns:
            dict: Paginated results with metadata
        """
        # Calculate pagination indices
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Slice the texts according to pagination
        paginated_texts = texts[start_idx:end_idx]
        
        # Process the batch
        results = []
        for text in paginated_texts:
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
        
        # Prepare pagination metadata
        total_items = len(texts)
        total_pages = (total_items + page_size - 1) // page_size  # Ceiling division
        
        return {
            'results': results,
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_items': total_items,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
    
    def generate_batch_sync(self, texts, **kwargs):
        """
        Synchronous batch generation without pagination
        
        Args:
            texts (list): List of texts to encode
            **kwargs: Additional parameters for KD-Code generation
        
        Returns:
            list: List of results for each text
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


# Global batch processor instance
batch_processor = BatchProcessor()