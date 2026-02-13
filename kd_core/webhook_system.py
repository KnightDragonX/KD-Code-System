"""
Webhook System for KD-Code Notifications
Implements real-time webhook notifications for KD-Code events
"""

import requests
import json
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sqlite3
import threading
import queue
from flask import Flask, request, jsonify
import logging
from enum import Enum


class WebhookEventType(Enum):
    """Types of events that can trigger webhooks"""
    CODE_GENERATED = "code.generated"
    CODE_SCANNED = "code.scanned"
    CODE_EXPIRED = "code.expired"
    CODE_REVOKED = "code.revoked"
    BATCH_COMPLETED = "batch.completed"
    ERROR_OCCURRED = "error.occurred"


class WebhookManager:
    """
    Manages webhook subscriptions and notifications for KD-Code events
    """
    
    def __init__(self, db_path: str = "kd_codes_webhooks.db"):
        """
        Initialize the webhook manager
        
        Args:
            db_path: Path to the database for storing webhook subscriptions
        """
        self.db_path = db_path
        self.webhook_queue = queue.Queue()
        self.is_running = False
        self.worker_thread = None
        self.logger = logging.getLogger(__name__)
        
        self.init_database()
        self.start_worker()
    
    def init_database(self):
        """Initialize the database with webhook subscription tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create webhook subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhook_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                target_url TEXT NOT NULL,
                secret TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_triggered TIMESTAMP,
                failure_count INTEGER DEFAULT 0,
                consecutive_failures INTEGER DEFAULT 0
            )
        ''')
        
        # Create webhook logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhook_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                event_type TEXT NOT NULL,
                payload TEXT,
                response_status INTEGER,
                response_body TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                FOREIGN KEY (subscription_id) REFERENCES webhook_subscriptions (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def subscribe(self, event_type: WebhookEventType, target_url: str, 
                  secret: str = None) -> Optional[int]:
        """
        Subscribe to a webhook event
        
        Args:
            event_type: Type of event to subscribe to
            target_url: URL to send webhook notifications to
            secret: Secret for signing webhook payloads (optional)
        
        Returns:
            Subscription ID or None if failed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO webhook_subscriptions (event_type, target_url, secret)
                VALUES (?, ?, ?)
            ''', (event_type.value, target_url, secret))
            
            subscription_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"New webhook subscription created: ID {subscription_id}, Event {event_type.value}, URL {target_url}")
            return subscription_id
        except Exception as e:
            self.logger.error(f"Error creating webhook subscription: {e}")
            conn.close()
            return None
    
    def unsubscribe(self, subscription_id: int) -> bool:
        """
        Unsubscribe from a webhook event
        
        Args:
            subscription_id: ID of the subscription to remove
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE webhook_subscriptions
                SET is_active = 0
                WHERE id = ?
            ''', (subscription_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                self.logger.info(f"Webhook subscription {subscription_id} deactivated")
            else:
                self.logger.warning(f"Webhook subscription {subscription_id} not found")
            
            return success
        except Exception as e:
            self.logger.error(f"Error deactivating webhook subscription: {e}")
            conn.close()
            return False
    
    def trigger_webhook(self, event_type: WebhookEventType, payload: Dict[str, Any]):
        """
        Trigger a webhook for a specific event
        
        Args:
            event_type: Type of event that occurred
            payload: Data to send with the webhook
        """
        # Add event metadata
        enriched_payload = {
            'event_type': event_type.value,
            'timestamp': datetime.now().isoformat(),
            'payload': payload
        }
        
        # Queue the webhook for asynchronous processing
        self.webhook_queue.put({
            'event_type': event_type.value,
            'payload': enriched_payload
        })
    
    def process_webhook_queue(self):
        """Process webhooks in the queue asynchronously"""
        while self.is_running:
            try:
                # Get a webhook from the queue (with timeout)
                webhook_data = self.webhook_queue.get(timeout=1)
                
                if webhook_data is None:
                    continue
                
                self._send_webhook_notifications(webhook_data['event_type'], webhook_data['payload'])
                self.webhook_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing webhook queue: {e}")
    
    def _send_webhook_notifications(self, event_type: str, payload: Dict[str, Any]):
        """
        Send webhook notifications to all subscribers of an event type
        
        Args:
            event_type: Type of event
            payload: Payload to send
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all active subscriptions for this event type
        cursor.execute('''
            SELECT id, target_url, secret
            FROM webhook_subscriptions
            WHERE event_type = ? AND is_active = 1
        ''', (event_type,))
        
        subscriptions = cursor.fetchall()
        conn.close()
        
        # Send webhook to each subscriber
        for sub_id, target_url, secret in subscriptions:
            self._send_single_webhook(sub_id, target_url, secret, payload)
    
    def _send_single_webhook(self, subscription_id: int, target_url: str, 
                           secret: str, payload: Dict[str, Any]):
        """
        Send a single webhook notification
        
        Args:
            subscription_id: ID of the subscription
            target_url: URL to send the webhook to
            secret: Secret for signing the payload
            payload: Payload to send
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'KD-Code-System Webhook Service'
        }
        
        # Add signature if secret is provided
        if secret:
            signature = self._create_signature(payload, secret)
            headers['X-KDCode-Signature'] = signature
        
        try:
            response = requests.post(
                target_url,
                json=payload,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            # Log the result
            self._log_webhook_result(subscription_id, payload, response.status_code, 
                                   response.text, response.ok)
            
            if not response.ok:
                self.logger.warning(f"Webhook to {target_url} failed with status {response.status_code}")
                self._increment_failure_count(subscription_id)
            else:
                self.logger.info(f"Webhook successfully sent to {target_url}")
                self._reset_failure_count(subscription_id)
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Webhook request failed: {e}")
            self._log_webhook_result(subscription_id, payload, 0, str(e), False)
            self._increment_failure_count(subscription_id)
        except Exception as e:
            self.logger.error(f"Unexpected error sending webhook: {e}")
            self._log_webhook_result(subscription_id, payload, 0, str(e), False)
            self._increment_failure_count(subscription_id)
    
    def _create_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Create a signature for webhook payload verification
        
        Args:
            payload: Payload to sign
            secret: Secret key for signing
        
        Returns:
            Signature string
        """
        payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def _log_webhook_result(self, subscription_id: int, payload: Dict[str, Any], 
                          status_code: int, response_body: str, success: bool):
        """
        Log the result of a webhook attempt
        
        Args:
            subscription_id: ID of the subscription
            payload: Payload that was sent
            status_code: HTTP status code received
            response_body: Response body received
            success: Whether the request was successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO webhook_logs 
                (subscription_id, event_type, payload, response_status, response_body, success)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                subscription_id,
                payload.get('event_type', 'unknown'),
                json.dumps(payload),
                status_code,
                response_body,
                success
            ))
            
            # Update the last triggered timestamp
            cursor.execute('''
                UPDATE webhook_subscriptions
                SET last_triggered = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (subscription_id,))
            
            conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging webhook result: {e}")
        finally:
            conn.close()
    
    def _increment_failure_count(self, subscription_id: int):
        """
        Increment the failure count for a subscription
        
        Args:
            subscription_id: ID of the subscription
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current failure counts
            cursor.execute('''
                SELECT failure_count, consecutive_failures
                FROM webhook_subscriptions
                WHERE id = ?
            ''', (subscription_id,))
            
            row = cursor.fetchone()
            if row:
                total_failures, consecutive_failures = row
                new_total = total_failures + 1
                new_consecutive = consecutive_failures + 1
                
                # Deactivate subscription if too many consecutive failures
                if new_consecutive >= 5:  # 5 consecutive failures
                    cursor.execute('''
                        UPDATE webhook_subscriptions
                        SET is_active = 0, consecutive_failures = ?
                        WHERE id = ?
                    ''', (new_consecutive, subscription_id))
                    self.logger.warning(f"Webhook subscription {subscription_id} deactivated due to consecutive failures")
                else:
                    cursor.execute('''
                        UPDATE webhook_subscriptions
                        SET failure_count = ?, consecutive_failures = ?
                        WHERE id = ?
                    ''', (new_total, new_consecutive, subscription_id))
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error incrementing failure count: {e}")
        finally:
            conn.close()
    
    def _reset_failure_count(self, subscription_id: int):
        """
        Reset the consecutive failure count for a subscription
        
        Args:
            subscription_id: ID of the subscription
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE webhook_subscriptions
                SET consecutive_failures = 0
                WHERE id = ?
            ''', (subscription_id,))
            
            conn.commit()
        except Exception as e:
            self.logger.error(f"Error resetting failure count: {e}")
        finally:
            conn.close()
    
    def start_worker(self):
        """Start the webhook processing worker thread"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self.process_webhook_queue, daemon=True)
            self.worker_thread.start()
            self.logger.info("Webhook worker thread started")
    
    def stop_worker(self):
        """Stop the webhook processing worker thread"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)  # Wait up to 5 seconds for graceful shutdown
            self.logger.info("Webhook worker thread stopped")
    
    def get_subscription_stats(self, subscription_id: int) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific subscription
        
        Args:
            subscription_id: ID of the subscription
        
        Returns:
            Subscription statistics or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ws.event_type, ws.target_url, ws.is_active, ws.created_at, 
                   ws.last_triggered, ws.failure_count, ws.consecutive_failures,
                   COUNT(wl.id) as total_attempts,
                   SUM(CASE WHEN wl.success THEN 1 ELSE 0 END) as successful_attempts
            FROM webhook_subscriptions ws
            LEFT JOIN webhook_logs wl ON ws.id = wl.subscription_id
            WHERE ws.id = ?
            GROUP BY ws.id
        ''', (subscription_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'event_type': row[0],
            'target_url': row[1],
            'is_active': bool(row[2]),
            'created_at': row[3],
            'last_triggered': row[4],
            'failure_count': row[5],
            'consecutive_failures': row[6],
            'total_attempts': row[7],
            'successful_attempts': row[8],
            'success_rate': row[8] / row[7] if row[7] > 0 else 0
        }
    
    def get_recent_logs(self, subscription_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent logs for a subscription
        
        Args:
            subscription_id: ID of the subscription
            limit: Number of logs to return
        
        Returns:
            List of recent webhook logs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_type, payload, response_status, response_body, 
                   timestamp, success
            FROM webhook_logs
            WHERE subscription_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (subscription_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for event_type, payload, status, response, timestamp, success in rows:
            logs.append({
                'event_type': event_type,
                'payload': json.loads(payload) if payload else {},
                'response_status': status,
                'response_body': response,
                'timestamp': timestamp,
                'success': bool(success)
            })
        
        return logs


# Global webhook manager instance
webhook_manager = WebhookManager()


def initialize_webhook_system():
    """Initialize the webhook system"""
    global webhook_manager
    webhook_manager = WebhookManager()


def subscribe_to_webhook(event_type: WebhookEventType, target_url: str, secret: str = None) -> Optional[int]:
    """
    Subscribe to webhook notifications for a specific event
    
    Args:
        event_type: Type of event to subscribe to
        target_url: URL to receive webhook notifications
        secret: Secret for payload signing (optional)
    
    Returns:
        Subscription ID or None if failed
    """
    return webhook_manager.subscribe(event_type, target_url, secret)


def unsubscribe_from_webhook(subscription_id: int) -> bool:
    """
    Unsubscribe from webhook notifications
    
    Args:
        subscription_id: ID of the subscription to remove
    
    Returns:
        True if successful, False otherwise
    """
    return webhook_manager.unsubscribe(subscription_id)


def trigger_webhook_notification(event_type: WebhookEventType, payload: Dict[str, Any]):
    """
    Trigger a webhook notification for an event
    
    Args:
        event_type: Type of event that occurred
        payload: Data to send with the webhook
    """
    webhook_manager.trigger_webhook(event_type, payload)


def get_webhook_subscription_stats(subscription_id: int) -> Optional[Dict[str, Any]]:
    """
    Get statistics for a webhook subscription
    
    Args:
        subscription_id: ID of the subscription
    
    Returns:
        Subscription statistics or None if not found
    """
    return webhook_manager.get_subscription_stats(subscription_id)


def get_webhook_logs(subscription_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent logs for a webhook subscription
    
    Args:
        subscription_id: ID of the subscription
        limit: Number of logs to return
    
    Returns:
        List of webhook logs
    """
    return webhook_manager.get_recent_logs(subscription_id, limit)


# Example usage and integration points
def notify_code_generated(code_id: str, content: str, user_id: str = None):
    """Notify when a KD-Code is generated"""
    payload = {
        'code_id': code_id,
        'content': content,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }
    trigger_webhook_notification(WebhookEventType.CODE_GENERATED, payload)


def notify_code_scanned(code_id: str, decoded_text: str, scanner_ip: str = None, 
                       user_agent: str = None, success: bool = True):
    """Notify when a KD-Code is scanned"""
    payload = {
        'code_id': code_id,
        'decoded_text': decoded_text,
        'scanner_ip': scanner_ip,
        'user_agent': user_agent,
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    trigger_webhook_notification(WebhookEventType.CODE_SCANNED, payload)


def notify_batch_completed(batch_id: str, results_count: int, success_count: int):
    """Notify when a batch operation is completed"""
    payload = {
        'batch_id': batch_id,
        'results_count': results_count,
        'success_count': success_count,
        'timestamp': datetime.now().isoformat()
    }
    trigger_webhook_notification(WebhookEventType.BATCH_COMPLETED, payload)


def notify_error_occurred(error_type: str, error_message: str, context: Dict[str, Any] = None):
    """Notify when an error occurs in the system"""
    payload = {
        'error_type': error_type,
        'error_message': error_message,
        'context': context or {},
        'timestamp': datetime.now().isoformat()
    }
    trigger_webhook_notification(WebhookEventType.ERROR_OCCURRED, payload)


# Flask route for webhook management
def add_webhook_routes(app: Flask):
    """
    Add webhook management routes to a Flask app
    
    Args:
        app: Flask application instance
    """
    @app.route('/webhooks/subscribe', methods=['POST'])
    def webhook_subscribe():
        """Subscribe to webhook notifications"""
        try:
            data = request.get_json()
            
            if not data or 'event_type' not in data or 'target_url' not in data:
                return jsonify({'error': 'event_type and target_url are required'}), 400
            
            event_type_str = data['event_type']
            target_url = data['target_url']
            secret = data.get('secret')
            
            # Validate event type
            try:
                event_type = WebhookEventType(event_type_str)
            except ValueError:
                return jsonify({'error': 'Invalid event type'}), 400
            
            subscription_id = subscribe_to_webhook(event_type, target_url, secret)
            
            if subscription_id is None:
                return jsonify({'error': 'Failed to create subscription'}), 500
            
            return jsonify({
                'status': 'success',
                'subscription_id': subscription_id
            })
        except Exception as e:
            app.logger.error(f"Error in webhook_subscribe: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/webhooks/unsubscribe/<int:subscription_id>', methods=['DELETE'])
    def webhook_unsubscribe(subscription_id: int):
        """Unsubscribe from webhook notifications"""
        try:
            success = unsubscribe_from_webhook(subscription_id)
            
            if not success:
                return jsonify({'error': 'Subscription not found'}), 404
            
            return jsonify({'status': 'success'})
        except Exception as e:
            app.logger.error(f"Error in webhook_unsubscribe: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/webhooks/stats/<int:subscription_id>', methods=['GET'])
    def webhook_stats(subscription_id: int):
        """Get statistics for a webhook subscription"""
        try:
            stats = get_webhook_subscription_stats(subscription_id)
            
            if not stats:
                return jsonify({'error': 'Subscription not found'}), 404
            
            return jsonify({
                'status': 'success',
                'stats': stats
            })
        except Exception as e:
            app.logger.error(f"Error in webhook_stats: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    
    @app.route('/webhooks/logs/<int:subscription_id>', methods=['GET'])
    def webhook_logs(subscription_id: int):
        """Get recent logs for a webhook subscription"""
        try:
            limit = int(request.args.get('limit', 10))
            logs = get_webhook_logs(subscription_id, limit)
            
            return jsonify({
                'status': 'success',
                'logs': logs
            })
        except Exception as e:
            app.logger.error(f"Error in webhook_logs: {e}")
            return jsonify({'error': 'Internal server error'}), 500


# Example usage
if __name__ == "__main__":
    # Initialize the webhook system
    initialize_webhook_system()
    
    # Example of subscribing to events
    sub_id = subscribe_to_webhook(
        WebhookEventType.CODE_GENERATED,
        "https://example.com/webhook/kdcode-generated",
        secret="my_secret_key"
    )
    
    if sub_id:
        print(f"Subscribed to CODE_GENERATED events with ID: {sub_id}")
        
        # Example of triggering a notification
        notify_code_generated("test_code_123", "Hello, Webhook!", "user_456")
        
        # Get subscription stats
        stats = get_webhook_subscription_stats(sub_id)
        print(f"Subscription stats: {stats}")
        
        # Get recent logs
        logs = get_webhook_logs(sub_id)
        print(f"Recent logs: {len(logs)} entries")
    else:
        print("Failed to subscribe to webhook")
    
    # Clean up
    webhook_manager.stop_worker()