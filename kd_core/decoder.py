"""
KD-Code Decoder Module
Implements the detection and decoding of KD-Codes from images.
"""

import numpy as np
import cv2
import math
from PIL import Image
from io import BytesIO
from .config import (
    DEFAULT_SCAN_SEGMENTS_PER_RING, DEFAULT_MIN_ANCHOR_RADIUS,
    DEFAULT_MAX_ANCHOR_RADIUS, ALLOWED_SEGMENTS_VALUES
)
from .ml_error_correction import correct_scanned_bits, correct_pixel_value


def decode_kd_code(image_data, segments_per_ring=DEFAULT_SCAN_SEGMENTS_PER_RING, min_anchor_radius=DEFAULT_MIN_ANCHOR_RADIUS, max_anchor_radius=DEFAULT_MAX_ANCHOR_RADIUS, enable_multithreading=False):
    """
    Decode a KD-Code from an image.
    
    Args:
        image_data (bytes): Image data as bytes (from file or base64 decoded)
        segments_per_ring (int): Expected number of segments per ring (default 16)
        min_anchor_radius (int): Minimum expected anchor radius for filtering
        max_anchor_radius (int): Maximum expected anchor radius for filtering
        enable_multithreading (bool): Whether to enable multithreading for processing
    
    Returns:
        str or None: Decoded text from the KD-Code, or None if no code is detected
    
    Raises:
        ValueError: If input parameters are invalid
        TypeError: If input types are incorrect
    """
    # Validate inputs
    if not isinstance(image_data, bytes):
        raise TypeError("image_data must be bytes")
    
    if not isinstance(segments_per_ring, int) or segments_per_ring <= 0:
        raise ValueError("segments_per_ring must be a positive integer")
    
    if segments_per_ring not in ALLOWED_SEGMENTS_VALUES:  # Common values
        raise ValueError(f"segments_per_ring should be one of {ALLOWED_SEGMENTS_VALUES} for optimal results")
    
    if not isinstance(min_anchor_radius, int) or min_anchor_radius <= 0:
        raise ValueError("min_anchor_radius must be a positive integer")
    
    if not isinstance(max_anchor_radius, int) or max_anchor_radius <= min_anchor_radius:
        raise ValueError("max_anchor_radius must be greater than min_anchor_radius")
    
    # Convert bytes to OpenCV image
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return None
    
    # Store original image dimensions for scaling calculations
    orig_h, orig_w = img.shape[:2]
    
    # Resize image if too large to improve processing speed
    MAX_DIMENSION = 800
    scale_factor = 1.0
    if max(orig_h, orig_w) > MAX_DIMENSION:
        scale_factor = MAX_DIMENSION / max(orig_h, orig_w)
        new_w = int(orig_w * scale_factor)
        new_h = int(orig_h * scale_factor)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_gray = clahe.apply(gray)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(enhanced_gray, (5, 5), 0)
    
    # Try multiple thresholding techniques to improve detection
    _, thresh_binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh_adaptive = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Combine thresholds to get better results
    combined_thresh = cv2.bitwise_and(thresh_binary, thresh_adaptive)
    
    # Try to detect circles using HoughCircles with multiple parameter sets
    circles = None
    params_list = [
        {'dp': 1, 'minDist': 50, 'param1': 50, 'param2': 30, 'minRadius': min_anchor_radius, 'maxRadius': max_anchor_radius},
        {'dp': 1, 'minDist': 30, 'param1': 40, 'param2': 25, 'minRadius': min_anchor_radius, 'maxRadius': max_anchor_radius},
        {'dp': 2, 'minDist': 40, 'param1': 60, 'param2': 35, 'minRadius': min_anchor_radius, 'maxRadius': max_anchor_radius}
    ]
    
    # If multithreading is enabled, we could process different parameter sets in parallel
    # For now, we'll optimize by breaking early when sufficient circles are found
    for params in params_list:
        detected_circles = cv2.HoughCircles(
            combined_thresh,
            cv2.HOUGH_GRADIENT,
            **params
        )
        if detected_circles is not None:
            circles = detected_circles
            # Early termination: if we have enough circles for processing, break
            if len(detected_circles[0]) >= 2:  # Need at least outer ring and anchor
                break
            # Otherwise, continue with next parameter set for better detection
    
    if circles is None or len(circles) == 0:
        return None
    
    # Round and convert to integers
    circles = np.round(circles[0, :]).astype("int")
    
    # Filter circles based on expected characteristics
    filtered_circles = []
    for (x, y, r) in circles:
        # Check if circle is reasonably centered in the image (for outer distortion ring)
        center_threshold = min(img.shape[0], img.shape[1]) * 0.4
        if abs(x - img.shape[1]/2) < center_threshold and abs(y - img.shape[0]/2) < center_threshold:
            filtered_circles.append((x, y, r))
    
    if not filtered_circles:
        return None
    
    # Sort by radius to find the outer distortion ring (largest) and anchor (smallest reasonable)
    sorted_circles = sorted(filtered_circles, key=lambda c: c[2])
    
    # Find the outer distortion ring (largest circle that fits expected pattern)
    outer_circle = sorted_circles[-1]  # Usually the largest
    outer_x, outer_y, outer_r = outer_circle
    
    # Find the anchor (smallest circle that could be the center)
    # Look for circles that are significantly smaller and centered within the outer circle
    anchors = []
    for (x, y, r) in sorted_circles:
        # Check if this circle is near the center of the outer circle and has appropriate size
        dist_from_center = math.sqrt((x - outer_x)**2 + (y - outer_y)**2)
        if dist_from_center < outer_r * 0.3 and r < outer_r * 0.3:  # Reasonable anchor size
            anchors.append((x, y, r))
    
    if not anchors:
        return None
    
    # Get the most centrally located small circle as the anchor
    anchor_x, anchor_y, anchor_r = min(anchors, key=lambda c: math.sqrt((c[0]-outer_x)**2 + (c[1]-outer_y)**2))
    
    # Determine the orientation fin by looking for a triangular shape at the top of the anchor
    # We'll analyze the area above the anchor for the fin
    fin_area = gray[
        max(0, anchor_y - anchor_r - anchor_r//2):anchor_y - anchor_r//2,
        anchor_x - anchor_r:anchor_x + anchor_r
    ]
    
    # Check for orientation by looking at multiple directions
    # The fin should create a distinctive pattern
    orientation_angle = 0  # Default to top
    
    if fin_area.size > 0:
        # Look for directional patterns by sampling different quadrants around the anchor
        # Divide the area around the anchor into sectors and compare intensities
        comparison_radius = anchor_r * 2
        sector_samples = []
        
        # Sample 4 directions: top, right, bottom, left
        for direction in [0, math.pi/2, math.pi, 3*math.pi/2]:  # top, right, bottom, left
            sample_x = int(anchor_x + comparison_radius * math.cos(direction))
            sample_y = int(anchor_y + comparison_radius * math.sin(direction))
            
            if 0 <= sample_x < gray.shape[1] and 0 <= sample_y < gray.shape[0]:
                intensity = gray[sample_y, sample_x]
                sector_samples.append((direction, intensity))
        
        # Find the darkest direction (likely where the fin is)
        if sector_samples:
            darkest_direction, _ = min(sector_samples, key=lambda x: x[1])
            # The fin points away from the darkest direction, so we adjust
            orientation_angle = (darkest_direction + math.pi) % (2 * math.pi)
    
    # Calculate number of rings based on outer radius and estimated ring width
    estimated_ring_width = max(1, (outer_r - anchor_r) // 10)  # Rough estimation
    num_rings = max(1, (outer_r - anchor_r) // estimated_ring_width)
    
    if num_rings <= 0:
        return None
    
    # Extract bits from each ring with improved sampling
    raw_bitstream = []
    confidence_scores = []
    
    for ring_idx in range(num_rings):
        # Calculate the radius for sampling this ring
        ring_radius = anchor_r + (ring_idx + 0.5) * estimated_ring_width

        # Sample points around the ring with anti-aliasing
        for seg_idx in range(segments_per_ring):
            # Calculate angle for this segment with orientation offset
            angle = orientation_angle + (seg_idx * 2 * math.pi / segments_per_ring)

            # Calculate coordinates for sampling point
            sample_x = int(anchor_x + ring_radius * math.cos(angle))
            sample_y = int(anchor_y + ring_radius * math.sin(angle))

            # Ensure coordinates are within image bounds
            if 0 <= sample_x < gray.shape[1] and 0 <= sample_y < gray.shape[0]:
                # Use bilinear interpolation for more accurate sampling
                intensity = get_interpolated_pixel(gray, sample_x, sample_y)

                # Calculate local context for error correction
                local_avg = get_local_average(gray, sample_x, sample_y, max(2, anchor_r//4))
                
                # Calculate gradient for context
                grad_x = 0
                grad_y = 0
                if (sample_x > 0 and sample_x < gray.shape[1]-1 and 
                    sample_y > 0 and sample_y < gray.shape[0]-1):
                    grad_x = int(gray[sample_y, sample_x+1] - gray[sample_y, sample_x-1])
                    grad_y = int(gray[sample_y+1, sample_x] - gray[sample_y-1, sample_x])
                
                # Calculate confidence based on contrast
                contrast = abs(intensity - local_avg)
                confidence = min(1.0, contrast / 128.0)  # Normalize confidence
                
                # Create context information for ML model
                context_info = {
                    'original_intensity': intensity,
                    'local_avg': local_avg,
                    'gradient': math.sqrt(grad_x**2 + grad_y**2),
                    'surrounding_avg': local_avg,
                    'confidence': confidence,
                    'noise_level': 255 - contrast,  # Lower contrast = more noise
                    'position_variance': abs(ring_idx - num_rings//2)  # Distance from center
                }
                
                # Use ML model to predict the bit value with context
                bit_value = correct_pixel_value(intensity, context_info)
                
                raw_bitstream.append(bit_value)
                confidence_scores.append(confidence)
            else:
                # If out of bounds, append 0 as default
                raw_bitstream.append(0)
                confidence_scores.append(0.0)

    # Apply ML-based error correction to the entire bitstream
    corrected_bitstream = correct_scanned_bits(raw_bitstream, confidence_scores)

    # Convert bitstream back to text
    decoded_text = bits_to_text(corrected_bitstream)

    return decoded_text


def get_interpolated_pixel(image, x, y):
    """
    Get pixel value using bilinear interpolation for sub-pixel accuracy.
    """
    x1, y1 = int(x), int(y)
    x2, y2 = min(x1 + 1, image.shape[1] - 1), min(y1 + 1, image.shape[0] - 1)
    
    dx, dy = x - x1, y - y1
    
    # Bilinear interpolation
    val = (image[y1, x1] * (1 - dx) * (1 - dy) +
           image[y1, x2] * dx * (1 - dy) +
           image[y2, x1] * (1 - dx) * dy +
           image[y2, x2] * dx * dy)
    
    return int(val)


def get_local_average(image, x, y, radius):
    """
    Calculate the average intensity in a local neighborhood around a point.
    """
    h, w = image.shape
    y_min = max(0, y - radius)
    y_max = min(h, y + radius + 1)
    x_min = max(0, x - radius)
    x_max = min(w, x + radius + 1)
    
    local_region = image[y_min:y_max, x_min:x_max]
    return float(np.mean(local_region))


def bits_to_text(bits):
    """
    Convert a bitstream back to text.
    
    Args:
        bits (list): List of bits (0s and 1s)
    
    Returns:
        str: Decoded text
    """
    if not bits:
        return ""
    
    # Group bits into 8-bit chunks (bytes)
    bytes_list = []
    i = 0
    while i < len(bits):
        byte_chunk = bits[i:i+8]
        
        # Ensure we have a full byte (pad with zeros if needed)
        while len(byte_chunk) < 8:
            byte_chunk.append(0)
        
        # Convert 8-bit chunk to integer
        byte_val = 0
        for bit in byte_chunk:
            byte_val = (byte_val << 1) | bit
        
        # Convert to character (if it's a valid ASCII character)
        if 32 <= byte_val <= 126:  # Printable ASCII range
            bytes_list.append(chr(byte_val))
        elif byte_val == 0:  # Null terminator
            break
        elif byte_val == 10:  # Line feed
            bytes_list.append('\n')
        elif byte_val == 13:  # Carriage return
            bytes_list.append('\r')
        elif byte_val == 9:  # Tab
            bytes_list.append('\t')
        # Skip non-printable characters
        
        i += 8
    
    return "".join(bytes_list)


# Example usage
if __name__ == "__main__":
    # This would be tested with an actual KD-Code image
    print("KD-Code decoder initialized.")