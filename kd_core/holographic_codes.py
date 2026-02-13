"""
Holographic KD-Code Generator
Simulates holographic effects for KD-Codes to create depth and 3D-like appearance
"""

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import math
from typing import Tuple, Dict, Any, Optional
import base64
from io import BytesIO


class HolographicKDCodeGenerator:
    """
    Generates holographic KD-Codes with simulated 3D and light effects
    """
    
    def __init__(self):
        self.holographic_effects = {
            'rainbow': self._apply_rainbow_effect,
            'depth': self._apply_depth_effect,
            'glow': self._apply_glow_effect,
            'metallic': self._apply_metallic_effect,
            'prismatic': self._apply_prismatic_effect
        }
    
    def generate_holographic_kd_code(self, text: str, effect_type: str = 'rainbow', 
                                   depth_level: float = 0.5, intensity: float = 0.8) -> str:
        """
        Generate a holographic KD-Code with specified effect
        
        Args:
            text: Text to encode in the KD-Code
            effect_type: Type of holographic effect ('rainbow', 'depth', 'glow', 'metallic', 'prismatic')
            depth_level: Level of depth effect (0.0 to 1.0)
            intensity: Intensity of the holographic effect (0.0 to 1.0)
        
        Returns:
            Base64 encoded holographic KD-Code image
        """
        # First, generate a standard KD-Code
        from kd_core.encoder import generate_kd_code
        standard_kd_code_b64 = generate_kd_code(text)
        
        # Decode the standard KD-Code to manipulate it
        img_data = base64.b64decode(standard_kd_code_b64)
        img = Image.open(BytesIO(img_data))
        
        # Apply holographic effect
        if effect_type in self.holographic_effects:
            holographic_img = self.holographic_effects[effect_type](img, depth_level, intensity)
        else:
            # Default to rainbow effect if invalid effect type
            holographic_img = self._apply_rainbow_effect(img, depth_level, intensity)
        
        # Convert back to base64
        buffer = BytesIO()
        holographic_img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return img_base64
    
    def _apply_rainbow_effect(self, img: Image.Image, depth_level: float = 0.5, 
                             intensity: float = 0.8) -> Image.Image:
        """
        Apply rainbow holographic effect to the KD-Code
        
        Args:
            img: Original KD-Code image
            depth_level: Depth level for the effect
            intensity: Intensity of the effect
        
        Returns:
            Image with rainbow holographic effect
        """
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create a new image for the holographic overlay
        width, height = img.size
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Calculate center for radial effect
        center_x, center_y = width // 2, height // 2
        max_radius = min(width, height) // 2
        
        # Create rainbow gradient
        for y in range(height):
            for x in range(width):
                # Calculate distance from center
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                angle = math.atan2(y - center_y, x - center_x)
                
                # Calculate color based on angle and distance
                hue = (angle + math.pi) / (2 * math.pi)  # Normalize to 0-1
                saturation = min(1.0, distance / max_radius) * intensity
                value = 1.0  # Brightness
                
                # Convert HSV to RGB
                rgb = self._hsv_to_rgb(hue, saturation, value)
                
                # Only apply to non-white pixels (the actual KD-Code parts)
                r, g, b, a = img.getpixel((x, y))
                if (r, g, b) != (255, 255, 255):  # Not a white pixel
                    # Blend original color with holographic color
                    blended_r = int(r * (1 - intensity) + rgb[0] * intensity)
                    blended_g = int(g * (1 - intensity) + rgb[1] * intensity)
                    blended_b = int(b * (1 - intensity) + rgb[2] * intensity)
                    
                    overlay.putpixel((x, y), (blended_r, blended_g, blended_b, a))
        
        # Composite the original image with the holographic overlay
        result = Image.alpha_composite(img, overlay)
        return result
    
    def _apply_depth_effect(self, img: Image.Image, depth_level: float = 0.5, 
                           intensity: float = 0.8) -> Image.Image:
        """
        Apply depth/holographic 3D effect to the KD-Code
        
        Args:
            img: Original KD-Code image
            depth_level: Level of depth effect
            intensity: Intensity of the effect
        
        Returns:
            Image with depth holographic effect
        """
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        width, height = img.size
        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Create multiple layers for depth effect
        for layer in range(3):
            offset_x = int((layer - 1) * depth_level * 3)  # Shift each layer slightly
            offset_y = int((layer - 1) * depth_level * 3)
            
            # Create a copy of the image
            layer_img = img.copy()
            
            # Apply color tint to each layer
            if layer == 0:  # Left layer - cyan tint
                layer_img = self._apply_color_tint(layer_img, (0, 255, 255), intensity * 0.3)
            elif layer == 2:  # Right layer - red tint
                layer_img = self._apply_color_tint(layer_img, (255, 0, 0), intensity * 0.3)
            # Middle layer (layer == 1) remains original
            
            # Paste the layer with offset
            result = Image.alpha_composite(result, layer_img.transform(
                (width, height), 
                Image.AFFINE, 
                (1, 0, offset_x, 0, 1, offset_y),
                resample=Image.BILINEAR
            ))
        
        return result
    
    def _apply_glow_effect(self, img: Image.Image, depth_level: float = 0.5, 
                          intensity: float = 0.8) -> Image.Image:
        """
        Apply glowing holographic effect to the KD-Code
        
        Args:
            img: Original KD-Code image
            depth_level: Level of glow effect
            intensity: Intensity of the effect
        
        Returns:
            Image with glow holographic effect
        """
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create glow by blurring and enhancing
        glow_layer = img.filter(ImageFilter.GaussianBlur(radius=2 + depth_level * 3))
        
        # Enhance brightness of the glow
        enhancer = ImageEnhance.Brightness(glow_layer)
        glow_layer = enhancer.enhance(1.0 + intensity)
        
        # Composite original with glow
        result = Image.alpha_composite(glow_layer, img)
        return result
    
    def _apply_metallic_effect(self, img: Image.Image, depth_level: float = 0.5, 
                              intensity: float = 0.8) -> Image.Image:
        """
        Apply metallic holographic effect to the KD-Code
        
        Args:
            img: Original KD-Code image
            depth_level: Level of metallic effect
            intensity: Intensity of the effect
        
        Returns:
            Image with metallic holographic effect
        """
        # Convert to RGB if not already
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Apply emboss effect for metallic look
        embossed = img.filter(ImageFilter.EMBOSS)
        
        # Blend original with embossed version
        blend_factor = intensity * 0.5
        blended = Image.blend(img, embossed, blend_factor)
        
        # Enhance contrast for more metallic appearance
        enhancer = ImageEnhance.Contrast(blended)
        result = enhancer.enhance(1.0 + intensity * 0.5)
        
        return result
    
    def _apply_prismatic_effect(self, img: Image.Image, depth_level: float = 0.5, 
                               intensity: float = 0.8) -> Image.Image:
        """
        Apply prismatic holographic effect to the KD-Code
        
        Args:
            img: Original KD-Code image
            depth_level: Level of prismatic effect
            intensity: Intensity of the effect
        
        Returns:
            Image with prismatic holographic effect
        """
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        width, height = img.size
        result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Apply different color shifts to different regions
        for y in range(height):
            for x in range(width):
                r, g, b, a = img.getpixel((x, y))
                
                # Only apply effect to non-white pixels
                if (r, g, b) != (255, 255, 255):
                    # Calculate position-based color shifts
                    pos_factor_x = x / width
                    pos_factor_y = y / height
                    
                    # Apply prismatic shifts
                    shift_r = int(r * (1 - intensity * 0.3) + 
                                 (math.sin(pos_factor_x * 10) * 255 * intensity * 0.3))
                    shift_g = int(g * (1 - intensity * 0.3) + 
                                 (math.sin(pos_factor_y * 10 + 2) * 255 * intensity * 0.3))
                    shift_b = int(b * (1 - intensity * 0.3) + 
                                 (math.sin((pos_factor_x + pos_factor_y) * 10 + 4) * 255 * intensity * 0.3))
                    
                    # Clamp values to valid range
                    shift_r = max(0, min(255, shift_r))
                    shift_g = max(0, min(255, shift_g))
                    shift_b = max(0, min(255, shift_b))
                    
                    result.putpixel((x, y), (shift_r, shift_g, shift_b, a))
                else:
                    # Keep white pixels as-is
                    result.putpixel((x, y), (r, g, b, a))
        
        return result
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """
        Convert HSV color to RGB
        
        Args:
            h: Hue (0-1)
            s: Saturation (0-1)
            v: Value (0-1)
        
        Returns:
            RGB tuple
        """
        if s == 0.0:
            r = g = b = int(v * 255)
            return (r, g, b)
        
        i = int(h * 6.)
        f = (h * 6.) - i
        p = v * (1. - s)
        q = v * (1. - s * f)
        t = v * (1. - s * (1. - f))
        i = i % 6
        
        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        elif i == 5:
            r, g, b = v, p, q
        
        return (int(r * 255), int(g * 255), int(b * 255))
    
    def _apply_color_tint(self, img: Image.Image, tint_color: Tuple[int, int, int], 
                         intensity: float) -> Image.Image:
        """
        Apply a color tint to an image
        
        Args:
            img: Input image
            tint_color: RGB color to tint with
            intensity: Intensity of the tint (0.0 to 1.0)
        
        Returns:
            Tinted image
        """
        # Create a solid color image
        tint = Image.new('RGBA', img.size, tint_color + (int(255 * intensity),))
        
        # Composite the tint over the original image
        result = Image.alpha_composite(img, tint)
        return result


