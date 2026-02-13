"""
Multi-Modal KD-Code System
Supports audio, visual, and tactile representations of KD-Codes
"""

import numpy as np
import cv2
from PIL import Image, ImageDraw
import base64
from io import BytesIO
import wave
import struct
import math
from typing import Tuple, List, Dict, Any, Optional
import json
import logging


class MultiModalKDCodeGenerator:
    """
    Generates multi-modal KD-Codes that can be represented in audio, visual, and tactile forms
    """
    
    def __init__(self):
        self.audio_freq_base = 440  # Base frequency (A4)
        self.audio_duration = 0.1  # Duration of each audio segment in seconds
        self.audio_sample_rate = 44100  # Standard audio sample rate
        self.logger = logging.getLogger(__name__)
    
    def generate_visual_code(self, text: str, **kwargs) -> str:
        """
        Generate the visual KD-Code (standard circular barcode)
        
        Args:
            text: Text to encode
            **kwargs: Additional parameters for generation
        
        Returns:
            Base64 encoded visual KD-Code image
        """
        from kd_core.encoder import generate_kd_code
        return generate_kd_code(text, **kwargs)
    
    def generate_audio_code(self, text: str, frequency_multiplier: float = 1.0) -> str:
        """
        Generate an audio representation of the KD-Code
        
        Args:
            text: Text to encode
            frequency_multiplier: Multiplier for base frequencies
        
        Returns:
            Base64 encoded WAV audio file
        """
        # Convert text to binary representation
        binary_sequence = self._text_to_binary(text)
        
        # Generate audio signal based on binary sequence
        audio_signal = self._binary_to_audio_signal(binary_sequence, frequency_multiplier)
        
        # Create WAV file
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.audio_sample_rate)
            wav_file.writeframes(audio_signal)
        
        # Encode to base64
        wav_base64 = base64.b64encode(wav_buffer.getvalue()).decode('utf-8')
        return wav_base64
    
    def generate_tactile_code(self, text: str, cell_size: int = 5) -> str:
        """
        Generate a tactile representation of the KD-Code (for visually impaired users)
        
        Args:
            text: Text to encode
            cell_size: Size of each tactile cell in pixels
        
        Returns:
            Base64 encoded tactile KD-Code image
        """
        # First generate the visual code
        from kd_core.encoder import generate_kd_code
        visual_b64 = generate_kd_code(text)
        
        # Decode the visual code to manipulate it for tactile representation
        img_data = base64.b64decode(visual_b64)
        img = Image.open(BytesIO(img_data))
        
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Enhance contrast for tactile representation
        enhanced_img = self._enhance_for_tactile(img, cell_size)
        
        # Convert back to base64
        tactile_buffer = BytesIO()
        enhanced_img.save(tactile_buffer, format='PNG')
        tactile_b64 = base64.b64encode(tactile_buffer.getvalue()).decode('utf-8')
        
        return tactile_b64
    
    def generate_multi_modal_code(self, text: str, include_audio: bool = True, 
                                 include_tactile: bool = True, **kwargs) -> Dict[str, str]:
        """
        Generate a complete multi-modal KD-Code with all modalities
        
        Args:
            text: Text to encode
            include_audio: Whether to include audio representation
            include_tactile: Whether to include tactile representation
            **kwargs: Additional parameters for generation
        
        Returns:
            Dictionary with all modal representations
        """
        result = {
            'text': text,
            'visual': self.generate_visual_code(text, **kwargs),
            'modalities': ['visual']
        }
        
        if include_audio:
            result['audio'] = self.generate_audio_code(text)
            result['modalities'].append('audio')
        
        if include_tactile:
            result['tactile'] = self.generate_tactile_code(text)
            result['modalities'].append('tactile')
        
        return result
    
    def _text_to_binary(self, text: str) -> List[int]:
        """
        Convert text to binary sequence
        
        Args:
            text: Input text
        
        Returns:
            List of binary digits (0s and 1s)
        """
        binary_sequence = []
        for char in text:
            # Convert each character to its ASCII value and then to 8-bit binary
            ascii_val = ord(char)
            binary = format(ascii_val, '08b')  # 8-bit binary representation
            for bit in binary:
                binary_sequence.append(int(bit))
        
        return binary_sequence
    
    def _binary_to_audio_signal(self, binary_sequence: List[int], 
                               frequency_multiplier: float = 1.0) -> bytes:
        """
        Convert binary sequence to audio signal
        
        Args:
            binary_sequence: Binary sequence to convert
            frequency_multiplier: Multiplier for base frequencies
        
        Returns:
            Audio signal as bytes
        """
        # Create audio signal
        total_samples = int(self.audio_duration * self.audio_sample_rate * len(binary_sequence))
        audio_signal = np.zeros(total_samples, dtype=np.int16)
        
        sample_per_bit = int(self.audio_duration * self.audio_sample_rate)
        
        for i, bit in enumerate(binary_sequence):
            start_sample = i * sample_per_bit
            end_sample = start_sample + sample_per_bit
            
            # Use different frequencies for 0 and 1
            if bit == 0:
                freq = self.audio_freq_base * frequency_multiplier  # Lower frequency for 0
            else:
                freq = self.audio_freq_base * 1.5 * frequency_multiplier  # Higher frequency for 1
            
            # Generate sine wave for this bit
            time_array = np.arange(sample_per_bit) / self.audio_sample_rate
            wave_data = np.sin(2 * np.pi * freq * time_array) * 0.3  # 0.3 amplitude
            audio_signal[start_sample:end_sample] = (wave_data * 32767).astype(np.int16)
        
        # Convert to bytes
        byte_signal = audio_signal.tobytes()
        return byte_signal
    
    def _enhance_for_tactile(self, img: Image.Image, cell_size: int) -> Image.Image:
        """
        Enhance an image for tactile representation
        
        Args:
            img: Input image
            cell_size: Size of tactile cells
        
        Returns:
            Enhanced image for tactile representation
        """
        # Increase contrast and make patterns more pronounced
        img_array = np.array(img)
        
        # Apply high-pass filter to enhance edges
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        enhanced = cv2.filter2D(img_array, -1, kernel)
        
        # Convert back to PIL Image
        enhanced_img = Image.fromarray(enhanced)
        
        # Increase the size to make tactile features more prominent
        width, height = enhanced_img.size
        new_width = width * cell_size // 10  # Adjust based on cell size
        new_height = height * cell_size // 10
        tactile_img = enhanced_img.resize((new_width, new_height), Image.NEAREST)
        
        return tactile_img


