"""
Slack/Microsoft Teams Bot Integration for KD-Code System
Enables generation and scanning of KD-Codes through workplace messaging platforms
"""

import asyncio
import json
from typing import Dict, Any, Optional
import logging
import requests
from flask import Flask, request, jsonify
from functools import wraps


class KDCodeBot:
    """
    Base class for workplace messaging platform bots
    """
    
    def __init__(self, platform: str, webhook_url: str = None, api_token: str = None):
        """
        Initialize the bot
        
        Args:
            platform: Platform name ('slack' or 'teams')
            webhook_url: Webhook URL for the bot
            api_token: API token for advanced features
        """
        self.platform = platform.lower()
        self.webhook_url = webhook_url
        self.api_token = api_token
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, message: str, channel: str = None, attachments: list = None) -> bool:
        """
        Send a message to the platform
        
        Args:
            message: Message text to send
            channel: Channel to send to (if applicable)
            attachments: List of attachments (images, files, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        if self.platform == 'slack':
            return self._send_slack_message(message, channel, attachments)
        elif self.platform == 'teams':
            return self._send_teams_message(message, channel, attachments)
        else:
            self.logger.error(f"Unsupported platform: {self.platform}")
            return False
    
    def _send_slack_message(self, message: str, channel: str = None, attachments: list = None) -> bool:
        """Send a message to Slack"""
        payload = {
            'text': message
        }
        
        if channel:
            payload['channel'] = channel
        
        if attachments:
            payload['attachments'] = attachments
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error sending Slack message: {e}")
            return False
    
    def _send_teams_message(self, message: str, channel: str = None, attachments: list = None) -> bool:
        """Send a message to Microsoft Teams"""
        # Teams uses a different webhook format
        payload = {
            '@type': 'MessageCard',
            '@context': 'http://schema.org/extensions',
            'themeColor': '0076D7',
            'summary': 'KD-Code Notification',
            'sections': [{
                'activityTitle': 'KD-Code System',
                'activitySubtitle': message,
                'markdown': True
            }]
        }
        
        if attachments:
            # Add images to the message
            images = []
            for attachment in attachments:
                if 'image_url' in attachment:
                    images.append({'image': attachment['image_url']})
            
            if images:
                payload['sections'][0]['images'] = images
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error sending Teams message: {e}")
            return False
    
    def generate_kd_code_from_command(self, text: str, user_id: str = None) -> Optional[str]:
        """
        Generate a KD-Code from a command
        
        Args:
            text: Text to encode in the KD-Code
            user_id: ID of the user requesting generation
        
        Returns:
            Base64 encoded KD-Code image or None if failed
        """
        try:
            from kd_core.encoder import generate_kd_code
            
            # Generate the KD-Code
            kd_code_b64 = generate_kd_code(text)
            
            # Log the generation event
            self.logger.info(f"KD-Code generated via bot for user {user_id}: {text[:50]}...")
            
            return kd_code_b64
        except Exception as e:
            self.logger.error(f"Error generating KD-Code from bot command: {e}")
            return None
    
    def handle_bot_command(self, command: str, user_id: str = None, channel: str = None) -> Dict[str, Any]:
        """
        Handle a bot command
        
        Args:
            command: Command received from the bot
            user_id: ID of the user issuing the command
            channel: Channel where command was issued
        
        Returns:
            Response dictionary
        """
        command_parts = command.strip().split(' ', 1)
        cmd = command_parts[0].lower()
        
        if cmd in ['/generate', '/gen', '!generate', '!gen']:
            if len(command_parts) < 2:
                return {
                    'response_type': 'ephemeral',
                    'text': 'Usage: /generate <text_to_encode>\nExample: /generate Hello World'
                }
            
            text_to_encode = command_parts[1]
            
            # Generate KD-Code
            kd_code_b64 = self.generate_kd_code_from_command(text_to_encode, user_id)
            
            if kd_code_b64:
                # Create attachment with the KD-Code image
                attachment = {
                    'title': f'Generated KD-Code for: {text_to_encode[:50]}{"..." if len(text_to_encode) > 50 else ""}',
                    'image_url': f'data:image/png;base64,{kd_code_b64}'
                }
                
                return {
                    'response_type': 'in_channel',
                    'text': f'Generated KD-Code for: "{text_to_encode}"',
                    'attachments': [attachment]
                }
            else:
                return {
                    'response_type': 'ephemeral',
                    'text': 'Error: Failed to generate KD-Code. Please try again.'
                }
        
        elif cmd in ['/help', '/info', '!help', '!info']:
            help_text = (
                "*KD-Code Bot Commands:*\n"
                "• `/generate <text>` - Generate a KD-Code from text\n"
                "• `/help` - Show this help message\n"
                "• `/scan <image_url>` - Scan a KD-Code from an image (coming soon)\n"
                "• `/history` - Show your recent KD-Code generation history (coming soon)"
            )
            
            return {
                'response_type': 'ephemeral',
                'text': help_text
            }
        
        elif cmd in ['/scan', '!scan']:
            if len(command_parts) < 2:
                return {
                    'response_type': 'ephemeral',
                    'text': 'Usage: /scan <image_url>\nExample: /scan https://example.com/image.png'
                }
            
            image_url = command_parts[1]
            # For now, just acknowledge the command - scanning implementation would go here
            return {
                'response_type': 'ephemeral',
                'text': f'Scanning KD-Code from: {image_url}\n(Scanning functionality coming soon)'
            }
        
        else:
            return {
                'response_type': 'ephemeral',
                'text': f'Unknown command: {cmd}\nUse `/help` to see available commands.'
            }


class SlackBot(KDCodeBot):
    """
    Slack-specific bot implementation
    """
    
    def __init__(self, webhook_url: str, api_token: str = None):
        super().__init__('slack', webhook_url, api_token)
    
    def verify_request(self, request) -> bool:
        """
        Verify that the request comes from Slack
        
        Args:
            request: Flask request object
        
        Returns:
            True if request is verified, False otherwise
        """
        # In a real implementation, you would verify Slack's request signature
        # This is a simplified version
        return True


class TeamsBot(KDCodeBot):
    """
    Microsoft Teams-specific bot implementation
    """
    
    def __init__(self, webhook_url: str, api_token: str = None):
        super().__init__('teams', webhook_url, api_token)
    
    def verify_request(self, request) -> bool:
        """
        Verify that the request comes from Teams
        
        Args:
            request: Flask request object
        
        Returns:
            True if request is verified, False otherwise
        """
        # In a real implementation, you would verify Teams' request signature
        # This is a simplified version
        return True


# Global bot instances
slack_bot = None
teams_bot = None


def initialize_bots(slack_webhook: str = None, teams_webhook: str = None, 
                   slack_token: str = None, teams_token: str = None):
    """
    Initialize the Slack and Teams bots
    
    Args:
        slack_webhook: Slack webhook URL
        teams_webhook: Teams webhook URL
        slack_token: Slack API token
        teams_token: Teams API token
    """
    global slack_bot, teams_bot
    
    if slack_webhook:
        slack_bot = SlackBot(slack_webhook, slack_token)
        print("Slack bot initialized")
    
    if teams_webhook:
        teams_bot = TeamsBot(teams_webhook, teams_token)
        print("Teams bot initialized")


def handle_slack_command(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a command from Slack
    
    Args:
        data: Slack command data
    
    Returns:
        Response to send back to Slack
    """
    if not slack_bot:
        return {
            'response_type': 'ephemeral',
            'text': 'Slack bot is not configured. Contact administrator.'
        }
    
    command = data.get('text', '')
    user_id = data.get('user_id', '')
    channel = data.get('channel_id', '')
    
    return slack_bot.handle_bot_command(command, user_id, channel)


