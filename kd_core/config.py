"""
Configuration for KD-Code System
Defines default parameters and settings for the KD-Code generator and scanner.
"""

# KD-Code Generation Parameters
DEFAULT_SEGMENTS_PER_RING = 16
DEFAULT_ANCHOR_RADIUS = 10
DEFAULT_RING_WIDTH = 15
DEFAULT_SCALE_FACTOR = 5
DEFAULT_MAX_CHARS = 128

# KD-Code Scanning Parameters
DEFAULT_SCAN_SEGMENTS_PER_RING = 16
DEFAULT_MIN_ANCHOR_RADIUS = 5
DEFAULT_MAX_ANCHOR_RADIUS = 100

# Image Processing Parameters
MAX_IMAGE_SIZE = 2000  # Maximum allowed image dimension in pixels
MAX_RINGS = 20  # Maximum number of rings allowed

# Camera and Scanning Parameters
SCAN_FPS = 5  # Frames per second for scanning
DETECTION_DEBOUNCE_MS = 1000  # Milliseconds to wait between detections

# Validation Parameters
ALLOWED_SEGMENTS_VALUES = [8, 16, 32]  # Valid segments per ring values
MAX_ALLOWED_CHARS = 1024  # Maximum characters allowed in input