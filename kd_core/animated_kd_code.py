"""
Animated KD-Code Module with Temporal Encoding
Implements animated KD-Codes that encode additional information through temporal variations
"""

import numpy as np
import cv2
from PIL import Image, ImageDraw
import math
import base64
from io import BytesIO
import json
from typing import List, Tuple, Dict, Any
import zlib
import gzip


class AnimatedKDEncoder:
    """
    Encoder for animated KD-Codes with temporal encoding
    """
    
    def __init__(self):
        self.frame_rate = 30  # frames per second
        self.duration = 2.0   # seconds
    
    def generate_animated_kd_code(self, 
                                 text: str, 
                                 frames: int = 60,
                                 segments_per_ring: int = 16,
                                 anchor_radius: int = 10,
                                 ring_width: int = 15,
                                 scale_factor: int = 5,
                                 max_chars: int = 128,
                                 temporal_encoding: str = 'phase_shift') -> List[str]:
        """
        Generate animated KD-Code with temporal encoding
        
        Args:
            text: Input text to encode
            frames: Number of frames in the animation
            segments_per_ring: Number of segments per ring
            anchor_radius: Radius of the central anchor
            ring_width: Width of each ring
            scale_factor: Scaling factor for the image
            max_chars: Maximum number of characters
            temporal_encoding: Type of temporal encoding ('phase_shift', 'intensity', 'frequency')
        
        Returns:
            List of base64 encoded frames
        """
        if len(text) > max_chars:
            raise ValueError(f"Input text exceeds maximum length of {max_chars} characters")
        
        # Convert text to bitstream
        bitstream = self._text_to_bitstream(text)
        
        # Apply temporal encoding based on the selected method
        if temporal_encoding == 'phase_shift':
            return self._generate_phase_shift_animation(
                bitstream, frames, segments_per_ring, anchor_radius, ring_width, scale_factor
            )
        elif temporal_encoding == 'intensity':
            return self._generate_intensity_modulation_animation(
                bitstream, frames, segments_per_ring, anchor_radius, ring_width, scale_factor
            )
        elif temporal_encoding == 'frequency':
            return self._generate_frequency_modulation_animation(
                bitstream, frames, segments_per_ring, anchor_radius, ring_width, scale_factor
            )
        else:
            raise ValueError(f"Unknown temporal encoding method: {temporal_encoding}")
    
    def _text_to_bitstream(self, text: str) -> List[int]:
        """Convert text to bitstream"""
        bitstream = []
        for char in text:
            ascii_val = ord(char)
            if ascii_val > 255:
                raise ValueError(f"Character '{char}' is outside the 8-bit ASCII range")
            
            binary = format(ascii_val, '08b')  # 8-bit binary representation
            for bit in binary:
                bitstream.append(int(bit))
        
        return bitstream
    
    def _generate_phase_shift_animation(self, 
                                       bitstream: List[int], 
                                       frames: int, 
                                       segments_per_ring: int,
                                       anchor_radius: int,
                                       ring_width: int,
                                       scale_factor: int) -> List[str]:
        """Generate animation using phase shift temporal encoding"""
        frames_list = []
        
        # Calculate number of rings needed
        total_bits = len(bitstream)
        rings_needed = math.ceil(total_bits / segments_per_ring)
        
        # Pad bitstream to fill complete rings
        bits_per_ring = segments_per_ring
        padded_length = rings_needed * bits_per_ring
        padded_bitstream = bitstream + [0] * (padded_length - total_bits)
        
        for frame_idx in range(frames):
            # Calculate phase shift for this frame
            phase_shift = (frame_idx / frames) * 2 * math.pi  # Full rotation over all frames
            
            # Create frame with phase-shifted encoding
            frame = self._create_single_frame(
                padded_bitstream, rings_needed, segments_per_ring,
                anchor_radius, ring_width, scale_factor, phase_shift
            )
            
            # Convert to base64
            buffer = BytesIO()
            frame.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            frames_list.append(img_base64)
        
        return frames_list
    
    def _generate_intensity_modulation_animation(self, 
                                                bitstream: List[int], 
                                                frames: int, 
                                                segments_per_ring: int,
                                                anchor_radius: int,
                                                ring_width: int,
                                                scale_factor: int) -> List[str]:
        """Generate animation using intensity modulation temporal encoding"""
        frames_list = []
        
        # Calculate number of rings needed
        total_bits = len(bitstream)
        rings_needed = math.ceil(total_bits / segments_per_ring)
        
        # Pad bitstream to fill complete rings
        bits_per_ring = segments_per_ring
        padded_length = rings_needed * bits_per_ring
        padded_bitstream = bitstream + [0] * (padded_length - total_bits)
        
        for frame_idx in range(frames):
            # Calculate intensity modulation factor for this frame
            intensity_factor = 0.5 + 0.5 * math.sin(frame_idx * 2 * math.pi / frames)
            
            # Create frame with intensity-modulated encoding
            frame = self._create_single_frame(
                padded_bitstream, rings_needed, segments_per_ring,
                anchor_radius, ring_width, scale_factor,
                intensity_factor=intensity_factor
            )
            
            # Convert to base64
            buffer = BytesIO()
            frame.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            frames_list.append(img_base64)
        
        return frames_list
    
    def _generate_frequency_modulation_animation(self, 
                                                bitstream: List[int], 
                                                frames: int, 
                                                segments_per_ring: int,
                                                anchor_radius: int,
                                                ring_width: int,
                                                scale_factor: int) -> List[str]:
        """Generate animation using frequency modulation temporal encoding"""
        frames_list = []
        
        # Calculate number of rings needed
        total_bits = len(bitstream)
        rings_needed = math.ceil(total_bits / segments_per_ring)
        
        # Pad bitstream to fill complete rings
        bits_per_ring = segments_per_ring
        padded_length = rings_needed * bits_per_ring
        padded_bitstream = bitstream + [0] * (padded_length - total_bits)
        
        for frame_idx in range(frames):
            # Calculate frequency modulation for this frame
            freq_mod = 1.0 + 0.5 * math.sin(frame_idx * 4 * math.pi / frames)  # Double frequency
            
            # Create frame with frequency-modulated encoding
            frame = self._create_single_frame(
                padded_bitstream, rings_needed, segments_per_ring,
                anchor_radius, ring_width, scale_factor,
                frequency_mod=freq_mod
            )
            
            # Convert to base64
            buffer = BytesIO()
            frame.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            frames_list.append(img_base64)
        
        return frames_list
    
    def _create_single_frame(self, 
                           bitstream: List[int], 
                           rings_needed: int, 
                           segments_per_ring: int,
                           anchor_radius: int,
                           ring_width: int,
                           scale_factor: int,
                           phase_shift: float = 0.0,
                           intensity_factor: float = 1.0,
                           frequency_mod: float = 1.0) -> Image.Image:
        """Create a single frame of the animated KD-Code"""
        # Calculate image size based on number of rings
        outer_radius = anchor_radius + rings_needed * ring_width + ring_width  # Extra space for distortion ring
        image_size = int((outer_radius * 2 + 20) * scale_factor)  # Add margin and scale
        
        # Create blank white image
        img = Image.new('RGB', (image_size, image_size), 'white')
        draw = ImageDraw.Draw(img)
        
        # Calculate center of the image
        center_x, center_y = image_size // 2, image_size // 2
        
        # Draw central anchor (solid black circle)
        anchor_radius_scaled = anchor_radius * scale_factor
        draw.ellipse([
            center_x - anchor_radius_scaled, 
            center_y - anchor_radius_scaled, 
            center_x + anchor_radius_scaled, 
            center_y + anchor_radius_scaled
        ], fill='black')
        
        # Draw orientation fin (isosceles triangle pointing upward)
        fin_height_scaled = ring_width * scale_factor
        fin_base_scaled = ring_width * scale_factor
        fin_points = [
            (center_x, center_y - anchor_radius_scaled),  # Apex at top of anchor
            (center_x - fin_base_scaled//2, center_y - anchor_radius_scaled + fin_height_scaled),
            (center_x + fin_base_scaled//2, center_y - anchor_radius_scaled + fin_height_scaled)
        ]
        draw.polygon(fin_points, fill='black')
        
        # Draw data rings with temporal encoding
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
            
            # Draw each segment in the ring with temporal encoding
            angle_step = 2 * math.pi / segments_per_ring
            
            for seg_idx, bit in enumerate(ring_bits):
                # Calculate angles for this segment with phase shift
                base_angle = seg_idx * angle_step
                shifted_angle = base_angle + phase_shift
                
                # Apply frequency modulation to angle
                modulated_angle = shifted_angle * frequency_mod
                
                start_angle = math.degrees(modulated_angle)
                end_angle = math.degrees(modulated_angle + angle_step)
                
                # Skip drawing if bit is 0 (white segment)
                if bit == 1:
                    # Apply intensity modulation
                    if intensity_factor < 0.3:
                        fill_color = 'gray'  # Dimmed for low intensity
                    elif intensity_factor > 0.7:
                        fill_color = 'black'  # Bright for high intensity
                    else:
                        fill_color = 'darkgray'  # Medium for mid intensity
                    
                    # Draw an annular segment for the black segment
                    self._draw_annular_segment(
                        draw, center_x, center_y, 
                        ring_inner_radius_scaled, ring_outer_radius_scaled,
                        start_angle, end_angle, fill_color
                    )
        
        # Draw distortion ring (thin black circle at the outer edge)
        distortion_radius_scaled = (anchor_radius + rings_needed * ring_width) * scale_factor
        draw.ellipse([
            center_x - distortion_radius_scaled, 
            center_y - distortion_radius_scaled, 
            center_x + distortion_radius_scaled, 
            center_y + distortion_radius_scaled
        ], outline='black', width=max(1, int(2*scale_factor)))
        
        return img
    
    def _draw_annular_segment(self, draw, center_x, center_y, inner_radius, outer_radius, 
                             start_angle, end_angle, fill_color):
        """Draw an annular segment (part of a ring)"""
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


class AnimatedKDVideoEncoder:
    """
    Encoder that creates video files from animated KD-Codes
    """
    
    def __init__(self):
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    def create_video_from_frames(self, frames: List[str], output_path: str, fps: int = 30) -> bool:
        """
        Create a video file from animated KD-Code frames
        
        Args:
            frames: List of base64 encoded frames
            output_path: Path to save the video file
            fps: Frames per second
        
        Returns:
            True if successful, False otherwise
        """
        if not frames:
            return False
        
        # Decode the first frame to get dimensions
        first_frame_data = base64.b64decode(frames[0])
        first_img = Image.open(BytesIO(first_frame_data))
        img_array = np.array(first_img)
        
        # Ensure image is in BGR format for OpenCV
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        height, width = img_array.shape[:2]
        
        # Create video writer
        video_writer = cv2.VideoWriter(output_path, self.fourcc, fps, (width, height))
        
        # Write all frames to video
        for frame_b64 in frames:
            try:
                # Decode base64 to image
                frame_data = base64.b64decode(frame_b64)
                img = Image.open(BytesIO(frame_data))
                img_array = np.array(img)
                
                # Convert RGB to BGR if needed
                if len(img_array.shape) == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Write frame to video
                video_writer.write(img_array)
            except Exception as e:
                print(f"Error processing frame: {e}")
                continue
        
        # Release the video writer
        video_writer.release()
        return True


# Example usage
if __name__ == "__main__":
    # Example of creating animated KD-Code
    encoder = AnimatedKDEncoder()
    
    # Generate animated KD-Code
    frames = encoder.generate_animated_kd_code(
        "Animated KD-Code!",
        frames=30,
        temporal_encoding='phase_shift'
    )
    
    print(f"Generated {len(frames)} frames for animated KD-Code")
    
    # Create video from frames
    video_encoder = AnimatedKDVideoEncoder()
    success = video_encoder.create_video_from_frames(frames, "animated_kd_code.mp4", fps=15)
    
    if success:
        print("Video created successfully: animated_kd_code.mp4")
    else:
        print("Failed to create video")