# Global holographic generator instance
holographic_generator = HolographicKDCodeGenerator()


def generate_holographic_kd_code(text: str, effect_type: str = 'rainbow', 
                               depth_level: float = 0.5, intensity: float = 0.8) -> str:
    """
    Generate a holographic KD-Code with specified effect
    
    Args:
        text: Text to encode in the KD-Code
        effect_type: Type of holographic effect
        depth_level: Level of depth effect (0.0 to 1.0)
        intensity: Intensity of the holographic effect (0.0 to 1.0)
    
    Returns:
        Base64 encoded holographic KD-Code image
    """
    return holographic_generator.generate_holographic_kd_code(text, effect_type, depth_level, intensity)


def get_available_holographic_effects() -> List[str]:
    """
    Get list of available holographic effects
    
    Returns:
        List of available effect names
    """
    return list(holographic_generator.holographic_effects.keys())


# Example usage
if __name__ == "__main__":
    # Example of generating a holographic KD-Code
    text = "Holographic KD-Code"
    
    # Generate with different effects
    rainbow_code = generate_holographic_kd_code(text, effect_type='rainbow', intensity=0.7)
    print(f"Rainbow holographic code generated, length: {len(rainbow_code)}")
    
    depth_code = generate_holographic_kd_code(text, effect_type='depth', depth_level=0.8)
    print(f"Depth holographic code generated, length: {len(depth_code)}")
    
    glow_code = generate_holographic_kd_code(text, effect_type='glow', intensity=0.6)
    print(f"Glow holographic code generated, length: {len(glow_code)}")
    
    available_effects = get_available_holographic_effects()
    print(f"Available holographic effects: {available_effects}")