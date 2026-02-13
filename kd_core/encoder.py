"""
KD-Code Encoder Module
Implements the generation of KD-Codes as specified.
"""

import numpy as np
import cv2
from PIL import Image, ImageDraw
import math
import base64
from io import BytesIO
from .config import (
    DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
    DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS, MAX_RINGS, MAX_IMAGE_SIZE,
    ALLOWED_SEGMENTS_VALUES
)


def generate_kd_code(text, segments_per_ring=DEFAULT_SEGMENTS_PER_RING, anchor_radius=DEFAULT_ANCHOR_RADIUS, ring_width=DEFAULT_RING_WIDTH, scale_factor=DEFAULT_SCALE_FACTOR, max_chars=DEFAULT_MAX_CHARS, compression_quality=95, 
                     foreground_color='black', background_color='white', theme=None):
    """
    Generate a KD-Code image from input text.
    
    Args:
        text (str): Input text to encode (max 128 characters by default)
        segments_per_ring (int): Number of segments per ring (default 16, configurable to 32)
        anchor_radius (int): Radius of the central anchor circle in pixels
        ring_width (int): Width of each data ring in pixels
        scale_factor (int): Scaling factor for the image (to improve quality)
        max_chars (int): Maximum number of characters allowed (default 128)
        compression_quality (int): Quality for image compression (1-100, higher means better quality)
        foreground_color (str): Color for the foreground elements (bits, anchor, etc.)
        background_color (str): Color for the background
        theme (str): Predefined theme ('dark', 'light', 'colorful', etc.) - overrides individual colors
    
    Returns:
        str: Base64 encoded PNG image of the KD-Code
    
    Raises:
        ValueError: If input parameters are invalid
        TypeError: If input types are incorrect
    """
    # Validate inputs
    if not isinstance(text, str):
        raise TypeError("Input text must be a string")
    
    if not isinstance(segments_per_ring, int) or segments_per_ring <= 0:
        raise ValueError("segments_per_ring must be a positive integer")
    
    if segments_per_ring not in ALLOWED_SEGMENTS_VALUES:  # Common values
        raise ValueError(f"segments_per_ring should be one of {ALLOWED_SEGMENTS_VALUES} for optimal results")
    
    if not isinstance(anchor_radius, int) or anchor_radius <= 0:
        raise ValueError("anchor_radius must be a positive integer")
    
    if not isinstance(ring_width, int) or ring_width <= 0:
        raise ValueError("ring_width must be a positive integer")
    
    if not isinstance(scale_factor, int) or scale_factor <= 0:
        raise ValueError("scale_factor must be a positive integer")
    
    if len(text) > max_chars:
        raise ValueError(f"Input text exceeds maximum length of {max_chars} characters")
    
    if len(text) == 0:
        raise ValueError("Input text cannot be empty")
    
    if not isinstance(compression_quality, int) or compression_quality < 1 or compression_quality > 100:
        raise ValueError("compression_quality must be an integer between 1 and 100")
    
    # Validate colors
    if not isinstance(foreground_color, str) or not isinstance(background_color, str):
        raise ValueError("Colors must be strings")
    
    # Apply theme if specified
    if theme:
        if theme.lower() == 'dark':
            background_color = 'black'
            foreground_color = 'white'
        elif theme.lower() == 'colorful':
            background_color = 'white'
            foreground_color = '#FF6B6B'  # Coral red
        elif theme.lower() == 'business':
            background_color = 'white'
            foreground_color = '#2C3E50'  # Dark blue-gray
        elif theme.lower() == 'nature':
            background_color = '#F0F8E8'  # Light green
            foreground_color = '#2E8B57'  # Sea green
        # Add more themes as needed
    
    # Convert text to bitstream (using ASCII encoding)
    bitstream = []
    for char in text:
        # Convert each character to its ASCII value and then to 8-bit binary
        ascii_val = ord(char)
        if ascii_val > 255:
            raise ValueError(f"Character '{char}' is outside the 8-bit ASCII range")
        
        binary = format(ascii_val, '08b')  # 8-bit binary representation
        for bit in binary:
            bitstream.append(int(bit))
    
    # Calculate number of rings needed
    total_bits = len(bitstream)
    rings_needed = math.ceil(total_bits / segments_per_ring)
    
    # Limit the number of rings to prevent extremely large images
    if rings_needed > MAX_RINGS:
        raise ValueError(f"Input text is too long and would require {rings_needed} rings. "
                         f"Maximum allowed is {MAX_RINGS} rings.")
    
    # Pad bitstream to fill complete rings
    bits_per_ring = segments_per_ring
    padded_length = rings_needed * bits_per_ring
    bitstream.extend([0] * (padded_length - total_bits))
    
    # Calculate image size based on number of rings
    outer_radius = anchor_radius + rings_needed * ring_width + ring_width  # Extra space for distortion ring
    image_size = int((outer_radius * 2 + 20) * scale_factor)  # Add margin and scale
    
    # Validate that image size is reasonable
    if image_size > MAX_IMAGE_SIZE:
        raise ValueError(f"Calculated image size ({image_size}) exceeds maximum allowed size ({MAX_IMAGE_SIZE})")
    
    # Create image with custom background color
    img = Image.new('RGB', (image_size, image_size), background_color)
    draw = ImageDraw.Draw(img)
    
    # Calculate center of the image
    center_x, center_y = image_size // 2, image_size // 2
    
    # Draw central anchor (solid foreground color circle)
    anchor_radius_scaled = anchor_radius * scale_factor
    draw.ellipse([
        center_x - anchor_radius_scaled, 
        center_y - anchor_radius_scaled, 
        center_x + anchor_radius_scaled, 
        center_y + anchor_radius_scaled
    ], fill=foreground_color)
    
    # Draw orientation fin (isosceles triangle pointing upward)
    fin_height_scaled = ring_width * scale_factor
    fin_base_scaled = ring_width * scale_factor
    fin_points = [
        (center_x, center_y - anchor_radius_scaled),  # Apex at top of anchor
        (center_x - fin_base_scaled//2, center_y - anchor_radius_scaled + fin_height_scaled),
        (center_x + fin_base_scaled//2, center_y - anchor_radius_scaled + fin_height_scaled)
    ]
    draw.polygon(fin_points, fill=foreground_color)
    
    # Draw data rings
    for ring_idx in range(rings_needed):
        # Calculate radius for this ring
        ring_outer_radius = anchor_radius + (ring_idx + 1) * ring_width
        ring_inner_radius = anchor_radius + ring_idx * ring_width
        
        # Scale radii
        ring_inner_radius_scaled = ring_inner_radius * scale_factor
        ring_outer_radius_scaled = (ring_inner_radius + ring_width) * scale_factor
        
        # Get bits for this ring
        start_bit = ring_idx * segments_per_ring
        end_bit = min(start_bit + segments_per_ring, len(bitstream))
        ring_bits = bitstream[start_bit:end_bit]
        
        # Draw each segment in the ring
        angle_step = 2 * math.pi / segments_per_ring
        
        for seg_idx, bit in enumerate(ring_bits):
            # Calculate angles for this segment
            start_angle = seg_idx * angle_step
            end_angle = (seg_idx + 1) * angle_step
            
            # Skip drawing if bit is 0 (background color segment)
            if bit == 1:
                # Draw an annular segment for the foreground color segment
                draw_annular_segment(draw, center_x, center_y, 
                                   ring_inner_radius_scaled, ring_outer_radius_scaled,
                                   math.degrees(start_angle), math.degrees(end_angle), foreground_color)
    
    # Draw distortion ring (thin foreground color circle at the outer edge)
    distortion_radius_scaled = (anchor_radius + rings_needed * ring_width) * scale_factor
    draw.ellipse([
        center_x - distortion_radius_scaled, 
        center_y - distortion_radius_scaled, 
        center_x + distortion_radius_scaled, 
        center_y + distortion_radius_scaled
    ], outline=foreground_color, width=max(1, int(2*scale_factor)))
    
    # Convert image to base64
    buffer = BytesIO()
    
    # Use JPEG format for compression if quality is less than 100, otherwise use PNG
    if compression_quality < 100:
        # Convert to RGB if not already (PNG might have alpha channel)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format='JPEG', quality=compression_quality, optimize=True)
    else:
        img.save(buffer, format='PNG')
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return img_base64


def draw_annular_segment(draw, center_x, center_y, inner_radius, outer_radius, start_angle, end_angle, fill_color):
    """
    Draw an annular segment (part of a ring) more efficiently.
    """
    # Ensure radii are positive and valid
    if inner_radius < 0 or outer_radius <= 0 or inner_radius >= outer_radius:
        return  # Invalid radii, skip drawing
    
    # Create a path for the annular segment
    from PIL import ImagePath
    path = ImagePath.Path()
    
    # Calculate points along the outer arc
    outer_points = []
    inner_points = []
    
    # Number of points to approximate the arc (more points = smoother curve)
    num_points = max(10, int(abs(end_angle - start_angle) * 0.5))  # At least 10 points
    
    for i in range(num_points + 1):
        t = i / num_points
        angle = start_angle + t * (end_angle - start_angle)
        x_outer = center_x + outer_radius * math.cos(math.radians(angle))
        y_outer = center_y + outer_radius * math.sin(math.radians(angle))
        outer_points.append((x_outer, y_outer))
    
    # Calculate points along the inner arc (in reverse order)
    for i in range(num_points + 1):
        t = i / num_points
        angle = end_angle - t * (end_angle - start_angle)
        x_inner = center_x + inner_radius * math.cos(math.radians(angle))
        y_inner = center_y + inner_radius * math.sin(math.radians(angle))
        inner_points.append((x_inner, y_inner))
    
    # Combine points to form the complete path
    all_points = outer_points + inner_points
    
    # Draw the polygon
    draw.polygon(all_points, fill=fill_color)


# Example usage
if __name__ == "__main__":
    # Generate a sample KD-Code
    sample_text = "Hello, KD-Code!"
    try:
        kd_code_image = generate_kd_code(sample_text)
        print(f"Generated KD-Code for: '{sample_text}'")
        print(f"Base64 length: {len(kd_code_image)}")
    except Exception as e:
        print(f"Error generating KD-Code: {e}")