class MultiModalKDCodeDecoder:
    """
    Decodes multi-modal KD-Codes from various input modalities
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def decode_audio_code(self, audio_data: bytes) -> Optional[str]:
        """
        Decode a KD-Code from audio representation
        
        Args:
            audio_data: Audio data as bytes (WAV format)
        
        Returns:
            Decoded text or None if decoding fails
        """
        try:
            # Read WAV file
            wav_buffer = BytesIO(audio_data)
            with wave.open(wav_buffer, 'r') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                sample_rate = wav_file.getframerate()
                sampwidth = wav_file.getsampwidth()
                nchannels = wav_file.getnchannels()
            
            # Convert to numpy array
            if sampwidth == 1:
                dtype = np.uint8
            elif sampwidth == 2:
                dtype = np.int16
            elif sampwidth == 4:
                dtype = np.int32
            else:
                raise ValueError(f"Unsupported sample width: {sampwidth}")
            
            audio_array = np.frombuffer(frames, dtype=dtype)
            
            # If stereo, convert to mono
            if nchannels == 2:
                audio_array = audio_array.reshape(-1, 2).mean(axis=1)
            
            # Analyze the audio signal to extract binary sequence
            binary_sequence = self._analyze_audio_signal(audio_array, sample_rate)
            
            # Convert binary sequence back to text
            decoded_text = self._binary_to_text(binary_sequence)
            
            return decoded_text
        except Exception as e:
            self.logger.error(f"Error decoding audio KD-Code: {e}")
            return None
    
    def _analyze_audio_signal(self, audio_array: np.ndarray, sample_rate: int) -> List[int]:
        """
        Analyze audio signal to extract binary sequence
        
        Args:
            audio_array: Audio signal as numpy array
            sample_rate: Sample rate of the audio
        
        Returns:
            Binary sequence as list of 0s and 1s
        """
        # Calculate samples per bit based on expected duration
        samples_per_bit = int(0.1 * sample_rate)  # 0.1 seconds per bit
        
        binary_sequence = []
        
        # Process the audio in chunks corresponding to bits
        for i in range(0, len(audio_array), samples_per_bit):
            chunk = audio_array[i:i+samples_per_bit]
            
            if len(chunk) == 0:
                continue
            
            # Calculate dominant frequency in this chunk
            fft = np.fft.fft(chunk)
            magnitude = np.abs(fft[:len(fft)//2])
            peak_freq_idx = np.argmax(magnitude)
            peak_freq = peak_freq_idx * sample_rate / len(chunk)
            
            # Determine if it's a 0 or 1 based on frequency
            # In our encoding: 0 = base frequency, 1 = 1.5 * base frequency
            base_freq = 440.0  # Our base frequency
            threshold_freq = base_freq * 1.25  # Midpoint between 0 and 1 frequencies
            
            bit = 1 if peak_freq > threshold_freq else 0
            binary_sequence.append(bit)
        
        return binary_sequence
    
    def _binary_to_text(self, binary_sequence: List[int]) -> str:
        """
        Convert binary sequence back to text
        
        Args:
            binary_sequence: Binary sequence as list of 0s and 1s
        
        Returns:
            Decoded text
        """
        text = ""
        
        # Process in groups of 8 bits (1 byte)
        for i in range(0, len(binary_sequence), 8):
            byte_bits = binary_sequence[i:i+8]
            
            if len(byte_bits) < 8:
                # Pad with zeros if necessary
                byte_bits.extend([0] * (8 - len(byte_bits)))
            
            # Convert 8 bits to a character
            byte_val = 0
            for bit in byte_bits:
                byte_val = (byte_val << 1) | bit
            
            # Convert to character
            if 32 <= byte_val <= 126:  # Printable ASCII range
                text += chr(byte_val)
            elif byte_val == 0:  # Null terminator
                break
            else:
                # For non-printable characters, we might want to handle differently
                # For now, skip them
                continue
        
        return text
    
    def decode_tactile_code(self, tactile_image_data: bytes) -> Optional[str]:
        """
        Decode a KD-Code from tactile representation
        
        Args:
            tactile_image_data: Tactile image data as bytes
        
        Returns:
            Decoded text or None if decoding fails
        """
        try:
            # For tactile codes, we'll use the same decoding algorithm as visual codes
            # but with preprocessing to normalize the tactile representation
            from kd_core.decoder import decode_kd_code
            
            # Decode the tactile KD-Code using the standard decoder
            decoded_text = decode_kd_code(tactile_image_data)
            
            return decoded_text
        except Exception as e:
            self.logger.error(f"Error decoding tactile KD-Code: {e}")
            return None
    
    def decode_multi_modal_code(self, multimodal_data: Dict[str, str]) -> Optional[str]:
        """
        Decode a multi-modal KD-Code using the most reliable modality available
        
        Args:
            multimodal_data: Dictionary with different modal representations
        
        Returns:
            Decoded text or None if all modalities fail
        """
        # Try each modality in order of reliability
        modalities_to_try = ['visual', 'audio', 'tactile']
        
        for modality in modalities_to_try:
            if modality in multimodal_data:
                if modality == 'visual':
                    # For visual, we need to decode the base64 and use standard decoder
                    from kd_core.decoder import decode_kd_code
                    img_bytes = base64.b64decode(multimodal_data[modality])
                    result = decode_kd_code(img_bytes)
                    if result:
                        return result
                elif modality == 'audio':
                    # Decode audio representation
                    audio_bytes = base64.b64decode(multimodal_data[modality])
                    result = self.decode_audio_code(audio_bytes)
                    if result:
                        return result
                elif modality == 'tactile':
                    # Decode tactile representation
                    tactile_bytes = base64.b64decode(multimodal_data[modality])
                    result = self.decode_tactile_code(tactile_bytes)
                    if result:
                        return result
        
        # If all modalities failed, return None
        return None


# Global multi-modal generator and decoder instances
multi_modal_generator = MultiModalKDCodeGenerator()
multi_modal_decoder = MultiModalKDCodeDecoder()


def initialize_multi_modal_support():
    """Initialize the multi-modal KD-Code support system"""
    global multi_modal_generator, multi_modal_decoder
    multi_modal_generator = MultiModalKDCodeGenerator()
    multi_modal_decoder = MultiModalKDCodeDecoder()


def generate_multi_modal_kd_code(text: str, include_audio: bool = True, 
                               include_tactile: bool = True, **kwargs) -> Dict[str, str]:
    """
    Generate a multi-modal KD-Code with audio, visual, and tactile representations
    
    Args:
        text: Text to encode
        include_audio: Whether to include audio representation
        include_tactile: Whether to include tactile representation
        **kwargs: Additional parameters for generation
    
    Returns:
        Dictionary with all modal representations
    """
    return multi_modal_generator.generate_multi_modal_code(
        text, include_audio, include_tactile, **kwargs
    )


def decode_multi_modal_kd_code(multimodal_data: Dict[str, str]) -> Optional[str]:
    """
    Decode a multi-modal KD-Code using the most reliable available modality
    
    Args:
        multimodal_data: Dictionary with different modal representations
    
    Returns:
        Decoded text or None if all modalities fail
    """
    return multi_modal_decoder.decode_multi_modal_code(multimodal_data)


def decode_audio_kd_code(audio_data: bytes) -> Optional[str]:
    """
    Decode a KD-Code from audio representation
    
    Args:
        audio_data: Audio data as bytes
    
    Returns:
        Decoded text or None if decoding fails
    """
    return multi_modal_decoder.decode_audio_code(audio_data)


def decode_tactile_kd_code(tactile_image_data: bytes) -> Optional[str]:
    """
    Decode a KD-Code from tactile representation
    
    Args:
        tactile_image_data: Tactile image data as bytes
    
    Returns:
        Decoded text or None if decoding fails
    """
    return multi_modal_decoder.decode_tactile_code(tactile_image_data)


# Example usage
if __name__ == "__main__":
    # Initialize multi-modal support
    initialize_multi_modal_support()
    
    # Example of generating a multi-modal KD-Code
    text = "Hello, Multi-Modal World!"
    print(f"Original text: {text}")
    
    # Generate multi-modal code
    multimodal_code = generate_multi_modal_kd_code(
        text, 
        include_audio=True, 
        include_tactile=True,
        segments_per_ring=16,
        anchor_radius=10,
        ring_width=15,
        scale_factor=5
    )
    
    print(f"Generated multi-modal code with modalities: {multimodal_code['modalities']}")
    
    # The multimodal_code contains:
    # - 'visual': Base64 encoded visual KD-Code
    # - 'audio': Base64 encoded audio KD-Code
    # - 'tactile': Base64 encoded tactile KD-Code
    # - 'modalities': List of included modalities
    
    # Example of decoding (would need actual data in a real implementation)
    # decoded_text = decode_multi_modal_kd_code(multimodal_code)
    # print(f"Decoded text: {decoded_text}")
    
    print("Multi-modal KD-Code system initialized successfully!")