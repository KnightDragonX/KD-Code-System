"""
IoT Device Integration API for KD-Code System
Provides APIs and protocols for integrating KD-Codes with IoT devices
"""

import json
import requests
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional, List
import logging
import uuid
from datetime import datetime
import socket
import struct


class IoTDeviceManager:
    """
    Manages IoT device integration with KD-Code system
    """
    
    def __init__(self):
        self.devices = {}  # Dictionary to store registered devices
        self.device_sessions = {}  # Active sessions
        self.logger = logging.getLogger(__name__)
    
    def register_iot_device(self, device_id: str, device_type: str, 
                          device_name: str, capabilities: List[str] = None) -> Dict[str, Any]:
        """
        Register an IoT device with the KD-Code system
        
        Args:
            device_id: Unique identifier for the device
            device_type: Type of device ('scanner', 'printer', 'display', 'sensor', etc.)
            device_name: Human-readable name for the device
            capabilities: List of device capabilities
        
        Returns:
            Registration result
        """
        if capabilities is None:
            capabilities = []
        
        # Generate a registration token for the device
        registration_token = str(uuid.uuid4())
        
        device_info = {
            'device_id': device_id,
            'device_type': device_type,
            'device_name': device_name,
            'capabilities': capabilities,
            'registration_token': registration_token,
            'registered_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'status': 'registered',
            'ip_address': request.remote_addr if request else 'unknown'
        }
        
        self.devices[device_id] = device_info
        
        self.logger.info(f"IoT device registered: {device_id} ({device_name})")
        
        return {
            'status': 'success',
            'device_id': device_id,
            'registration_token': registration_token,
            'message': 'Device registered successfully'
        }
    
    def authenticate_iot_device(self, device_id: str, registration_token: str) -> bool:
        """
        Authenticate an IoT device using its registration token
        
        Args:
            device_id: Device ID to authenticate
            registration_token: Registration token
        
        Returns:
            True if authentication successful, False otherwise
        """
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        return device['registration_token'] == registration_token
    
    def update_device_status(self, device_id: str, status: str, 
                           additional_info: Dict[str, Any] = None) -> bool:
        """
        Update the status of an IoT device
        
        Args:
            device_id: ID of the device
            status: New status ('active', 'inactive', 'error', 'maintenance')
            additional_info: Additional status information (optional)
        
        Returns:
            True if successful, False otherwise
        """
        if device_id not in self.devices:
            return False
        
        self.devices[device_id]['status'] = status
        self.devices[device_id]['last_updated'] = datetime.now().isoformat()
        
        if additional_info:
            self.devices[device_id]['additional_info'] = additional_info
        
        self.logger.info(f"Device {device_id} status updated to: {status}")
        return True
    
    def get_device_capabilities(self, device_id: str) -> Optional[List[str]]:
        """
        Get the capabilities of an IoT device
        
        Args:
            device_id: ID of the device
        
        Returns:
            List of device capabilities or None if device not found
        """
        if device_id not in self.devices:
            return None
        
        return self.devices[device_id]['capabilities']
    
    def send_command_to_device(self, device_id: str, command: str, 
                             parameters: Dict[str, Any] = None) -> bool:
        """
        Send a command to an IoT device
        
        Args:
            device_id: ID of the target device
            command: Command to send
            parameters: Command parameters (optional)
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        
        # In a real implementation, this would send the command to the actual device
        # For this example, we'll just log the command
        command_data = {
            'command': command,
            'parameters': parameters or {},
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"Command sent to device {device_id}: {command}")
        
        # Simulate command delivery
        # In a real system, this would use MQTT, HTTP, or another protocol
        return True
    
    def get_registered_devices(self) -> List[Dict[str, Any]]:
        """
        Get all registered IoT devices
        
        Returns:
            List of registered device information
        """
        return list(self.devices.values())
    
    def remove_device(self, device_id: str) -> bool:
        """
        Remove a device from the registry
        
        Args:
            device_id: ID of the device to remove
        
        Returns:
            True if successful, False otherwise
        """
        if device_id in self.devices:
            del self.devices[device_id]
            if device_id in self.device_sessions:
                del self.device_sessions[device_id]
            
            self.logger.info(f"Device {device_id} removed from registry")
            return True
        
        return False
    
    def get_device_by_type(self, device_type: str) -> List[Dict[str, Any]]:
        """
        Get all devices of a specific type
        
        Args:
            device_type: Type of device to filter by
        
        Returns:
            List of devices matching the type
        """
        return [device for device in self.devices.values() 
                if device['device_type'] == device_type]


class KDCodeIoTAPI:
    """
    API endpoints for IoT device integration
    """
    
    def __init__(self):
        self.device_manager = IoTDeviceManager()
        self.logger = logging.getLogger(__name__)
    
    def handle_device_registration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle IoT device registration request
        
        Args:
            data: Registration data from device
        
        Returns:
            Registration response
        """
        device_id = data.get('device_id')
        device_type = data.get('device_type')
        device_name = data.get('device_name')
        capabilities = data.get('capabilities', [])
        
        if not device_id or not device_type or not device_name:
            return {
                'status': 'error',
                'message': 'device_id, device_type, and device_name are required'
            }
        
        return self.device_manager.register_iot_device(device_id, device_type, device_name, capabilities)
    
    def handle_device_authentication(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle IoT device authentication request
        
        Args:
            data: Authentication data from device
        
        Returns:
            Authentication response
        """
        device_id = data.get('device_id')
        registration_token = data.get('registration_token')
        
        if not device_id or not registration_token:
            return {
                'status': 'error',
                'message': 'device_id and registration_token are required'
            }
        
        is_authenticated = self.device_manager.authenticate_iot_device(device_id, registration_token)
        
        if is_authenticated:
            # Create a session for the authenticated device
            session_id = str(uuid.uuid4())
            self.device_manager.device_sessions[device_id] = {
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            
            return {
                'status': 'success',
                'session_id': session_id,
                'message': 'Device authenticated successfully'
            }
        else:
            return {
                'status': 'error',
                'message': 'Authentication failed'
            }
    
    def handle_generate_request(self, device_id: str, session_id: str, 
                              data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle KD-Code generation request from IoT device
        
        Args:
            device_id: ID of the requesting device
            session_id: Session ID for the device
            data: Generation request data
        
        Returns:
            Generation response
        """
        # Verify device session
        if device_id not in self.device_manager.device_sessions:
            return {'status': 'error', 'message': 'Invalid session'}
        
        session = self.device_manager.device_sessions[device_id]
        if session['session_id'] != session_id:
            return {'status': 'error', 'message': 'Invalid session'}
        
        text = data.get('text')
        if not text:
            return {'status': 'error', 'message': 'Text is required for generation'}
        
        # Import KD-Code generation function
        from kd_core.encoder import generate_kd_code
        
        try:
            # Generate KD-Code
            kd_code_b64 = generate_kd_code(text)
            
            return {
                'status': 'success',
                'kd_code': kd_code_b64,
                'message': 'KD-Code generated successfully'
            }
        except Exception as e:
            self.logger.error(f"Error generating KD-Code for device {device_id}: {e}")
            return {'status': 'error', 'message': f'Generation failed: {str(e)}'}
    
    def handle_scan_request(self, device_id: str, session_id: str, 
                          data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle KD-Code scanning request from IoT device
        
        Args:
            device_id: ID of the requesting device
            session_id: Session ID for the device
            data: Scan request data
        
        Returns:
            Scan response
        """
        # Verify device session
        if device_id not in self.device_manager.device_sessions:
            return {'status': 'error', 'message': 'Invalid session'}
        
        session = self.device_manager.device_sessions[device_id]
        if session['session_id'] != session_id:
            return {'status': 'error', 'message': 'Invalid session'}
        
        image_data = data.get('image_data')
        if not image_data:
            return {'status': 'error', 'message': 'Image data is required for scanning'}
        
        # Import KD-Code scanning function
        from kd_core.decoder import decode_kd_code
        import base64
        
        try:
            # Decode the image data
            if image_data.startswith('data:image'):
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(image_data)
            
            # Decode KD-Code
            decoded_text = decode_kd_code(image_bytes)
            
            if decoded_text:
                return {
                    'status': 'success',
                    'decoded_text': decoded_text,
                    'message': 'KD-Code scanned successfully'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No KD-Code detected in image'
                }
        except Exception as e:
            self.logger.error(f"Error scanning KD-Code for device {device_id}: {e}")
            return {'status': 'error', 'message': f'Scanning failed: {str(e)}'}
    
    def handle_status_update(self, device_id: str, session_id: str, 
                           data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle device status update request
        
        Args:
            device_id: ID of the device
            session_id: Session ID for the device
            data: Status update data
        
        Returns:
            Status update response
        """
        # Verify device session
        if device_id not in self.device_manager.device_sessions:
            return {'status': 'error', 'message': 'Invalid session'}
        
        session = self.device_manager.device_sessions[device_id]
        if session['session_id'] != session_id:
            return {'status': 'error', 'message': 'Invalid session'}
        
        status = data.get('status')
        additional_info = data.get('additional_info')
        
        if not status:
            return {'status': 'error', 'message': 'Status is required'}
        
        success = self.device_manager.update_device_status(device_id, status, additional_info)
        
        if success:
            return {
                'status': 'success',
                'message': 'Status updated successfully'
            }
        else:
            return {
                'status': 'error',
                'message': 'Failed to update status'
            }


# Global IoT API instance
iot_api = KDCodeIoTAPI()


def initialize_iot_integration():
    """Initialize the IoT integration system"""
    global iot_api
    iot_api = KDCodeIoTAPI()


def register_iot_device(device_id: str, device_type: str, device_name: str, 
                      capabilities: List[str] = None) -> Dict[str, Any]:
    """
    Register an IoT device with the KD-Code system
    
    Args:
        device_id: Unique identifier for the device
        device_type: Type of device ('scanner', 'printer', 'display', etc.)
        device_name: Human-readable name for the device
        capabilities: List of device capabilities
    
    Returns:
        Registration result
    """
    data = {
        'device_id': device_id,
        'device_type': device_type,
        'device_name': device_name,
        'capabilities': capabilities
    }
    
    return iot_api.handle_device_registration(data)


def authenticate_iot_device(device_id: str, registration_token: str) -> Dict[str, Any]:
    """
    Authenticate an IoT device
    
    Args:
        device_id: ID of the device to authenticate
        registration_token: Registration token
    
    Returns:
        Authentication result
    """
    data = {
        'device_id': device_id,
        'registration_token': registration_token
    }
    
    return iot_api.handle_device_authentication(data)


def send_generate_request_to_iot(device_id: str, session_id: str, text: str, 
                               **kwargs) -> Dict[str, Any]:
    """
    Send a KD-Code generation request to an IoT device
    
    Args:
        device_id: ID of the target device
        session_id: Session ID for the device
        text: Text to encode in the KD-Code
        **kwargs: Additional parameters for generation
    
    Returns:
        Generation result
    """
    data = {
        'text': text,
        **kwargs
    }
    
    return iot_api.handle_generate_request(device_id, session_id, data)


def send_scan_request_to_iot(device_id: str, session_id: str, image_data: str) -> Dict[str, Any]:
    """
    Send a KD-Code scan request to an IoT device
    
    Args:
        device_id: ID of the target device
        session_id: Session ID for the device
        image_data: Image data to scan (base64 encoded)
    
    Returns:
        Scan result
    """
    data = {
        'image_data': image_data
    }
    
    return iot_api.handle_scan_request(device_id, session_id, data)


def update_iot_device_status(device_id: str, session_id: str, status: str, 
                           additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Update the status of an IoT device
    
    Args:
        device_id: ID of the device
        session_id: Session ID for the device
        status: New status
        additional_info: Additional status information
    
    Returns:
        Status update result
    """
    data = {
        'status': status,
        'additional_info': additional_info
    }
    
    return iot_api.handle_status_update(device_id, session_id, data)


def get_registered_iot_devices() -> List[Dict[str, Any]]:
    """
    Get all registered IoT devices
    
    Returns:
        List of registered devices
    """
    return iot_api.device_manager.get_registered_devices()


def get_iot_devices_by_type(device_type: str) -> List[Dict[str, Any]]:
    """
    Get all IoT devices of a specific type
    
    Args:
        device_type: Type of device to filter by
    
    Returns:
        List of devices matching the type
    """
    return iot_api.device_manager.get_device_by_type(device_type)


# Flask routes for IoT integration
def add_iot_routes(app: Flask):
    """
    Add IoT integration routes to a Flask app
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/api/iot/register', methods=['POST'])
    def iot_register():
        """Register an IoT device"""
        try:
            data = request.get_json()
            result = register_iot_device(
                data.get('device_id'),
                data.get('device_type'),
                data.get('device_name'),
                data.get('capabilities')
            )
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in IoT registration: {e}")
            return jsonify({'status': 'error', 'message': 'Registration failed'}), 500
    
    @app.route('/api/iot/authenticate', methods=['POST'])
    def iot_authenticate():
        """Authenticate an IoT device"""
        try:
            data = request.get_json()
            result = authenticate_iot_device(
                data.get('device_id'),
                data.get('registration_token')
            )
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in IoT authentication: {e}")
            return jsonify({'status': 'error', 'message': 'Authentication failed'}), 500
    
    @app.route('/api/iot/generate', methods=['POST'])
    def iot_generate():
        """Generate KD-Code via IoT device"""
        try:
            data = request.get_json()
            device_id = data.get('device_id')
            session_id = data.get('session_id')
            
            if not device_id or not session_id:
                return jsonify({'status': 'error', 'message': 'Device ID and session ID required'}), 400
            
            result = send_generate_request_to_iot(device_id, session_id, data.get('text', ''))
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in IoT generation: {e}")
            return jsonify({'status': 'error', 'message': 'Generation failed'}), 500
    
    @app.route('/api/iot/scan', methods=['POST'])
    def iot_scan():
        """Scan KD-Code via IoT device"""
        try:
            data = request.get_json()
            device_id = data.get('device_id')
            session_id = data.get('session_id')
            
            if not device_id or not session_id:
                return jsonify({'status': 'error', 'message': 'Device ID and session ID required'}), 400
            
            result = send_scan_request_to_iot(device_id, session_id, data.get('image_data', ''))
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in IoT scan: {e}")
            return jsonify({'status': 'error', 'message': 'Scanning failed'}), 500
    
    @app.route('/api/iot/status', methods=['POST'])
    def iot_status():
        """Update IoT device status"""
        try:
            data = request.get_json()
            device_id = data.get('device_id')
            session_id = data.get('session_id')
            
            if not device_id or not session_id:
                return jsonify({'status': 'error', 'message': 'Device ID and session ID required'}), 400
            
            result = update_iot_device_status(
                device_id, 
                session_id, 
                data.get('status', 'active'),
                data.get('additional_info')
            )
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Error in IoT status update: {e}")
            return jsonify({'status': 'error', 'message': 'Status update failed'}), 500
    
    @app.route('/api/iot/devices', methods=['GET'])
    def iot_devices():
        """Get all registered IoT devices"""
        try:
            devices = get_registered_iot_devices()
            return jsonify({'status': 'success', 'devices': devices})
        except Exception as e:
            app.logger.error(f"Error getting IoT devices: {e}")
            return jsonify({'status': 'error', 'message': 'Failed to retrieve devices'}), 500


# Example usage
if __name__ == "__main__":
    print("IoT Device Integration API for KD-Code System")
    print("This module provides APIs for integrating KD-Codes with IoT devices")
    
    # Example of how to register a device:
    # device_info = register_iot_device(
    #     device_id="scanner_001",
    #     device_type="scanner",
    #     device_name="Office Scanner Unit 1",
    #     capabilities=["scan", "generate", "display"]
    # )
    # print(f"Device registration result: {device_info}")
    #
    # # Example of how to authenticate a device:
    # auth_result = authenticate_iot_device("scanner_001", device_info['registration_token'])
    # print(f"Authentication result: {auth_result}")
    #
    # # Example of how to generate a code via IoT device:
    # gen_result = send_generate_request_to_iot(
    #     "scanner_001", 
    #     auth_result['session_id'], 
    #     "Hello from IoT Device!"
    # )
    # print(f"Generation result: {gen_result}")
    
    print("Module ready for IoT device integration")