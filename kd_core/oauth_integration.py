"""
OAuth 2.0 Integration Module for KD-Code System
Enables third-party applications to integrate with the KD-Code system
"""

from flask import Flask, request, jsonify, redirect, url_for
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import grants
from authlib.common.security import generate_token
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import os


class OAuth2Provider:
    """
    OAuth 2.0 provider implementation for KD-Code system
    """
    
    def __init__(self, db_path: str = "oauth_tokens.db"):
        """
        Initialize the OAuth 2.0 provider
        
        Args:
            db_path: Path to the database for storing OAuth tokens
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        self.init_database()
    
    def init_database(self):
        """Initialize the database with OAuth-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create clients table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT UNIQUE NOT NULL,
                client_secret TEXT NOT NULL,
                client_name TEXT NOT NULL,
                redirect_uris TEXT,  -- JSON array of redirect URIs
                scopes TEXT,  -- JSON array of allowed scopes
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create authorization codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                user_id TEXT,
                redirect_uri TEXT NOT NULL,
                scopes TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES oauth_clients (client_id)
            )
        ''')
        
        # Create access tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_access_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                client_id TEXT NOT NULL,
                user_id TEXT,
                scopes TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES oauth_clients (client_id)
            )
        ''')
        
        # Create refresh tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                access_token_id INTEGER,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (access_token_id) REFERENCES oauth_access_tokens (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_client(self, client_name: str, redirect_uris: List[str], 
                       scopes: List[str] = None) -> Dict[str, str]:
        """
        Register a new OAuth client application
        
        Args:
            client_name: Name of the client application
            redirect_uris: List of allowed redirect URIs
            scopes: List of allowed scopes (defaults to standard scopes)
        
        Returns:
            Dictionary with client credentials
        """
        if scopes is None:
            scopes = ['generate', 'scan', 'read:user', 'write:user']
        
        client_id = secrets.token_urlsafe(32)
        client_secret = secrets.token_urlsafe(48)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO oauth_clients 
                (client_id, client_secret, client_name, redirect_uris, scopes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                client_id, 
                client_secret, 
                client_name,
                json.dumps(redirect_uris),
                json.dumps(scopes)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'client_id': client_id,
                'client_secret': client_secret,
                'client_name': client_name,
                'redirect_uris': redirect_uris,
                'scopes': scopes
            }
        except Exception as e:
            conn.close()
            self.logger.error(f"Error registering OAuth client: {e}")
            return None
    
    def generate_authorization_code(self, client_id: str, user_id: str, 
                                  redirect_uri: str, scopes: List[str]) -> str:
        """
        Generate an authorization code for OAuth flow
        
        Args:
            client_id: Client ID requesting authorization
            user_id: User ID granting authorization
            redirect_uri: Redirect URI for the authorization code
            scopes: Scopes being requested
        
        Returns:
            Authorization code
        """
        # Verify client exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM oauth_clients WHERE client_id = ?', (client_id,))
        if not cursor.fetchone():
            conn.close()
            raise ValueError("Invalid client ID")
        
        # Generate authorization code
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=10)  # 10 minute expiry
        
        cursor.execute('''
            INSERT INTO oauth_authorization_codes 
            (code, client_id, user_id, redirect_uri, scopes, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            code, client_id, user_id, redirect_uri, 
            json.dumps(scopes), expires_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return code
    
    def exchange_code_for_token(self, code: str, client_id: str, 
                              client_secret: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """
        Exchange an authorization code for access and refresh tokens
        
        Args:
            code: Authorization code
            client_id: Client ID
            client_secret: Client secret
            redirect_uri: Redirect URI (must match the one used for authorization)
        
        Returns:
            Token response or None if invalid
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verify the authorization code
        cursor.execute('''
            SELECT client_id, user_id, redirect_uri, scopes, expires_at
            FROM oauth_authorization_codes
            WHERE code = ?
        ''', (code,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        
        db_client_id, user_id, db_redirect_uri, scopes_json, expires_at = result
        
        # Verify client credentials
        cursor.execute('''
            SELECT client_secret FROM oauth_clients 
            WHERE client_id = ?
        ''', (client_id,))
        
        client_result = cursor.fetchone()
        if not client_result or client_result[0] != client_secret:
            conn.close()
            return None
        
        # Verify redirect URI matches
        if db_redirect_uri != redirect_uri:
            conn.close()
            return None
        
        # Check if code has expired
        if datetime.now() > datetime.fromisoformat(expires_at):
            conn.close()
            return None
        
        # Generate access and refresh tokens
        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(48)
        
        # Set expiration times
        access_expires_at = datetime.now() + timedelta(hours=1)  # 1 hour expiry
        refresh_expires_at = datetime.now() + timedelta(days=30)  # 30 days expiry
        
        # Store access token
        cursor.execute('''
            INSERT INTO oauth_access_tokens 
            (token, client_id, user_id, scopes, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            access_token, client_id, user_id, 
            scopes_json, access_expires_at.isoformat()
        ))
        
        access_token_id = cursor.lastrowid
        
        # Store refresh token
        cursor.execute('''
            INSERT INTO oauth_refresh_tokens 
            (token, access_token_id, expires_at)
            VALUES (?, ?, ?)
        ''', (refresh_token, access_token_id, refresh_expires_at.isoformat()))
        
        conn.commit()
        
        # Mark authorization code as used
        cursor.execute('DELETE FROM oauth_authorization_codes WHERE code = ?', (code,))
        conn.commit()
        conn.close()
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,  # 1 hour in seconds
            'scope': json.loads(scopes_json)
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: Refresh token
        
        Returns:
            New token response or None if invalid
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find the refresh token
        cursor.execute('''
            SELECT ort.access_token_id, oat.client_id, oat.user_id, oat.scopes, ort.expires_at
            FROM oauth_refresh_tokens ort
            JOIN oauth_access_tokens oat ON ort.access_token_id = oat.id
            WHERE ort.token = ?
        ''', (refresh_token,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        
        access_token_id, client_id, user_id, scopes_json, expires_at = result
        
        # Check if refresh token has expired
        if datetime.now() > datetime.fromisoformat(expires_at):
            conn.close()
            return None
        
        # Generate new access token
        new_access_token = secrets.token_urlsafe(48)
        new_expires_at = datetime.now() + timedelta(hours=1)  # 1 hour expiry
        
        # Update access token
        cursor.execute('''
            UPDATE oauth_access_tokens
            SET token = ?, expires_at = ?
            WHERE id = ?
        ''', (new_access_token, new_expires_at.isoformat(), access_token_id))
        
        conn.commit()
        conn.close()
        
        return {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': 3600,  # 1 hour in seconds
            'scope': json.loads(scopes_json)
        }
    
    def validate_access_token(self, token: str, required_scopes: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Validate an access token and return associated information
        
        Args:
            token: Access token to validate
            required_scopes: List of required scopes (optional)
        
        Returns:
            Token information or None if invalid
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT client_id, user_id, scopes, expires_at
            FROM oauth_access_tokens
            WHERE token = ?
        ''', (token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        client_id, user_id, scopes_json, expires_at = result
        
        # Check if token has expired
        if datetime.now() > datetime.fromisoformat(expires_at):
            return None
        
        scopes = json.loads(scopes_json) if scopes_json else []
        
        # Check if required scopes are present
        if required_scopes:
            for req_scope in required_scopes:
                if req_scope not in scopes:
                    return None
        
        return {
            'client_id': client_id,
            'user_id': user_id,
            'scopes': scopes
        }
    
    def revoke_access_token(self, token: str) -> bool:
        """
        Revoke an access token
        
        Args:
            token: Access token to revoke
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM oauth_access_tokens WHERE token = ?', (token,))
            success = cursor.rowcount > 0
            
            if success:
                # Also delete associated refresh tokens
                cursor.execute('''
                    DELETE ort FROM oauth_refresh_tokens ort
                    JOIN oauth_access_tokens oat ON ort.access_token_id = oat.id
                    WHERE oat.token = ?
                ''', (token,))
            
            conn.commit()
            conn.close()
            return success
        except Exception as e:
            conn.close()
            self.logger.error(f"Error revoking access token: {e}")
            return False


# Global OAuth provider instance
oauth_provider = OAuth2Provider()


def initialize_oauth_system():
    """Initialize the OAuth 2.0 system"""
    global oauth_provider
    oauth_provider = OAuth2Provider()


def register_third_party_app(client_name: str, redirect_uris: List[str], 
                           scopes: List[str] = None) -> Optional[Dict[str, str]]:
    """
    Register a third-party application with the OAuth system
    
    Args:
        client_name: Name of the application
        redirect_uris: List of allowed redirect URIs
        scopes: List of allowed scopes
    
    Returns:
        Client credentials or None if registration failed
    """
    return oauth_provider.register_client(client_name, redirect_uris, scopes)


def generate_auth_code(client_id: str, user_id: str, redirect_uri: str, 
                      scopes: List[str]) -> Optional[str]:
    """
    Generate an authorization code for OAuth flow
    
    Args:
        client_id: Client ID requesting authorization
        user_id: User ID granting authorization
        redirect_uri: Redirect URI for the authorization code
        scopes: Scopes being requested
    
    Returns:
        Authorization code or None if failed
    """
    try:
        return oauth_provider.generate_authorization_code(client_id, user_id, redirect_uri, scopes)
    except ValueError:
        return None


def exchange_code_for_tokens(code: str, client_id: str, client_secret: str, 
                           redirect_uri: str) -> Optional[Dict[str, Any]]:
    """
    Exchange an authorization code for access and refresh tokens
    
    Args:
        code: Authorization code
        client_id: Client ID
        client_secret: Client secret
        redirect_uri: Redirect URI
    
    Returns:
        Token response or None if exchange failed
    """
    return oauth_provider.exchange_code_for_token(code, client_id, client_secret, redirect_uri)


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Refresh an access token using a refresh token
    
    Args:
        refresh_token: Refresh token
    
    Returns:
        New token response or None if refresh failed
    """
    return oauth_provider.refresh_access_token(refresh_token)


def validate_oauth_token(token: str, required_scopes: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Validate an OAuth access token
    
    Args:
        token: Access token to validate
        required_scopes: Required scopes for the operation
    
    Returns:
        Token information or None if invalid
    """
    return oauth_provider.validate_access_token(token, required_scopes)


def revoke_oauth_token(token: str) -> bool:
    """
    Revoke an OAuth access token
    
    Args:
        token: Access token to revoke
    
    Returns:
        True if successful, False otherwise
    """
    return oauth_provider.revoke_access_token(token)


# Flask routes for OAuth endpoints
def add_oauth_routes(app: Flask, jwt: JWTManager):
    """
    Add OAuth 2.0 routes to a Flask application
    
    Args:
        app: Flask application instance
        jwt: JWT manager instance
    """
    
    @app.route('/oauth/authorize', methods=['GET'])
    def oauth_authorize():
        """OAuth authorization endpoint"""
        client_id = request.args.get('client_id')
        redirect_uri = request.args.get('redirect_uri')
        response_type = request.args.get('response_type', 'code')
        scope = request.args.get('scope', '')
        state = request.args.get('state')
        
        # Validate required parameters
        if not client_id or not redirect_uri or response_type != 'code':
            return jsonify({'error': 'Invalid request parameters'}), 400
        
        # Verify client exists
        conn = sqlite3.connect(oauth_provider.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT redirect_uris FROM oauth_clients WHERE client_id = ?', (client_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({'error': 'Invalid client ID'}), 400
        
        # Check if redirect URI is allowed
        allowed_uris = json.loads(result[0])
        if redirect_uri not in allowed_uris:
            return jsonify({'error': 'Redirect URI not allowed'}), 400
        
        # In a real implementation, you would show an authorization page here
        # For this example, we'll assume the user has authorized the request
        # and generate an authorization code
        
        # Get the currently authenticated user (requires JWT token in header)
        try:
            current_user = get_jwt_identity()
        except:
            # If no JWT token, redirect to login
            return redirect(url_for('login', next=request.url))
        
        # Generate authorization code
        scopes = scope.split(' ') if scope else []
        auth_code = generate_auth_code(client_id, current_user, redirect_uri, scopes)
        
        if not auth_code:
            return jsonify({'error': 'Failed to generate authorization code'}), 500
        
        # Redirect back to client with authorization code
        redirect_url = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_url += f"&state={state}"
        
        return redirect(redirect_url)
    
    @app.route('/oauth/token', methods=['POST'])
    def oauth_token():
        """OAuth token endpoint"""
        grant_type = request.form.get('grant_type')
        
        if grant_type == 'authorization_code':
            code = request.form.get('code')
            client_id = request.form.get('client_id')
            client_secret = request.form.get('client_secret')
            redirect_uri = request.form.get('redirect_uri')
            
            if not all([code, client_id, client_secret, redirect_uri]):
                return jsonify({'error': 'Missing required parameters'}), 400
            
            token_response = exchange_code_for_tokens(code, client_id, client_secret, redirect_uri)
            
            if not token_response:
                return jsonify({'error': 'Invalid authorization code or credentials'}), 400
            
            return jsonify(token_response)
        
        elif grant_type == 'refresh_token':
            refresh_token = request.form.get('refresh_token')
            
            if not refresh_token:
                return jsonify({'error': 'Missing refresh token'}), 400
            
            token_response = refresh_access_token(refresh_token)
            
            if not token_response:
                return jsonify({'error': 'Invalid refresh token'}), 400
            
            return jsonify(token_response)
        
        else:
            return jsonify({'error': 'Unsupported grant type'}), 400
    
    @app.route('/oauth/revoke', methods=['POST'])
    def oauth_revoke():
        """OAuth token revocation endpoint"""
        token = request.form.get('token')
        
        if not token:
            return jsonify({'error': 'Token is required'}), 400
        
        success = revoke_oauth_token(token)
        
        if success:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'error': 'Failed to revoke token'}), 400


# Example usage
if __name__ == "__main__":
    # Initialize the OAuth system
    initialize_oauth_system()
    
    # Example: Register a third-party application
    app_registration = register_third_party_app(
        client_name="Example Third-Party App",
        redirect_uris=["https://example.com/callback"],
        scopes=["generate", "scan"]
    )
    
    if app_registration:
        print(f"Third-party app registered successfully!")
        print(f"Client ID: {app_registration['client_id']}")
        print(f"Client Secret: {app_registration['client_secret'][:10]}...")  # Show first 10 chars only
        print(f"Allowed scopes: {app_registration['scopes']}")
    else:
        print("Failed to register third-party app")
    
    # Example: Validate an access token (would need a real token in practice)
    # token_info = validate_oauth_token("some_access_token", ["generate"])
    # print(f"Token validation result: {token_info}")