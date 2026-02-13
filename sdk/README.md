# KD-Code SDK

The official SDK for integrating KD-Code functionality into third-party applications.

## Overview

The KD-Code SDK provides a simple interface for generating and scanning KD-Codes from within your own applications. It wraps the KD-Code API with convenient methods and handles authentication, error handling, and data formatting.

## Installation

Install the SDK using pip:

```bash
pip install kdcode-sdk
```

## Quick Start

Here's a simple example of how to use the SDK:

```python
from kdcode_sdk import KDCodeSDK

# Initialize the SDK
sdk = KDCodeSDK(base_url="http://localhost:5000", api_key="your-api-key")

# Generate a KD-Code
result = sdk.generate_kd_code("Hello, World!")
print("Generated KD-Code:", result['image'])

# Scan a KD-Code from an image
with open("kdcode.png", "rb") as f:
    image_data = f.read()
    
scan_result = sdk.scan_kd_code(image_data)
print("Scanned text:", scan_result['data'])
```

## Features

- **Simple API**: Clean, intuitive methods for common operations
- **Error Handling**: Comprehensive error handling and meaningful error messages
- **Session Management**: Automatic session management and authentication
- **Flexible Options**: Support for all KD-Code generation and scanning options
- **Batch Operations**: Support for processing multiple codes at once

## API Reference

### Initialization

```python
from kdcode_sdk import KDCodeSDK

sdk = KDCodeSDK(base_url="http://localhost:5000", api_key="your-api-key")
```

### Generate KD-Code

```python
result = sdk.generate_kd_code(
    text="Your text here",
    segments_per_ring=16,
    anchor_radius=10,
    ring_width=15,
    scale_factor=5,
    compression_quality=95,
    foreground_color="black",
    background_color="white",
    theme="default"
)
```

### Scan KD-Code

```python
with open("image.png", "rb") as f:
    image_data = f.read()

result = sdk.scan_kd_code(
    image_data,
    segments_per_ring=16,
    min_anchor_radius=5,
    max_anchor_radius=100
)
```

### Batch Generation

```python
texts = ["Text 1", "Text 2", "Text 3"]
result = sdk.batch_generate(texts, segments_per_ring=16)
```

### Health Check

```python
health = sdk.get_health()
print(health['status'])  # Should print "healthy"
```

## Authentication

If your KD-Code service requires authentication, pass your API key during initialization:

```python
sdk = KDCodeSDK(base_url="http://your-service.com", api_key="your-api-key")
```

## Error Handling

The SDK raises exceptions for API errors:

```python
try:
    result = sdk.generate_kd_code("Hello")
except Exception as e:
    print(f"Error: {e}")
```

## Development

To contribute to the SDK:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

### Running Tests

```bash
pip install -e .[dev]
pytest
```

## License

MIT License