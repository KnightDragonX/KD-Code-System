"""
IFTTT Integration Module for KD-Code System
Enables integration with IFTTT for smart home automation
"""

import requests
import json
from typing import Dict, Any, Optional
import logging
from datetime import datetime


class IFTTTIntegration:
    """
    Integration system for connecting KD-Code system with IFTTT
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the IFTTT integration
        
        Args:
            api_key: IFTTT Webhook API key
        """
        self.api_key = api_key
        self.webhook_base_url = "https://maker.ifttt.com/trigger"
        self.logger = logging.getLogger(__name__)
    
    def set_api_key(self, api_key: str):
        """
        Set the IFTTT API key
        
        Args:
            api_key: IFTTT Webhook API key
        """
        self.api_key = api_key
    
    def trigger_webhook(self, event_name: str, value1: str = None, 
                       value2: str = None, value3: str = None) -> bool:
        """
        Trigger an IFTTT webhook
        
        Args:
            event_name: Name of the IFTTT event
            value1: First value to send (optional)
            value2: Second value to send (optional)
            value3: Third value to send (optional)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.api_key:
            self.logger.error("IFTTT API key not set")
            return False
        
        try:
            # Construct the webhook URL
            webhook_url = f"{self.webhook_base_url}/{event_name}/with/key/{self.api_key}"
            
            # Prepare payload
            payload = {}
            if value1 is not None:
                payload['value1'] = value1
            if value2 is not None:
                payload['value2'] = value2
            if value3 is not None:
                payload['value3'] = value3
            
            # Add timestamp
            payload['timestamp'] = datetime.now().isoformat()
            
            # Make the request
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code == 200:
                self.logger.info(f"IFTTT webhook '{event_name}' triggered successfully")
                return True
            else:
                self.logger.error(f"IFTTT webhook failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Error triggering IFTTT webhook: {e}")
            return False
    
    def trigger_kd_code_generated(self, code_id: str, content: str, user_id: str = None) -> bool:
        """
        Trigger IFTTT event when a KD-Code is generated
        
        Args:
            code_id: ID of the generated code
            content: Content of the generated code
            user_id: ID of the user who generated it (optional)
        
        Returns:
            True if successful, False otherwise
        """
        event_name = "kd_code_generated"
        value1 = f"KD-Code generated: {content[:50]}{'...' if len(content) > 50 else ''}"
        value2 = code_id
        value3 = user_id or "unknown"
        
        return self.trigger_webhook(event_name, value1, value2, value3)
    
    def trigger_kd_code_scanned(self, code_id: str, decoded_text: str, 
                               scanner_device: str = None) -> bool:
        """
        Trigger IFTTT event when a KD-Code is scanned
        
        Args:
            code_id: ID of the scanned code
            decoded_text: Text decoded from the code
            scanner_device: Device that performed the scan (optional)
        
        Returns:
            True if successful, False otherwise
        """
        event_name = "kd_code_scanned"
        value1 = f"KD-Code scanned: {decoded_text[:50]}{'...' if len(decoded_text) > 50 else ''}"
        value2 = code_id
        value3 = scanner_device or "unknown_device"
        
        return self.trigger_webhook(event_name, value1, value2, value3)
    
    def trigger_kd_code_shared(self, code_id: str, sharer_id: str, 
                              recipient_info: str = None) -> bool:
        """
        Trigger IFTTT event when a KD-Code is shared
        
        Args:
            code_id: ID of the shared code
            sharer_id: ID of the user who shared it
            recipient_info: Information about the recipient (optional)
        
        Returns:
            True if successful, False otherwise
        """
        event_name = "kd_code_shared"
        value1 = f"KD-Code shared: {code_id}"
        value2 = sharer_id
        value3 = recipient_info or "unknown_recipient"
        
        return self.trigger_webhook(event_name, value1, value2, value3)
    
    def trigger_batch_operation_completed(self, batch_id: str, 
                                         success_count: int, total_count: int) -> bool:
        """
        Trigger IFTTT event when a batch operation completes
        
        Args:
            batch_id: ID of the batch operation
            success_count: Number of successful operations
            total_count: Total number of operations
        
        Returns:
            True if successful, False otherwise
        """
        event_name = "batch_operation_completed"
        value1 = f"Batch operation completed: {batch_id}"
        value2 = f"Success: {success_count}/{total_count}"
        value3 = f"Success rate: {(success_count/total_count)*100:.2f}%" if total_count > 0 else "0%"
        
        return self.trigger_webhook(event_name, value1, value2, value3)
    
    def trigger_high_usage_alert(self, metric_type: str, current_value: float, 
                                threshold: float) -> bool:
        """
        Trigger IFTTT event when high usage is detected
        
        Args:
            metric_type: Type of metric ('generation_count', 'scan_count', etc.)
            current_value: Current value of the metric
            threshold: Threshold that was exceeded
        
        Returns:
            True if successful, False otherwise
        """
        event_name = "high_usage_alert"
        value1 = f"High usage detected: {metric_type}"
        value2 = f"Current value: {current_value}"
        value3 = f"Threshold: {threshold}"
        
        return self.trigger_webhook(event_name, value1, value2, value3)
    
    def trigger_error_alert(self, error_type: str, error_message: str, 
                           context: str = None) -> bool:
        """
        Trigger IFTTT event when an error occurs
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context (optional)
        
        Returns:
            True if successful, False otherwise
        """
        event_name = "error_occurred"
        value1 = f"Error: {error_type}"
        value2 = error_message
        value3 = context or "No additional context"
        
        return self.trigger_webhook(event_name, value1, value2, value3)
    
    def setup_smart_home_automation(self) -> Dict[str, str]:
        """
        Provide instructions for setting up smart home automation with IFTTT
        
        Returns:
            Dictionary with setup instructions
        """
        return {
            'webhook_url': f"{self.webhook_base_url}/[EVENT_NAME]/with/key/[YOUR_KEY]",
            'supported_events': [
                'kd_code_generated',
                'kd_code_scanned', 
                'kd_code_shared',
                'batch_operation_completed',
                'high_usage_alert',
                'error_occurred'
            ],
            'setup_instructions': """
            1. Go to https://ifttt.com/maker_webhooks
            2. Get your unique webhook key
            3. Create applets that respond to the events:
               - kd_code_generated: Turn on lights when code is created
               - kd_code_scanned: Unlock door when code is scanned
               - kd_code_shared: Send notification when code is shared
               - batch_operation_completed: Send summary when batch completes
               - high_usage_alert: Adjust smart thermostat on high usage
               - error_occurred: Flash lights when error occurs
            4. Use the values (value1, value2, value3) in your applets
            """,
            'example_usage': {
                'event': 'kd_code_scanned',
                'value1': 'KD-Code scanned: Welcome home!',
                'value2': 'code_12345',
                'value3': 'mobile_app'
            }
        }


# Global IFTTT integration instance
ifttt_integration = IFTTTIntegration()


def initialize_ifttt_integration(api_key: str = None):
    """
    Initialize the IFTTT integration
    
    Args:
        api_key: IFTTT Webhook API key
    """
    global ifttt_integration
    ifttt_integration = IFTTTIntegration(api_key)


def set_ifttt_api_key(api_key: str):
    """
    Set the IFTTT API key
    
    Args:
        api_key: IFTTT Webhook API key
    """
    ifttt_integration.set_api_key(api_key)


def trigger_ifttt_kd_code_generated(code_id: str, content: str, user_id: str = None) -> bool:
    """
    Trigger IFTTT event when a KD-Code is generated
    
    Args:
        code_id: ID of the generated code
        content: Content of the generated code
        user_id: ID of the user who generated it (optional)
    
    Returns:
        True if successful, False otherwise
    """
    return ifttt_integration.trigger_kd_code_generated(code_id, content, user_id)


def trigger_ifttt_kd_code_scanned(code_id: str, decoded_text: str, 
                                scanner_device: str = None) -> bool:
    """
    Trigger IFTTT event when a KD-Code is scanned
    
    Args:
        code_id: ID of the scanned code
        decoded_text: Text decoded from the code
        scanner_device: Device that performed the scan (optional)
    
    Returns:
        True if successful, False otherwise
    """
    return ifttt_integration.trigger_kd_code_scanned(code_id, decoded_text, scanner_device)


def trigger_ifttt_kd_code_shared(code_id: str, sharer_id: str, 
                               recipient_info: str = None) -> bool:
    """
    Trigger IFTTT event when a KD-Code is shared
    
    Args:
        code_id: ID of the shared code
        sharer_id: ID of the user who shared it
        recipient_info: Information about the recipient (optional)
    
    Returns:
        True if successful, False otherwise
    """
    return ifttt_integration.trigger_kd_code_shared(code_id, sharer_id, recipient_info)


def trigger_ifttt_batch_completed(batch_id: str, success_count: int, total_count: int) -> bool:
    """
    Trigger IFTTT event when a batch operation completes
    
    Args:
        batch_id: ID of the batch operation
        success_count: Number of successful operations
        total_count: Total number of operations
    
    Returns:
        True if successful, False otherwise
    """
    return ifttt_integration.trigger_batch_operation_completed(batch_id, success_count, total_count)


def trigger_ifttt_high_usage(metric_type: str, current_value: float, threshold: float) -> bool:
    """
    Trigger IFTTT event when high usage is detected
    
    Args:
        metric_type: Type of metric ('generation_count', 'scan_count', etc.)
        current_value: Current value of the metric
        threshold: Threshold that was exceeded
    
    Returns:
        True if successful, False otherwise
    """
    return ifttt_integration.trigger_high_usage_alert(metric_type, current_value, threshold)


def trigger_ifttt_error(error_type: str, error_message: str, context: str = None) -> bool:
    """
    Trigger IFTTT event when an error occurs
    
    Args:
        error_type: Type of error
        error_message: Error message
        context: Additional context (optional)
    
    Returns:
        True if successful, False otherwise
    """
    return ifttt_integration.trigger_error_alert(error_type, error_message, context)


def get_ifttt_setup_guide() -> Dict[str, str]:
    """
    Get setup guide for IFTTT integration
    
    Returns:
        Dictionary with setup instructions
    """
    return ifttt_integration.setup_smart_home_automation()


# Example usage
if __name__ == "__main__":
    print("IFTTT Integration for KD-Code System")
    print("This module enables integration with IFTTT for smart home automation")
    
    # Example of how to use the integration:
    # 1. Initialize with your IFTTT webhook key
    # initialize_ifttt_integration("your_ifttt_webhook_key")
    # 
    # 2. Trigger events when KD-Codes are generated/scanned
    # success = trigger_ifttt_kd_code_generated("code_123", "Welcome Home", "user_456")
    # print(f"IFTTT trigger successful: {success}")
    # 
    # 3. Get setup instructions
    # setup_guide = get_ifttt_setup_guide()
    # print(f"Setup instructions: {setup_guide['setup_instructions']}")
    
    print("Module ready for IFTTT integration")