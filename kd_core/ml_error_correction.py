"""
Machine Learning-based Error Correction for KD-Code Scanning
Implements ML algorithms to improve scanning accuracy and correct errors
"""

import numpy as np
import cv2
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import pickle
import os
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class KDCErrorCorrection:
    """
    Machine Learning-based error correction system for KD-Code scanning
    """
    
    def __init__(self):
        """Initialize the error correction system"""
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self.model_path = "models/kd_error_correction_model.pkl"
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
    
    def generate_training_data(self, num_samples: int = 10000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data for error correction
        
        Args:
            num_samples: Number of training samples to generate
        
        Returns:
            Tuple of (features, labels) for training
        """
        logger.info(f"Generating {num_samples} training samples for error correction")
        
        # Features: [intensity, position_features, context_features, ...]
        features = np.zeros((num_samples, 10))
        labels = np.zeros(num_samples, dtype=int)
        
        for i in range(num_samples):
            # Simulate various error conditions
            base_intensity = np.random.uniform(0, 255)
            noise_level = np.random.uniform(0, 50)
            position_var = np.random.uniform(-10, 10)
            context_influence = np.random.uniform(-20, 20)
            
            # Add realistic noise patterns
            noisy_intensity = base_intensity + np.random.normal(0, noise_level)
            noisy_intensity = np.clip(noisy_intensity, 0, 255)
            
            # Other features
            features[i, 0] = base_intensity  # Original intensity
            features[i, 1] = noisy_intensity  # Noisy intensity
            features[i, 2] = noise_level  # Noise level
            features[i, 3] = position_var  # Position variation
            features[i, 4] = context_influence  # Context influence
            features[i, 5] = abs(base_intensity - noisy_intensity)  # Error magnitude
            features[i, 6] = np.random.uniform(0, 1)  # Random feature
            features[i, 7] = np.random.uniform(0, 1)  # Random feature
            features[i, 8] = np.random.uniform(0, 1)  # Random feature
            features[i, 9] = np.random.uniform(0, 1)  # Random feature
            
            # Labels: 0 for black (0), 1 for white (1)
            # Correct label based on original intensity
            labels[i] = 0 if base_intensity < 128 else 1
        
        logger.info("Training data generation completed")
        return features, labels
    
    def train_model(self, features: Optional[np.ndarray] = None, labels: Optional[np.ndarray] = None):
        """
        Train the error correction model
        
        Args:
            features: Training features (if None, generate synthetic data)
            labels: Training labels (if None, generate synthetic data)
        """
        logger.info("Starting model training for error correction")
        
        if features is None or labels is None:
            features, labels = self.generate_training_data()
        
        # Split data for training and validation
        X_train, X_val, y_train, y_val = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )
        
        # Train the model
        self.model.fit(X_train, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        
        logger.info(f"Model trained with validation accuracy: {accuracy:.4f}")
        
        # Save the model
        self.save_model()
        self.is_trained = True
    
    def load_model(self) -> bool:
        """
        Load a pre-trained model from disk
        
        Returns:
            True if model was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.is_trained = True
                logger.info("Pre-trained model loaded successfully")
                return True
            else:
                logger.warning(f"Model file not found at {self.model_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def save_model(self):
        """Save the trained model to disk"""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def correct_pixel_value(self, pixel_intensity: float, context_info: dict) -> int:
        """
        Use ML model to correct a pixel value based on context
        
        Args:
            pixel_intensity: Raw pixel intensity value
            context_info: Dictionary with contextual information
        
        Returns:
            Corrected binary value (0 or 1)
        """
        if not self.is_trained:
            # If not trained, use simple threshold
            return 0 if pixel_intensity < 128 else 1
        
        # Prepare features for prediction
        features = np.zeros((1, 10))
        features[0, 0] = context_info.get('original_intensity', pixel_intensity)  # Original intensity
        features[0, 1] = pixel_intensity  # Noisy intensity
        features[0, 2] = context_info.get('noise_level', 10.0)  # Noise level
        features[0, 3] = context_info.get('position_variance', 0.0)  # Position variation
        features[0, 4] = context_info.get('context_influence', 0.0)  # Context influence
        features[0, 5] = abs(context_info.get('original_intensity', pixel_intensity) - pixel_intensity)  # Error magnitude
        features[0, 6] = context_info.get('local_avg', 128)  # Local average
        features[0, 7] = context_info.get('gradient', 0.0)  # Gradient
        features[0, 8] = context_info.get('surrounding_avg', 128)  # Surrounding average
        features[0, 9] = context_info.get('confidence', 0.5)  # Confidence measure
        
        # Predict using the model
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0]
        
        # Return the predicted class
        return int(prediction)
    
    def correct_bit_sequence(self, bit_sequence: List[int], confidence_scores: List[float] = None) -> List[int]:
        """
        Apply ML-based error correction to a sequence of bits
        
        Args:
            bit_sequence: Original bit sequence
            confidence_scores: Confidence scores for each bit (optional)
        
        Returns:
            Corrected bit sequence
        """
        if not self.is_trained:
            return bit_sequence
        
        corrected_sequence = []
        
        for i, bit in enumerate(bit_sequence):
            # Use context from neighboring bits for correction
            context = {
                'original_bit': bit,
                'position': i,
                'sequence_length': len(bit_sequence),
                'confidence': confidence_scores[i] if confidence_scores else 0.5,
                'prev_bit': bit_sequence[i-1] if i > 0 else -1,
                'next_bit': bit_sequence[i+1] if i < len(bit_sequence)-1 else -1,
                'local_pattern': self._extract_local_pattern(bit_sequence, i)
            }
            
            corrected_bit = self._apply_contextual_correction(bit, context)
            corrected_sequence.append(corrected_bit)
        
        return corrected_sequence
    
    def _extract_local_pattern(self, sequence: List[int], pos: int, window_size: int = 5) -> List[int]:
        """Extract local pattern around a position"""
        start = max(0, pos - window_size//2)
        end = min(len(sequence), pos + window_size//2 + 1)
        pattern = sequence[start:end]
        
        # Pad if necessary
        while len(pattern) < window_size:
            pattern.append(-1)  # Padding value
        
        return pattern[:window_size]
    
    def _apply_contextual_correction(self, bit: int, context: dict) -> int:
        """Apply contextual correction based on pattern and context"""
        # Simple rule-based corrections combined with ML prediction
        local_pattern = context['local_pattern']
        prev_bit = context['prev_bit']
        next_bit = context['next_bit']
        
        # Pattern-based corrections
        if prev_bit != -1 and next_bit != -1 and prev_bit == next_bit and bit != prev_bit:
            # Single bit error surrounded by same bits
            return prev_bit
        
        # If we have a trained model, use it for final decision
        if self.is_trained:
            # Convert context to features for ML model
            features = self._context_to_features(context)
            prediction = self.model.predict([features])[0]
            return int(prediction)
        
        # Fallback to original bit
        return bit
    
    def _context_to_features(self, context: dict) -> np.ndarray:
        """Convert context dictionary to feature vector for ML model"""
        features = np.zeros(10)
        
        # Map context to features
        features[0] = context.get('original_bit', 0.5)
        features[1] = context.get('position', 0)
        features[2] = len(context.get('local_pattern', []))
        features[3] = context.get('confidence', 0.5)
        features[4] = context.get('prev_bit', 0.5)
        features[5] = context.get('next_bit', 0.5)
        
        # Sum of local pattern (excluding padding)
        local_sum = sum(x for x in context.get('local_pattern', []) if x != -1)
        features[6] = local_sum
        
        # Count of 1s in local pattern
        ones_count = sum(1 for x in context.get('local_pattern', []) if x == 1)
        features[7] = ones_count
        
        # Position normalized by sequence length
        seq_len = context.get('sequence_length', 1)
        features[8] = context.get('position', 0) / seq_len if seq_len > 0 else 0
        
        # Average of non-padding values in local pattern
        non_padding = [x for x in context.get('local_pattern', []) if x != -1]
        features[9] = sum(non_padding) / len(non_padding) if non_padding else 0.5
        
        return features


# Global error correction instance
error_corrector = KDCErrorCorrection()


def initialize_error_correction():
    """Initialize the error correction system"""
    global error_corrector
    
    # Try to load pre-trained model
    if not error_corrector.load_model():
        # If no pre-trained model exists, train a new one
        print("No pre-trained model found. Training new model...")
        error_corrector.train_model()


def correct_scanned_bits(bits: List[int], confidence_scores: List[float] = None) -> List[int]:
    """
    Apply ML-based error correction to scanned bits
    
    Args:
        bits: List of bits from scanning
        confidence_scores: Confidence scores for each bit (optional)
    
    Returns:
        Corrected list of bits
    """
    global error_corrector
    
    if not error_corrector.is_trained:
        initialize_error_correction()
    
    return error_corrector.correct_bit_sequence(bits, confidence_scores)


def correct_pixel_value(pixel_intensity: float, context_info: dict) -> int:
    """
    Apply ML-based error correction to a single pixel value
    
    Args:
        pixel_intensity: Raw pixel intensity value
        context_info: Dictionary with contextual information
    
    Returns:
        Corrected binary value (0 or 1)
    """
    global error_corrector
    
    if not error_corrector.is_trained:
        initialize_error_correction()
    
    return error_corrector.correct_pixel_value(pixel_intensity, context_info)


# Example usage and testing
if __name__ == "__main__":
    # Initialize the error correction system
    initialize_error_correction()
    
    # Example: Correct a bit sequence
    original_bits = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1]
    print(f"Original bits: {original_bits}")
    
    corrected_bits = correct_scanned_bits(original_bits)
    print(f"Corrected bits: {corrected_bits}")
    
    # Example: Correct a pixel value
    pixel_val = 130.0
    context = {
        'original_intensity': 40.0,  # Should be black
        'noise_level': 50.0,
        'position_variance': 2.0,
        'context_influence': -10.0,
        'local_avg': 50.0,
        'gradient': 0.5,
        'surrounding_avg': 45.0,
        'confidence': 0.8
    }
    
    corrected_val = correct_pixel_value(pixel_val, context)
    print(f"Pixel {pixel_val} corrected to: {corrected_val} (expected: 0)")