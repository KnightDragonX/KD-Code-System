"""
Real-Time Collaborative Scanning Module for KD-Code System
Enables multiple users to scan the same KD-Code simultaneously and share results
"""

import asyncio
import websockets
import json
import uuid
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
from threading import Thread
import base64
from kd_core.decoder import decode_kd_code
from kd_core.config import (
    DEFAULT_SCAN_SEGMENTS_PER_RING, DEFAULT_MIN_ANCHOR_RADIUS, DEFAULT_MAX_ANCHOR_RADIUS
)


class ScanEventType(Enum):
    """Types of events in collaborative scanning"""
    START_SCAN = "start_scan"
    FRAME_PROCESSED = "frame_processed"
    CODE_DETECTED = "code_detected"
    SCAN_COMPLETE = "scan_complete"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    CHAT_MESSAGE = "chat_message"
    SCAN_SETTINGS_UPDATE = "scan_settings_update"


@dataclass
class ScanParticipant:
    """Represents a participant in a collaborative scan session"""
    user_id: str
    username: str
    join_time: float
    is_scanning: bool = False
    last_activity: float = 0.0


@dataclass
class ScanResult:
    """Represents a scan result in collaborative scanning"""
    result_id: str
    user_id: str
    timestamp: float
    decoded_text: Optional[str]
    confidence: float
    processing_time: float
    image_preview: Optional[str]  # Base64 encoded image preview


@dataclass
class CollaborativeScanSession:
    """Represents a collaborative scanning session"""
    session_id: str
    created_at: float
    participants: List[ScanParticipant]
    scan_results: List[ScanResult]
    settings: Dict[str, any]
    is_active: bool
    shared_canvas: Optional[Dict] = None  # For AR overlay sharing


