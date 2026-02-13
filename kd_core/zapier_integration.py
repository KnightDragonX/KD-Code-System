"""
Zapier Integration Module for KD-Code System
Enables workflow automation through Zapier-compatible webhooks
"""

import json
import hashlib
import hmac
import requests
from flask import Flask, request, jsonify
from typing import Dict, Any, List
import logging
from datetime import datetime


class ZapierIntegration:
    """
    Integration system for connecting KD-Code system with Zapier
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.zapier_webhooks = {}  # Store registered Zapier webhooks
        self.zapier_triggers = {
            'kd_code_generated': self._handle_code_generated_trigger,
            'kd_code_scanned': self._handle_code_scanned_trigger,
            'kd_code_expired': self._handle_code_expired_trigger,
            'batch_operation_completed': self._handle_batch_completed_trigger,
            'user_logged_in': self._handle_user_login_trigger,
            'code_shared': self._handle_code_shared_trigger,
            'code_downloaded': self._handle_code_downloaded_trigger,
            'api_rate_limit_hit': self._handle_rate_limit_trigger,
            'error_occurred': self._handle_error_trigger,
            'high_usage_detected': self._handle_high_usage_trigger
        }
    
    def register_zapier_webhook(self, trigger_type: str, target_url: str, 
                              auth_token: str = None) -> str:
        """
        Register a Zapier webhook for a specific trigger
        
        Args:
            trigger_type: Type of trigger ('kd_code_generated', 'kd_code_scanned', etc.)
            target_url: URL to send webhook notifications to
            auth_token: Optional authentication token for the target
        
        Returns:
            Webhook ID
        """
        if trigger_type not in self.zapier_triggers:
            raise ValueError(f"Invalid trigger type: {trigger_type}")
        
        webhook_id = hashlib.sha256(f"{trigger_type}_{target_url}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        self.zapier_webhooks[webhook_id] = {
            'trigger_type': trigger_type,
            'target_url': target_url,
            'auth_token': auth_token,
            'created_at': datetime.now().isoformat(),
            'enabled': True
        }
        
        self.logger.info(f"Registered Zapier webhook: {webhook_id} for {trigger_type}")
        return webhook_id
    
    def unregister_zapier_webhook(self, webhook_id: str) -> bool:
        """
        Unregister a Zapier webhook
        
        Args:
            webhook_id: ID of the webhook to unregister
        
        Returns:
            True if successful, False otherwise
        """
        if webhook_id in self.zapier_webhooks:
            del self.zapier_webhooks[webhook_id]
            self.logger.info(f"Unregistered Zapier webhook: {webhook_id}")
            return True
        return False
    
    def trigger_zapier_webhook(self, trigger_type: str, payload: Dict[str, Any]):
        """
        Trigger a Zapier webhook for a specific event
        
        Args:
            trigger_type: Type of trigger
            payload: Data to send with the webhook
        """
        # Find all webhooks registered for this trigger type
        matching_webhooks = [
            (wid, config) for wid, config in self.zapier_webhooks.items()
            if config['trigger_type'] == trigger_type and config['enabled']
        ]
        
        for webhook_id, config in matching_webhooks:
            self._send_zapier_webhook(config['target_url'], payload, config.get('auth_token'))
    
    def _send_zapier_webhook(self, target_url: str, payload: Dict[str, Any], auth_token: str = None):
        """
        Send a webhook to Zapier
        
        Args:
            target_url: URL to send the webhook to
            payload: Data to send
            auth_token: Optional authentication token
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'KD-Code System Zapier Integration'
        }
        
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        
        try:
            response = requests.post(
                target_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Zapier webhook sent successfully to {target_url}")
            else:
                self.logger.warning(f"Zapier webhook failed with status {response.status_code}: {response.text}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error sending Zapier webhook to {target_url}: {e}")
    
    def _handle_code_generated_trigger(self, payload: Dict[str, Any]):
        """Handle KD-Code generation trigger"""
        # Add additional metadata for Zapier
        payload['event_type'] = 'kd_code_generated'
        payload['timestamp'] = datetime.now().isoformat()
        
        # Send to registered webhooks
        self.trigger_zapier_webhook('kd_code_generated', payload)
    
    def _handle_code_scanned_trigger(self, payload: Dict[str, Any]):
        """Handle KD-Code scanning trigger"""
        # Add additional metadata for Zapier
        payload['event_type'] = 'kd_code_scanned'
        payload['timestamp'] = datetime.now().isoformat()
        
        # Send to registered webhooks
        self.trigger_zapier_webhook('kd_code_scanned', payload)
    
    def _handle_code_expired_trigger(self, payload: Dict[str, Any]):
        """Handle KD-Code expiration trigger"""
        # Add additional metadata for Zapier
        payload['event_type'] = 'kd_code_expired'
        payload['timestamp'] = datetime.now().isoformat()
        
        # Send to registered webhooks
        self.trigger_zapier_webhook('kd_code_expired', payload)
    
    def _handle_batch_completed_trigger(self, payload: Dict[str, Any]):
        """Handle batch operation completion trigger"""
        # Add additional metadata for Zapier
        payload['event_type'] = 'batch_operation_completed'
        payload['timestamp'] = datetime.now().isoformat()
        
        # Send to registered webhooks
        self.trigger_zapier_webhook('batch_operation_completed', payload)
    
    def _handle_user_login_trigger(self, payload: Dict[str, Any]):
        """Handle user login trigger"""
        payload['event_type'] = 'user_logged_in'
        payload['timestamp'] = datetime.now().isoformat()
        
        self.trigger_zapier_webhook('user_logged_in', payload)
    
    def _handle_code_shared_trigger(self, payload: Dict[str, Any]):
        """Handle code sharing trigger"""
        payload['event_type'] = 'code_shared'
        payload['timestamp'] = datetime.now().isoformat()
        
        self.trigger_zapier_webhook('code_shared', payload)
    
    def _handle_code_downloaded_trigger(self, payload: Dict[str, Any]):
        """Handle code download trigger"""
        payload['event_type'] = 'code_downloaded'
        payload['timestamp'] = datetime.now().isoformat()
        
        self.trigger_zapier_webhook('code_downloaded', payload)
    
    def _handle_rate_limit_trigger(self, payload: Dict[str, Any]):
        """Handle API rate limit trigger"""
        payload['event_type'] = 'api_rate_limit_hit'
        payload['timestamp'] = datetime.now().isoformat()
        
        self.trigger_zapier_webhook('api_rate_limit_hit', payload)
    
    def _handle_error_trigger(self, payload: Dict[str, Any]):
        """Handle error occurrence trigger"""
        payload['event_type'] = 'error_occurred'
        payload['timestamp'] = datetime.now().isoformat()
        
        self.trigger_zapier_webhook('error_occurred', payload)
    
    def _handle_high_usage_trigger(self, payload: Dict[str, Any]):
        """Handle high usage detection trigger"""
        payload['event_type'] = 'high_usage_detected'
        payload['timestamp'] = datetime.now().isoformat()
        
        self.trigger_zapier_webhook('high_usage_detected', payload)


# Global Zapier integration instance
zapier_integration = ZapierIntegration()


def initialize_zapier_integration():
    """Initialize the Zapier integration system"""
    global zapier_integration
    zapier_integration = ZapierIntegration()


def register_zapier_hook(trigger_type: str, target_url: str, auth_token: str = None) -> str:
    """
    Register a Zapier webhook for a specific trigger
    
    Args:
        trigger_type: Type of trigger
        target_url: URL to send webhook notifications to
        auth_token: Optional authentication token
    
    Returns:
        Webhook ID
    """
    return zapier_integration.register_zapier_webhook(trigger_type, target_url, auth_token)


def unregister_zapier_hook(webhook_id: str) -> bool:
    """
    Unregister a Zapier webhook
    
    Args:
        webhook_id: ID of the webhook to unregister
    
    Returns:
        True if successful, False otherwise
    """
    return zapier_integration.unregister_zapier_webhook(webhook_id)


def trigger_zapier_hook(trigger_type: str, data: Dict[str, Any]):
    """
    Manually trigger a Zapier webhook
    
    Args:
        trigger_type: Type of trigger
        data: Data to send with the webhook
    """
    zapier_integration.trigger_zapier_webhook(trigger_type, data)


def notify_code_generated_zapier(code_id: str, content: str, user_id: str = None):
    """
    Notify Zapier when a KD-Code is generated
    
    Args:
        code_id: ID of the generated code
        content: Content of the generated code
        user_id: ID of the user who generated it (optional)
    """
    payload = {
        'code_id': code_id,
        'content': content,
        'user_id': user_id,
        'action': 'generate'
    }
    zapier_integration.trigger_zapier_webhook('kd_code_generated', payload)


def notify_code_scanned_zapier(code_id: str, decoded_text: str, scanner_ip: str = None, 
                            success: bool = True):
    """
    Notify Zapier when a KD-Code is scanned
    
    Args:
        code_id: ID of the scanned code
        decoded_text: Text decoded from the code
        scanner_ip: IP address of the scanner (optional)
        success: Whether the scan was successful
    """
    payload = {
        'code_id': code_id,
        'decoded_text': decoded_text,
        'scanner_ip': scanner_ip,
        'success': success,
        'action': 'scan'
    }
    zapier_integration.trigger_zapier_webhook('kd_code_scanned', payload)


def notify_code_expired_zapier(code_id: str, content: str):
    """
    Notify Zapier when a KD-Code expires
    
    Args:
        code_id: ID of the expired code
        content: Content of the expired code
    """
    payload = {
        'code_id': code_id,
        'content': content,
        'action': 'expire'
    }
    zapier_integration.trigger_zapier_webhook('kd_code_expired', payload)


def notify_batch_completed_zapier(batch_id: str, results_count: int, success_count: int):
    """
    Notify Zapier when a batch operation completes
    
    Args:
        batch_id: ID of the batch operation
        results_count: Total number of results
        success_count: Number of successful operations
    """
    payload = {
        'batch_id': batch_id,
        'results_count': results_count,
        'success_count': success_count,
        'action': 'batch_complete'
    }
    zapier_integration.trigger_zapier_webhook('batch_operation_completed', payload)


def notify_user_login_zapier(user_id: str, username: str = None, ip_address: str = None):
    """
    Notify Zapier when a user logs in
    
    Args:
        user_id: ID of the logged-in user
        username: Username of the user (optional)
        ip_address: IP address of the login (optional)
    """
    payload = {
        'user_id': user_id,
        'username': username,
        'ip_address': ip_address,
        'action': 'user_login'
    }
    zapier_integration.trigger_zapier_webhook('user_logged_in', payload)


def notify_code_shared_zapier(code_id: str, sharer_id: str, recipient_info: Dict[str, str] = None):
    """
    Notify Zapier when a code is shared
    
    Args:
        code_id: ID of the shared code
        sharer_id: ID of the user sharing the code
        recipient_info: Information about the recipient (optional)
    """
    payload = {
        'code_id': code_id,
        'sharer_id': sharer_id,
        'recipient_info': recipient_info,
        'action': 'code_shared'
    }
    zapier_integration.trigger_zapier_webhook('code_shared', payload)


def notify_code_downloaded_zapier(code_id: str, downloader_id: str, download_type: str = 'image'):
    """
    Notify Zapier when a code is downloaded
    
    Args:
        code_id: ID of the downloaded code
        downloader_id: ID of the user downloading the code
        download_type: Type of download ('image', 'svg', 'pdf', etc.)
    """
    payload = {
        'code_id': code_id,
        'downloader_id': downloader_id,
        'download_type': download_type,
        'action': 'code_downloaded'
    }
    zapier_integration.trigger_zapier_webhook('code_downloaded', payload)


def notify_rate_limit_hit_zapier(user_id: str, endpoint: str, limit_type: str = 'request'):
    """
    Notify Zapier when an API rate limit is hit
    
    Args:
        user_id: ID of the user hitting the limit
        endpoint: API endpoint that was rate limited
        limit_type: Type of limit ('request', 'bandwidth', 'generation', etc.)
    """
    payload = {
        'user_id': user_id,
        'endpoint': endpoint,
        'limit_type': limit_type,
        'action': 'rate_limit_hit',
        'timestamp': datetime.now().isoformat()
    }
    zapier_integration.trigger_zapier_webhook('api_rate_limit_hit', payload)


def notify_error_occurred_zapier(error_type: str, error_message: str, context: Dict[str, any] = None):
    """
    Notify Zapier when an error occurs
    
    Args:
        error_type: Type of error that occurred
        error_message: Error message
        context: Additional context about the error (optional)
    """
    payload = {
        'error_type': error_type,
        'error_message': error_message,
        'context': context or {},
        'action': 'error_occurred',
        'timestamp': datetime.now().isoformat()
    }
    zapier_integration.trigger_zapier_webhook('error_occurred', payload)


def notify_high_usage_detected_zapier(metric_type: str, current_value: float, threshold: float, 
                                   user_id: str = None):
    """
    Notify Zapier when high usage is detected
    
    Args:
        metric_type: Type of metric ('generation_count', 'scan_count', 'storage', etc.)
        current_value: Current value of the metric
        threshold: Threshold that was exceeded
        user_id: ID of the user if applicable (optional)
    """
    payload = {
        'metric_type': metric_type,
        'current_value': current_value,
        'threshold': threshold,
        'user_id': user_id,
        'action': 'high_usage_detected',
        'timestamp': datetime.now().isoformat()
    }
    zapier_integration.trigger_zapier_webhook('high_usage_detected', payload)


# Flask routes for Zapier integration
def add_zapier_routes(app: Flask):
    """
    Add Zapier integration routes to a Flask app
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/zapier/register', methods=['POST'])
    def register_zapier_webhook():
        """Register a new Zapier webhook"""
        try:
            data = request.get_json()
            
            if not data or 'trigger_type' not in data or 'target_url' not in data:
                return jsonify({'error': 'trigger_type and target_url are required'}), 400
            
            trigger_type = data['trigger_type']
            target_url = data['target_url']
            auth_token = data.get('auth_token')
            
            webhook_id = register_zapier_hook(trigger_type, target_url, auth_token)
            
            return jsonify({
                'status': 'success',
                'webhook_id': webhook_id
            })
        except Exception as e:
            app.logger.error(f"Error in register_zapier_webhook: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/zapier/unregister/<webhook_id>', methods=['DELETE'])
    def unregister_zapier_webhook(webhook_id: str):
        """Unregister a Zapier webhook"""
        try:
            success = unregister_zapier_hook(webhook_id)
            
            if not success:
                return jsonify({'error': 'Webhook not found'}), 404
            
            return jsonify({'status': 'success'})
        except Exception as e:
            app.logger.error(f"Error in unregister_zapier_webhook: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/zapier/test', methods=['POST'])
    def test_zapier_webhook():
        """Test endpoint to verify Zapier integration"""
        try:
            data = request.get_json()
            
            # Send test payload to registered webhooks
            test_payload = {
                'test': True,
                'timestamp': datetime.now().isoformat(),
                'message': 'This is a test message from KD-Code Zapier integration'
            }
            
            # If a specific trigger is provided, test that trigger
            trigger_type = data.get('trigger_type', 'kd_code_generated')
            zapier_integration.trigger_zapier_webhook(trigger_type, test_payload)
            
            return jsonify({
                'status': 'success',
                'message': f'Test webhook sent for trigger: {trigger_type}'
            })
        except Exception as e:
            app.logger.error(f"Error in test_zapier_webhook: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/zapier/triggers', methods=['GET'])
    def get_zapier_triggers():
        """Get available Zapier triggers"""
        triggers = list(zapier_integration.zapier_triggers.keys())
        
        return jsonify({
            'status': 'success',
            'triggers': triggers
        })


# Example usage
if __name__ == "__main__":
    # Initialize Zapier integration
    initialize_zapier_integration()
    
    print("Available Zapier triggers:")
    for trigger in zapier_integration.zapier_triggers:
        print(f"  - {trigger}")
    
    # Example of registering a webhook
    webhook_id = register_zapier_hook(
        'kd_code_generated',
        'https://hooks.zapier.com/hooks/catch/123456/abcde',
        auth_token='your_auth_token'
    )
    
    print(f"Registered webhook with ID: {webhook_id}")
    
    # Example of triggering a webhook
    notify_code_generated_zapier(
        code_id='test_code_123',
        content='Hello, Zapier!',
        user_id='user_456'
    )
    
    print("Zapier integration initialized and tested successfully!")