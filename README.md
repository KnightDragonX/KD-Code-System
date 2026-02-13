# KD-Code System

A novel circular barcode system invented by **K. D. Sithara Nimsara** and **J. A. Umeda Sammani**.

## Creator Information

**Inventors:**
- **K. D. Sithara Nimsara** - Original concept and design
- **J. A. Umeda Sammani** - Co-inventor and design contributor

This implementation is a technical realization of their innovative circular barcode concept.

## Overview

KD-Code is a circular barcode system that encodes text/URLs into a unique circular pattern. This web application provides both generation and scanning capabilities for KD-Codes, featuring advanced functionality including machine learning error correction, blockchain verification, augmented reality overlays, and more.

## Features

- Generate KD-Codes from text/URLs
- Scan KD-Codes using device camera
- Real-time decoding
- Responsive design for mobile and desktop
- Configurable parameters for customization
- Comprehensive error handling
- Machine learning-based error correction
- Blockchain verification for code authenticity
- Augmented reality overlay for code scanning
- Plugin system for custom encoding schemes
- Voice-guided scanning for accessibility
- 3D printable KD-Codes
- Collaborative code editor interface
- Real-time collaborative scanning
- Biometric-enhanced security
- Code lifecycle management system
- Predictive analytics for code usage
- Holographic KD-Codes
- Code versioning and history system
- Quantum-resistant encryption for codes
- Gesture-based code interaction
- Code marketplace for sharing
- Neural network-based pattern recognition
- Multi-modal codes (audio, visual, tactile)
- REST API v2 with GraphQL support
- Webhook system for real-time notifications
- OAuth 2.0 integration for third-party apps
- Zapier integration for workflow automation
- Slack/Teams bot for code generation
- Salesforce integration module
- WordPress/WooCommerce plugin
- Shopify app for e-commerce
- Microsoft Office integration
- Google Workspace add-on
- Zapier triggers for code events
- IFTTT integration for smart home
- API for IoT device integration

## Architecture

- Backend: Flask web application
- Image Processing: OpenCV, NumPy, Pillow
- Frontend: HTML, CSS (Tailwind), JavaScript
- Camera Integration: WebRTC API
- Machine Learning: TensorFlow, scikit-learn
- Blockchain: Smart contracts for verification
- AR: Three.js for augmented reality overlays
- IoT: MQTT protocol for device communication

## Installation

### Prerequisites
- Python 3.9+
- pip package manager
- Docker and Docker Compose (for containerized deployment)

### Quick Setup
```bash
pip install -r requirements.txt
```

### Docker Setup
```bash
# Build and run with Docker Compose
docker-compose up -d
```

## Usage

### Local Development
```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

### Docker Deployment
```bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

## Configuration

The KD-Code system supports various configuration options:

### Generation Parameters
- `segments_per_ring`: Number of segments per ring (8, 16, or 32)
- `anchor_radius`: Radius of the central anchor circle in pixels
- `ring_width`: Width of each data ring in pixels
- `scale_factor`: Scaling factor for the image (to improve quality)
- `max_chars`: Maximum number of characters allowed

### Scanning Parameters
- `segments_per_ring`: Expected number of segments per ring (8, 16, or 32)
- `min_anchor_radius`: Minimum expected anchor radius for filtering
- `max_anchor_radius`: Maximum expected anchor radius for filtering

## API Endpoints

Complete API documentation is available in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

### Generate KD-Code
- **Endpoint**: `POST /api/generate`
- **Request Body**:
  ```json
  {
    "text": "string to encode",
    "segments_per_ring": 16,
    "anchor_radius": 10,
    "ring_width": 15,
    "scale_factor": 5,
    "max_chars": 128
  }
  ```
- **Response**:
  ```json
  {
    "image": "base64_encoded_png",
    "status": "success"
  }
  ```

### Scan KD-Code
- **Endpoint**: `POST /api/scan`
- **Request Body (JSON)**:
  ```json
  {
    "image": "base64_encoded_image",
    "segments_per_ring": 16,
    "min_anchor_radius": 5,
    "max_anchor_radius": 100
  }
  ```
- **Request Body (Form Data)**: Upload image file with key `frame`
- **Response**:
  ```json
  {
    "data": "decoded_text",
    "status": "success"
  }
  ```

## Examples

### Basic Usage
1. Navigate to the Generator tab
2. Enter text in the input field
3. Click "Generate KD-Code"
4. The KD-Code will be displayed and can be downloaded

### Scanning
1. Navigate to the Scanner tab
2. Click "Start Camera"
3. Point your camera at a KD-Code
4. The decoded text will appear automatically