class CollaborativeScanner:
    """
    Manages real-time collaborative scanning sessions
    """
    
    def __init__(self):
        self.sessions: Dict[str, CollaborativeScanSession] = {}
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}  # user_id -> websocket
        self.session_participants: Dict[str, Set[str]] = {}  # session_id -> set of user_ids
        self.scan_locks: Dict[str, asyncio.Lock] = {}  # session_id -> lock
    
    async def create_session(self, creator_id: str, session_name: str = "Collaborative Scan", 
                           scan_settings: Dict[str, any] = None) -> str:
        """
        Create a new collaborative scanning session
        
        Args:
            creator_id: ID of the session creator
            session_name: Name of the session
            scan_settings: Initial scan settings
        
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        if scan_settings is None:
            scan_settings = {
                'segments_per_ring': DEFAULT_SCAN_SEGMENTS_PER_RING,
                'min_anchor_radius': DEFAULT_MIN_ANCHOR_RADIUS,
                'max_anchor_radius': DEFAULT_MAX_ANCHOR_RADIUS,
                'enable_multithreading': True,
                'detection_sensitivity': 'medium'
            }
        
        creator = ScanParticipant(
            user_id=creator_id,
            username=f"User_{creator_id[:8]}",
            join_time=time.time(),
            is_scanning=False,
            last_activity=time.time()
        )
        
        session = CollaborativeScanSession(
            session_id=session_id,
            created_at=time.time(),
            participants=[creator],
            scan_results=[],
            settings=scan_settings,
            is_active=True
        )
        
        self.sessions[session_id] = session
        self.session_participants[session_id] = {creator_id}
        self.scan_locks[session_id] = asyncio.Lock()
        
        return session_id
    
    async def join_session(self, session_id: str, user_id: str, username: str = None) -> bool:
        """
        Join a collaborative scanning session
        
        Args:
            session_id: Session ID to join
            user_id: User ID joining
            username: Optional username
        
        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions or not self.sessions[session_id].is_active:
            return False
        
        async with self.scan_locks[session_id]:
            # Check if user is already in the session
            for participant in self.sessions[session_id].participants:
                if participant.user_id == user_id:
                    return True  # Already joined
            
            # Add user to participants
            user = ScanParticipant(
                user_id=user_id,
                username=username or f"User_{user_id[:8]}",
                join_time=time.time(),
                last_activity=time.time()
            )
            
            self.sessions[session_id].participants.append(user)
            self.session_participants[session_id].add(user_id)
            
            # Notify all participants about the new user
            await self.broadcast_to_session(
                session_id,
                {
                    'type': ScanEventType.USER_JOIN.value,
                    'user': {
                        'user_id': user.user_id,
                        'username': user.username,
                        'join_time': user.join_time
                    },
                    'timestamp': time.time()
                }
            )
            
            # Send session state to new user
            if user_id in self.connections:
                session_state = await self.get_session_state(session_id)
                await self.connections[user_id].send(json.dumps({
                    'type': 'session_state',
                    'state': session_state
                }))
            
            return True
    
    async def leave_session(self, session_id: str, user_id: str):
        """
        Leave a collaborative scanning session
        
        Args:
            session_id: Session ID to leave
            user_id: User ID leaving
        """
        if session_id not in self.sessions:
            return
        
        async with self.scan_locks[session_id]:
            # Remove user from participants
            self.sessions[session_id].participants = [
                p for p in self.sessions[session_id].participants 
                if p.user_id != user_id
            ]
            
            # Remove from session participants set
            if session_id in self.session_participants:
                self.session_participants[session_id].discard(user_id)
            
            # If no participants left, deactivate session
            if not self.sessions[session_id].participants:
                self.sessions[session_id].is_active = False
            
            # Notify remaining participants
            await self.broadcast_to_session(
                session_id,
                {
                    'type': ScanEventType.USER_LEAVE.value,
                    'user_id': user_id,
                    'timestamp': time.time()
                }
            )
    
    async def process_scan_frame(self, session_id: str, user_id: str, frame_data: str):
        """
        Process a scan frame from a user and share results with collaborators
        
        Args:
            session_id: Session ID
            user_id: User ID submitting the frame
            frame_data: Base64 encoded image frame data
        """
        if session_id not in self.sessions:
            return
        
        start_time = time.time()
        
        try:
            # Decode the frame data
            if frame_data.startswith('data:image'):
                header, encoded = frame_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
            else:
                image_bytes = base64.b64decode(frame_data)
            
            # Decode the KD-Code using the session settings
            session_settings = self.sessions[session_id].settings
            decoded_text = decode_kd_code(
                image_bytes,
                segments_per_ring=session_settings.get('segments_per_ring', DEFAULT_SCAN_SEGMENTS_PER_RING),
                min_anchor_radius=session_settings.get('min_anchor_radius', DEFAULT_MIN_ANCHOR_RADIUS),
                max_anchor_radius=session_settings.get('max_anchor_radius', DEFAULT_MAX_ANCHOR_RADIUS)
            )
            
            processing_time = time.time() - start_time
            confidence = 0.9 if decoded_text else 0.1  # Simplified confidence calculation
            
            # Create scan result
            result = ScanResult(
                result_id=str(uuid.uuid4()),
                user_id=user_id,
                timestamp=time.time(),
                decoded_text=decoded_text,
                confidence=confidence,
                processing_time=processing_time,
                image_preview=frame_data[:100] + "..." if len(frame_data) > 100 else frame_data  # Truncate for storage
            )
            
            # Add to session results
            async with self.scan_locks[session_id]:
                self.sessions[session_id].scan_results.append(result)
            
            # Prepare result message
            result_msg = {
                'type': ScanEventType.FRAME_PROCESSED.value,
                'result': {
                    'result_id': result.result_id,
                    'user_id': result.user_id,
                    'timestamp': result.timestamp,
                    'decoded_text': result.decoded_text,
                    'confidence': result.confidence,
                    'processing_time': result.processing_time
                },
                'timestamp': time.time()
            }
            
            # If a code was detected, send special notification
            if decoded_text:
                result_msg['type'] = ScanEventType.CODE_DETECTED.value
                result_msg['message'] = f"User {self._get_username(session_id, user_id)} detected: {decoded_text[:50]}..."
            
            # Broadcast to all session participants
            await self.broadcast_to_session(session_id, result_msg)
            
        except Exception as e:
            error_msg = {
                'type': 'error',
                'message': f'Error processing scan frame: {str(e)}',
                'timestamp': time.time()
            }
            
            if user_id in self.connections:
                await self.connections[user_id].send(json.dumps(error_msg))
    
    async def update_scan_settings(self, session_id: str, user_id: str, new_settings: Dict[str, any]):
        """
        Update scan settings for a collaborative session
        
        Args:
            session_id: Session ID
            user_id: User ID making the update (should be session owner)
            new_settings: New scan settings
        """
        if session_id not in self.sessions:
            return
        
        # Only allow session owner to update settings (simplified check)
        session_owner = self.sessions[session_id].participants[0].user_id if self.sessions[session_id].participants else None
        if user_id != session_owner:
            # For now, allow anyone to update settings
            pass
        
        async with self.scan_locks[session_id]:
            self.sessions[session_id].settings.update(new_settings)
        
        # Broadcast settings update to all participants
        await self.broadcast_to_session(
            session_id,
            {
                'type': ScanEventType.SCAN_SETTINGS_UPDATE.value,
                'settings': self.sessions[session_id].settings,
                'updated_by': user_id,
                'timestamp': time.time()
            }
        )
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, any]):
        """
        Broadcast a message to all users in a session
        
        Args:
            session_id: Session ID
            message: Message to broadcast
        """
        if session_id not in self.session_participants:
            return
        
        message_json = json.dumps(message)
        
        # Send to all connected users in this session
        for user_id in self.session_participants[session_id]:
            if user_id in self.connections:
                try:
                    await self.connections[user_id].send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    # Remove disconnected user
                    del self.connections[user_id]
                    # Also remove from session
                    await self.leave_session(session_id, user_id)
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, any]]:
        """
        Get the current state of a collaborative scanning session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session state or None if session doesn't exist
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            'session_id': session.session_id,
            'created_at': session.created_at,
            'participants': [
                {
                    'user_id': p.user_id,
                    'username': p.username,
                    'join_time': p.join_time,
                    'is_scanning': p.is_scanning,
                    'last_activity': p.last_activity
                }
                for p in session.participants
            ],
            'settings': session.settings,
            'is_active': session.is_active,
            'result_count': len(session.scan_results),
            'recent_results': [
                {
                    'result_id': r.result_id,
                    'user_id': r.user_id,
                    'timestamp': r.timestamp,
                    'decoded_text': r.decoded_text,
                    'confidence': r.confidence,
                    'processing_time': r.processing_time
                }
                for r in session.scan_results[-5:]  # Last 5 results
            ]
        }
    
    def _get_username(self, session_id: str, user_id: str) -> str:
        """
        Get username for a user in a session
        
        Args:
            session_id: Session ID
            user_id: User ID
        
        Returns:
            Username or user ID if not found
        """
        if session_id in self.sessions:
            for participant in self.sessions[session_id].participants:
                if participant.user_id == user_id:
                    return participant.username
        return user_id


class CollaborativeScanServer:
    """
    WebSocket server for handling real-time collaborative scanning
    """
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.scanner = CollaborativeScanner()
        self.websocket_server = None
    
    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handle a new WebSocket connection for collaborative scanning
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        user_id = str(uuid.uuid4())
        self.scanner.connections[user_id] = websocket
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(user_id, data)
                except json.JSONDecodeError:
                    # Send error message to client
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON message'
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Clean up connection
            if user_id in self.scanner.connections:
                del self.scanner.connections[user_id]
            
            # Remove user from any sessions they were in
            for session_id, session_users in self.scanner.session_participants.items():
                if user_id in session_users:
                    await self.scanner.leave_session(session_id, user_id)
    
    async def handle_message(self, user_id: str, data: Dict[str, any]):
        """
        Handle incoming messages from clients
        
        Args:
            user_id: User ID of the sender
            data: Message data
        """
        msg_type = data.get('type')
        
        if msg_type == 'create_session':
            session_name = data.get('session_name', 'Collaborative Scan')
            settings = data.get('settings')
            
            session_id = await self.scanner.create_session(user_id, session_name, settings)
            
            await self.scanner.connections[user_id].send(json.dumps({
                'type': 'session_created',
                'session_id': session_id
            }))
        
        elif msg_type == 'join_session':
            session_id = data.get('session_id')
            username = data.get('username')
            
            success = await self.scanner.join_session(session_id, user_id, username)
            
            if success:
                session_state = await self.scanner.get_session_state(session_id)
                await self.scanner.connections[user_id].send(json.dumps({
                    'type': 'session_joined',
                    'state': session_state
                }))
            else:
                await self.scanner.connections[user_id].send(json.dumps({
                    'type': 'error',
                    'message': 'Could not join session'
                }))
        
        elif msg_type == 'submit_frame':
            session_id = data.get('session_id')
            frame_data = data.get('frame_data')
            
            if session_id and frame_data:
                await self.scanner.process_scan_frame(session_id, user_id, frame_data)
        
        elif msg_type == 'update_settings':
            session_id = data.get('session_id')
            new_settings = data.get('settings', {})
            
            if session_id:
                await self.scanner.update_scan_settings(session_id, user_id, new_settings)
        
        elif msg_type == 'send_chat':
            session_id = data.get('session_id')
            message = data.get('message')
            
            if session_id and message:
                await self.scanner.broadcast_to_session(
                    session_id,
                    {
                        'type': ScanEventType.CHAT_MESSAGE.value,
                        'user_id': user_id,
                        'message': message,
                        'timestamp': time.time()
                    }
                )
    
    async def start_server(self):
        """Start the collaborative scanning WebSocket server"""
        self.websocket_server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )
        print(f"Collaborative scanning server started on {self.host}:{self.port}")
        
        # Keep the server running
        await self.websocket_server.wait_closed()
    
    def run_server(self):
        """Run the server in a separate thread"""
        def run():
            asyncio.run(self.start_server())
        
        server_thread = Thread(target=run, daemon=True)
        server_thread.start()
        return server_thread


# Global collaborative scanner instance
collaborative_scanner = CollaborativeScanner()


def initialize_collaborative_scanning():
    """Initialize the collaborative scanning system"""
    global collaborative_scanner
    collaborative_scanner = CollaborativeScanner()


def create_collaborative_scan_session(creator_id: str, session_name: str = "Collaborative Scan", 
                                   settings: Dict[str, any] = None) -> str:
    """
    Create a new collaborative scanning session
    
    Args:
        creator_id: ID of the session creator
        session_name: Name of the session
        settings: Initial scan settings
    
    Returns:
        Session ID
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    session_id = loop.run_until_complete(
        collaborative_scanner.create_session(creator_id, session_name, settings)
    )
    loop.close()
    return session_id


