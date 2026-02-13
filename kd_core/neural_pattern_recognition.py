"""
Neural Network Pattern Recognition Module for KD-Code System
Implements deep learning algorithms for improved KD-Code detection and recognition
"""

import tensorflow as tf
import numpy as np
import cv2
from PIL import Image
import os
import logging
from typing import Tuple, List, Dict, Any, Optional
import json
from datetime import datetime


class KDCodeNeuralPatternRecognizer:
    """
    Neural network-based pattern recognition system for KD-Code detection and decoding
    """
    
    def __init__(self, model_path: str = "models/kd_code_nn_model.h5"):
        """
        Initialize the neural pattern recognizer
        
        Args:
            model_path: Path to the trained neural network model
        """
        self.model_path = model_path
        self.model = None
        self.is_trained = False
        self.input_shape = (224, 224, 3)  # Standard input size for the model
        self.logger = logging.getLogger(__name__)
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        # Initialize the model
        self.build_model()
    
    def build_model(self):
        """Build the neural network model for KD-Code recognition"""
        # Create a CNN model for KD-Code detection and classification
        model = tf.keras.Sequential([
            # Input layer
            tf.keras.layers.Input(shape=self.input_shape),
            
            # Feature extraction layers
            tf.keras.layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D((2, 2)),
            
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D((2, 2)),
            
            tf.keras.layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D((2, 2)),
            
            tf.keras.layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D((2, 2)),
            
            # Classification layers
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dropout(0.3),
            
            # Output layers - one for detection confidence, one for classification
            tf.keras.layers.Dense(1, activation='sigmoid', name='detection_output'),  # Whether KD-Code is present
            tf.keras.layers.Dense(256, activation='linear', name='feature_output')   # Feature vector for classification
        ])
        
        # Compile the model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss={
                'detection_output': 'binary_crossentropy',
                'feature_output': 'mse'
            },
            metrics=['accuracy']
        )
        
        self.model = model
        self.logger.info("Neural network model built successfully")
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for neural network input
        
        Args:
            image: Input image as numpy array
        
        Returns:
            Preprocessed image ready for neural network
        """
        # Resize image to model input size
        resized = cv2.resize(image, (self.input_shape[0], self.input_shape[1]))
        
        # Convert to RGB if needed
        if len(resized.shape) == 2:  # Grayscale
            resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
        elif resized.shape[2] == 4:  # RGBA
            resized = cv2.cvtColor(resized, cv2.COLOR_RGBA2RGB)
        
        # Normalize pixel values to [0, 1]
        normalized = resized.astype(np.float32) / 255.0
        
        # Add batch dimension
        processed = np.expand_dims(normalized, axis=0)
        
        return processed
    
    def detect_kd_code_with_nn(self, image: np.ndarray) -> Tuple[bool, float, List[Tuple[int, int]]]:
        """
        Detect KD-Code in an image using neural network
        
        Args:
            image: Input image as numpy array
        
        Returns:
            Tuple of (is_detected, confidence, bounding_box_coordinates)
        """
        if self.model is None:
            self.logger.warning("Model not initialized, using fallback detection")
            return self._fallback_detection(image)
        
        # Preprocess the image
        processed_image = self.preprocess_image(image)
        
        try:
            # Predict using the model
            predictions = self.model.predict(processed_image, verbose=0)
            
            # Extract detection confidence
            detection_confidence = float(predictions[0][0] if isinstance(predictions, list) else predictions[0])
            
            # For now, return a simple bounding box based on confidence
            # In a real implementation, the model would output coordinates
            if detection_confidence > 0.7:  # Threshold for detection
                height, width = image.shape[:2]
                # Return a bounding box in the center of the image as an example
                bbox = [
                    (width//4, height//4),      # Top-left
                    (3*width//4, height//4),    # Top-right
                    (3*width//4, 3*height//4),  # Bottom-right
                    (width//4, 3*height//4)     # Bottom-left
                ]
                return True, detection_confidence, bbox
            else:
                return False, detection_confidence, []
        except Exception as e:
            self.logger.error(f"Error in neural network detection: {e}")
            # Fallback to traditional detection
            return self._fallback_detection(image)
    
    def _fallback_detection(self, image: np.ndarray) -> Tuple[bool, float, List[Tuple[int, int]]]:
        """
        Fallback detection using traditional computer vision techniques
        
        Args:
            image: Input image as numpy array
        
        Returns:
            Tuple of (is_detected, confidence, bounding_box_coordinates)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Try to detect circles using HoughCircles
        circles = cv2.HoughCircles(
            thresh,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=20,
            maxRadius=200
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            # Return the largest circle as the most likely KD-Code
            if len(circles) > 0:
                # Find the largest circle
                largest_circle = max(circles, key=lambda c: c[2])
                x, y, r = largest_circle
                
                # Calculate bounding box
                bbox = [
                    (x - r, y - r),  # Top-left
                    (x + r, y - r),  # Top-right
                    (x + r, y + r),  # Bottom-right
                    (x - r, y + r)   # Bottom-left
                ]
                
                # Return with moderate confidence
                return True, 0.8, bbox
        
        return False, 0.0, []
    
    def recognize_pattern_with_nn(self, image: np.ndarray, bbox: List[Tuple[int, int]]) -> Optional[str]:
        """
        Recognize the pattern in a KD-Code using neural network
        
        Args:
            image: Input image as numpy array
            bbox: Bounding box coordinates of the KD-Code
        
        Returns:
            Recognized text or None if not recognized
        """
        if self.model is None:
            self.logger.warning("Model not initialized, skipping neural recognition")
            return None
        
        # Crop the image to the bounding box
        x_coords = [pt[0] for pt in bbox]
        y_coords = [pt[1] for pt in bbox]
        
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # Ensure coordinates are within image bounds
        h, w = image.shape[:2]
        x_min = max(0, x_min)
        x_max = min(w, x_max)
        y_min = max(0, y_min)
        y_max = min(h, y_max)
        
        cropped = image[y_min:y_max, x_min:x_max]
        
        if cropped.size == 0:
            return None
        
        # Preprocess the cropped image
        processed = self.preprocess_image(cropped)
        
        try:
            # Extract features using the neural network
            predictions = self.model.predict(processed, verbose=0)
            
            # In a real implementation, we would have a separate model for decoding
            # For now, we'll return None to indicate that traditional decoding should be used
            # along with the neural network's confidence in the detection
            return None
        except Exception as e:
            self.logger.error(f"Error in neural network pattern recognition: {e}")
            return None
    
    def train_model(self, training_data: List[Tuple[np.ndarray, int]], 
                   validation_data: List[Tuple[np.ndarray, int]] = None,
                   epochs: int = 50, batch_size: int = 32):
        """
        Train the neural network model
        
        Args:
            training_data: List of (image, label) tuples for training
            validation_data: List of (image, label) tuples for validation
            epochs: Number of training epochs
            batch_size: Batch size for training
        """
        self.logger.info(f"Starting model training with {len(training_data)} samples")
        
        # Prepare training data
        X_train = []
        y_train_detection = []
        y_train_features = []
        
        for image, label in training_data:
            processed = self.preprocess_image(image)
            X_train.append(processed[0])  # Remove batch dimension
            y_train_detection.append(label)  # 1 for KD-Code present, 0 for not present
            # For feature output, we'll use a simple encoding based on the label
            y_train_features.append([label] * 256)  # Repeat label for feature vector
        
        X_train = np.array(X_train)
        y_train_detection = np.array(y_train_detection)
        y_train_features = np.array(y_train_features)
        
        # Prepare validation data if provided
        X_val, y_val_detection, y_val_features = None, None, None
        if validation_data:
            X_val = []
            y_val_detection = []
            y_val_features = []
            
            for image, label in validation_data:
                processed = self.preprocess_image(image)
                X_val.append(processed[0])
                y_val_detection.append(label)
                y_val_features.append([label] * 256)
            
            X_val = np.array(X_val)
            y_val_detection = np.array(y_val_detection)
            y_val_features = np.array(y_val_features)
        
        # Train the model
        if validation_data:
            history = self.model.fit(
                X_train,
                {'detection_output': y_train_detection, 'feature_output': y_train_features},
                validation_data=(
                    X_val, 
                    {'detection_output': y_val_detection, 'feature_output': y_val_features}
                ),
                epochs=epochs,
                batch_size=batch_size,
                verbose=1
            )
        else:
            history = self.model.fit(
                X_train,
                {'detection_output': y_train_detection, 'feature_output': y_train_features},
                epochs=epochs,
                batch_size=batch_size,
                verbose=1
            )
        
        self.is_trained = True
        self.save_model()
        
        self.logger.info("Model training completed successfully")
        return history
    
    def save_model(self):
        """Save the trained model to disk"""
        try:
            self.model.save(self.model_path)
            self.logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
    
    def load_model(self) -> bool:
        """
        Load a pre-trained model from disk
        
        Returns:
            True if model was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                self.is_trained = True
                self.logger.info(f"Model loaded from {self.model_path}")
                return True
            else:
                self.logger.warning(f"Model file not found at {self.model_path}")
                return False
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    def enhance_detection_with_nn(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Enhance traditional detection with neural network insights
        
        Args:
            image: Input image as numpy array
        
        Returns:
            Dictionary with enhanced detection results
        """
        # First, use traditional detection to find potential KD-Codes
        traditional_result = self._traditional_detection(image)
        
        # Then, use neural network to validate and enhance
        nn_detected, nn_confidence, nn_bbox = self.detect_kd_code_with_nn(image)
        
        # Combine results
        result = {
            'traditional_detection': traditional_result,
            'neural_network_detection': {
                'detected': nn_detected,
                'confidence': nn_confidence,
                'bbox': nn_bbox
            },
            'combined_confidence': 0.0,
            'final_detection': False,
            'final_bbox': []
        }
        
        # If both methods agree, increase confidence
        if traditional_result['detected'] and nn_detected:
            result['combined_confidence'] = (traditional_result['confidence'] + nn_confidence) / 2 * 1.2  # Boost for agreement
            result['final_detection'] = True
            result['final_bbox'] = nn_bbox  # Prefer neural network's bounding box
        elif traditional_result['detected']:
            result['combined_confidence'] = traditional_result['confidence'] * 0.8  # Reduce for disagreement
            result['final_detection'] = True
            result['final_bbox'] = traditional_result['bbox']
        elif nn_detected:
            result['combined_confidence'] = nn_confidence * 0.8  # Reduce for disagreement
            result['final_detection'] = True
            result['final_bbox'] = nn_bbox
        else:
            result['combined_confidence'] = min(traditional_result.get('confidence', 0), nn_confidence)
            result['final_detection'] = False
            result['final_bbox'] = []
        
        # Ensure confidence doesn't exceed 1.0
        result['combined_confidence'] = min(1.0, result['combined_confidence'])
        
        return result
    
    def _traditional_detection(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Traditional computer vision-based detection
        
        Args:
            image: Input image as numpy array
        
        Returns:
            Detection results from traditional method
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Try to detect circles using HoughCircles
        circles = cv2.HoughCircles(
            thresh,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=20,
            maxRadius=200
        )
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            # Return the largest circle as the most likely KD-Code
            if len(circles) > 0:
                # Find the largest circle
                largest_circle = max(circles, key=lambda c: c[2])
                x, y, r = largest_circle
                
                # Calculate bounding box
                bbox = [
                    (x - r, y - r),  # Top-left
                    (x + r, y - r),  # Top-right
                    (x + r, y + r),  # Bottom-right
                    (x - r, y + r)   # Bottom-left
                ]
                
                # Return with moderate confidence
                return {
                    'detected': True,
                    'confidence': 0.7,
                    'bbox': bbox
                }
        
        return {
            'detected': False,
            'confidence': 0.0,
            'bbox': []
        }


# Global neural pattern recognizer instance
nn_pattern_recognizer = KDCodeNeuralPatternRecognizer()


def initialize_neural_recognition():
    """Initialize the neural network pattern recognition system"""
    global nn_pattern_recognizer
    nn_pattern_recognizer = KDCodeNeuralPatternRecognizer()
    
    # Try to load existing model, otherwise train a new one
    if not nn_pattern_recognizer.load_model():
        # In a real implementation, we would train with actual data
        # For now, we'll just log that we're using the untrained model
        print("No pre-trained model found. Using base model.")


def detect_kd_code_with_neural_network(image: np.ndarray) -> Dict[str, Any]:
    """
    Detect KD-Code in an image using neural network enhancement
    
    Args:
        image: Input image as numpy array
    
    Returns:
        Detection results with neural network enhancement
    """
    return nn_pattern_recognizer.enhance_detection_with_nn(image)


def recognize_kd_code_pattern(image: np.ndarray, bbox: List[Tuple[int, int]]) -> Optional[str]:
    """
    Recognize the pattern in a KD-Code using neural network
    
    Args:
        image: Input image as numpy array
        bbox: Bounding box coordinates of the KD-Code
    
    Returns:
        Recognized text or None if not recognized
    """
    return nn_pattern_recognizer.recognize_pattern_with_nn(image, bbox)


def get_neural_network_confidence(image: np.ndarray) -> float:
    """
    Get the neural network's confidence in detecting a KD-Code
    
    Args:
        image: Input image as numpy array
    
    Returns:
        Confidence score between 0 and 1
    """
    _, confidence, _ = nn_pattern_recognizer.detect_kd_code_with_nn(image)
    return confidence


# Example usage and testing
if __name__ == "__main__":
    # Initialize the neural pattern recognition system
    initialize_neural_recognition()
    
    # Example of using the neural detection
    print("Neural Network Pattern Recognition System Initialized")
    
    # The system would typically receive images from the camera feed
    # For this example, we'll just show the available functions
    print("Available functions:")
    print("- detect_kd_code_with_neural_network(image)")
    print("- recognize_kd_code_pattern(image, bbox)")
    print("- get_neural_network_confidence(image)")
    
    # Example of how to use in a scanning workflow:
    # 1. Capture image from camera
    # 2. Use detect_kd_code_with_neural_network to find KD-Codes
    # 3. If detected, use recognize_kd_code_pattern to decode
    # 4. Combine with traditional decoding for verification