## Development

### Running Tests
```bash
python -m pytest test_kd_code.py
python -m pytest test_e2e.py
```

### Project Structure
```
KD-Code-System/
├── app.py                 # Flask application factory / routes
├── kd_core/
│   ├── __init__.py
│   ├── encoder.py        # KD-Code generation logic
│   ├── decoder.py        # Detection & decoding logic
│   ├── config.py         # Configuration parameters
│   ├── qr_compatibility.py # QR code compatibility
│   ├── data_encryption.py # Data encryption functionality
│   ├── backup_recovery.py # Backup and recovery system
│   ├── batch_operations.py # Batch operations
│   └── bulk_operations.py # Bulk import/export operations
│   ├── ml_error_correction.py # ML-based error correction
│   ├── blockchain_verification.py # Blockchain verification
│   ├── ar_overlay.py # Augmented reality overlay
│   ├── plugin_system.py # Plugin system for custom encodings
│   ├── voice_guidance.py # Voice guidance for accessibility
│   ├── kd_3d_generator.py # 3D printable KD-Codes
│   ├── collaborative_editor.py # Collaborative editor
│   ├── collaborative_scanning.py # Real-time collaborative scanning
│   ├── biometric_security.py # Biometric security
│   ├── lifecycle_management.py # Code lifecycle management
│   ├── predictive_analytics.py # Predictive analytics
│   ├── holographic_codes.py # Holographic KD-Codes
│   ├── versioning.py # Code versioning system
│   ├── quantum_encryption.py # Quantum-resistant encryption
│   ├── gesture_control.py # Gesture-based interaction
│   ├── marketplace.py # Code marketplace
│   ├── neural_pattern_recognition.py # Neural pattern recognition
│   ├── multi_modal_codes.py # Multi-modal codes
│   ├── graphql_api.py # GraphQL API
│   ├── webhook_system.py # Webhook system
│   ├── oauth_integration.py # OAuth integration
│   ├── zapier_integration.py # Zapier integration
│   ├── bot_integration.py # Bot integrations
│   ├── salesforce_integration.py # Salesforce integration
│   ├── google_workspace_addon.py # Google Workspace add-on
│   ├── ms_office_integration.py # Microsoft Office integration
│   ├── shopify-integration/ # Shopify app
│   ├── wordpress-plugin/ # WordPress plugin
│   ├── browser-extension/ # Browser extension
│   ├── mobile/ # Mobile application
│   └── sdk/ # SDK for developers
├── static/               # CSS, JS, assets
├── templates/
│   └── index.html        # SPA or two‑tab layout
├── requirements.txt
├── README.md
├── API_DOCUMENTATION.md  # Complete API documentation
├── USER_GUIDE.md         # User guide
├── DEPLOYMENT_GUIDE.md   # Deployment guide
├── test_kd_code.py       # Unit tests
├── test_e2e.py          # Integration and E2E tests
├── Dockerfile           # Container configuration
├── docker-compose.yml   # Multi-container setup
├── deploy.sh            # Deployment script
├── .github/
│   └── workflows/
│       └── ci-cd.yml    # CI/CD pipeline configuration
└── .dockerignore        # Files to exclude from Docker image
```

### CI/CD Pipeline

The project includes a CI/CD pipeline configuration using GitHub Actions:

1. **Testing**: Runs unit and integration tests on every push/PR
2. **Security Scan**: Performs security scanning using Bandit
3. **Building**: Builds a Docker image on main branch
4. **Deployment**: Deploys to production when changes are merged to main

### Docker Support

The application can be containerized using Docker:

```bash
# Build the image
docker build -t kd-code-system .

# Run the container
docker run -p 5000:5000 kd-code-system
```

### Deployment

For production deployment, use the provided deployment script:

```bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

Complete deployment instructions are available in [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

### Monitoring and Health Checks

The application includes several endpoints for monitoring:

- `/health` - General health status
- `/health/ready` - Readiness check for load balancers
- `/metrics` - Prometheus-compatible metrics

## Documentation

- [API Documentation](API_DOCUMENTATION.md) - Complete API reference
- [User Guide](USER_GUIDE.md) - Detailed user instructions
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Deployment instructions
- [GitHub Setup Instructions](GITHUB_SETUP_INSTRUCTIONS.md) - Instructions for setting up GitHub repository
- [Contributing Guide](CONTRIBUTING.md) - How to contribute to the project

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the inventors K. D. Sithara Nimsara and J. A. Umeda Sammani for the innovative KD-Code concept
- Special thanks to the open-source community for the libraries and tools that made this project possible