def join_collaborative_scan_session(session_id: str, user_id: str, username: str = None) -> bool:
    """
    Join a collaborative scanning session
    
    Args:
        session_id: Session ID to join
        user_id: User ID joining
        username: Optional username
    
    Returns:
        True if successful, False otherwise
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(
        collaborative_scanner.join_session(session_id, user_id, username)
    )
    loop.close()
    return success


def submit_scan_frame_to_session(session_id: str, user_id: str, frame_data: str):
    """
    Submit a scan frame to a collaborative session
    
    Args:
        session_id: Session ID
        user_id: User ID submitting the frame
        frame_data: Base64 encoded image frame
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        collaborative_scanner.process_scan_frame(session_id, user_id, frame_data)
    )
    loop.close()


def get_collaborative_session_state(session_id: str) -> Optional[Dict[str, any]]:
    """
    Get the state of a collaborative scanning session
    
    Args:
        session_id: Session ID
    
    Returns:
        Session state or None if session doesn't exist
    """
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    state = loop.run_until_complete(
        collaborative_scanner.get_session_state(session_id)
    )
    loop.close()
    return state


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def example():
        # Create a collaborative scanning session
        session_id = await collaborative_scanner.create_session(
            "user123", 
            "Team Scan Session"
        )
        print(f"Created session: {session_id}")
        
        # Simulate joining users
        await collaborative_scanner.join_session(session_id, "user456", "Alice")
        await collaborative_scanner.join_session(session_id, "user789", "Bob")
        
        # Get session state
        state = await collaborative_scanner.get_session_state(session_id)
        print(f"Session has {len(state['participants'])} participants")
        
        # Simulate submitting a scan frame (would be actual image data in real use)
        fake_frame_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        await collaborative_scanner.process_scan_frame(session_id, "user123", fake_frame_data)
        
        print("Collaborative scanning example completed")
    
    # Run the example
    asyncio.run(example())