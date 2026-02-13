"""
QR Code Compatibility Module for KD-Code System
Provides QR code generation and decoding alongside KD-Codes
"""

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

import base64
from io import BytesIO


def generate_qr_code(text, box_size=10, border=4):
    """
    Generate a QR code for the given text
    
    Args:
        text (str): Text to encode in QR code
        box_size (int): Size of each box in pixels
        border (int): Border size in boxes
    
    Returns:
        str: Base64 encoded PNG image of the QR code
    """
    if not QR_AVAILABLE:
        raise ImportError("qrcode library not available. Install with 'pip install qrcode[pil]'")
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    
    # Add data and generate
    qr.add_data(text)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return img_base64


def is_qr_compatible(text):
    """
    Check if the text is compatible with QR code standards
    
    Args:
        text (str): Text to check
    
    Returns:
        bool: True if text is QR compatible
    """
    # QR codes can handle most text, but we'll set a reasonable limit
    return len(text) <= 2953  # Max for alphanumeric QR code


# Example usage
if __name__ == "__main__":
    if QR_AVAILABLE:
        sample_text = "Hello, QR Code!"
        qr_code_image = generate_qr_code(sample_text)
        print(f"Generated QR Code for: '{sample_text}'")
        print(f"Base64 length: {len(qr_code_image)}")
    else:
        print("QR code generation not available - qrcode library not installed")