def handle_teams_message(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a message from Microsoft Teams
    
    Args:
        data: Teams message data
    
    Returns:
        Response to send back to Teams
    """
    if not teams_bot:
        return {
            'type': 'message',
            'text': 'Teams bot is not configured. Contact administrator.'
        }
    
    # Extract text from Teams message
    text = data.get('text', '')
    if text.startswith('<at'):  # Remove @mention if present
        # Find the actual command after the mention
        parts = text.split('> ')
        if len(parts) > 1:
            text = parts[1]
    
    user_id = data.get('from', {}).get('id', '')
    channel = data.get('conversation', {}).get('id', '')
    
    # For Teams, we return a different format
    response = teams_bot.handle_bot_command(text, user_id, channel)
    
    # Convert to Teams format
    teams_response = {
        'type': 'message',
        'text': response.get('text', 'Command processed')
    }
    
    if 'attachments' in response:
        # Add card with image for Teams
        teams_response['attachments'] = []
        for attachment in response['attachments']:
            teams_response['attachments'].append({
                'contentType': 'application/vnd.microsoft.card.adaptive',
                'content': {
                    'type': 'AdaptiveCard',
                    '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json',
                    'version': '1.2',
                    'body': [
                        {
                            'type': 'TextBlock',
                            'text': attachment.get('title', 'KD-Code'),
                            'wrap': True
                        },
                        {
                            'type': 'Image',
                            'url': attachment['image_url'],
                            'altText': 'Generated KD-Code'
                        }
                    ]
                }
            })
    
    return teams_response


# Flask routes for bot integration
def add_bot_routes(app: Flask):
    """
    Add bot integration routes to a Flask app
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/bots/slack/command', methods=['POST'])
    def slack_command():
        """Handle Slack slash commands"""
        try:
            # Verify request is from Slack
            if slack_bot and not slack_bot.verify_request(request):
                return "Unauthorized", 401
            
            data = request.form.to_dict()  # Slack sends form data
            response = handle_slack_command(data)
            
            return jsonify(response)
        except Exception as e:
            app.logger.error(f"Error in Slack command handler: {e}")
            return jsonify({
                'response_type': 'ephemeral',
                'text': 'Error processing command. Please try again.'
            }), 500
    
    @app.route('/bots/teams/message', methods=['POST'])
    def teams_message():
        """Handle Microsoft Teams messages"""
        try:
            # Verify request is from Teams
            if teams_bot and not teams_bot.verify_request(request):
                return "Unauthorized", 401
            
            data = request.get_json()
            response = handle_teams_message(data)
            
            return jsonify(response)
        except Exception as e:
            app.logger.error(f"Error in Teams message handler: {e}")
            return jsonify({
                'type': 'message',
                'text': 'Error processing message. Please try again.'
            }), 500
    
    @app.route('/bots/slack/interactive', methods=['POST'])
    def slack_interactive():
        """Handle Slack interactive components (buttons, menus, etc.)"""
        try:
            payload = json.loads(request.form.get('payload', '{}'))
            
            # Handle different types of interactive components
            if payload.get('type') == 'block_actions':
                # Handle button clicks, menu selections, etc.
                action_id = payload['actions'][0]['action_id']
                
                if action_id == 'generate_kd_code':
                    # Extract text from the input field
                    text = payload['state']['values']['text_input']['text']['value']
                    
                    # Generate KD-Code
                    from kd_core.encoder import generate_kd_code
                    kd_code_b64 = generate_kd_code(text)
                    
                    if kd_code_b64:
                        # Respond with the generated KD-Code
                        response_url = payload['response_url']
                        response_payload = {
                            'text': f'Generated KD-Code for: "{text}"',
                            'attachments': [{
                                'title': f'KD-Code for: {text[:50]}{"..." if len(text) > 50 else ""}',
                                'image_url': f'data:image/png;base64,{kd_code_b64}'
                            }]
                        }
                        
                        requests.post(response_url, json=response_payload)
                        
                        return '', 200
                    else:
                        return jsonify({'text': 'Error generating KD-Code'}), 500
            
            return '', 200
        except Exception as e:
            app.logger.error(f"Error in Slack interactive handler: {e}")
            return "Error", 500


# Example usage
if __name__ == "__main__":
    # Example of initializing bots
    # initialize_bots(
    #     slack_webhook="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
    #     teams_webhook="https://outlook.office.com/webhook/YOUR/TEAMS/WEBHOOK"
    # )
    
    print("KD-Code Bot Integration System Initialized")
    print("Available endpoints:")
    print("  POST /bots/slack/command - Handle Slack slash commands")
    print("  POST /bots/teams/message - Handle Teams messages")
    print("  POST /bots/slack/interactive - Handle Slack interactive components")
    
    # Example of how to use the bot system:
    # 1. Set up Slack app with slash command: /kdcode
    # 2. Set request URL to your server's /bots/slack/command endpoint
    # 3. Users can then use commands like:
    #    /kdcode generate Hello World
    #    /kdcode help