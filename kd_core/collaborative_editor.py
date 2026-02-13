"""
Collaborative Code Editor for KD-Code System
Enables real-time collaboration for KD-Code generation and editing
"""

import json
import uuid
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import asyncio
import websockets
from threading import Thread


class OperationType(Enum):
    """Types of operations in the collaborative editor"""
    INSERT = "insert"
    DELETE = "delete"
    UPDATE = "update"
    JOIN = "join"
    LEAVE = "leave"
    SELECTION = "selection"
    CHAT = "chat"


@dataclass
class User:
    """Represents a user in the collaborative session"""
    user_id: str
    username: str
    color: str
    join_time: float


@dataclass
class Operation:
    """Represents an operation in the collaborative editor"""
    op_id: str
    user_id: str
    operation_type: OperationType
    position: Optional[int] = None
    text: Optional[str] = None
    timestamp: float = 0.0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['operation_type'] = self.operation_type.value
        return result


@dataclass
class CollaborativeDocument:
    """Represents a collaborative document for KD-Code editing"""
    doc_id: str
    title: str
    content: str
    created_at: float
    last_modified: float
    owner_id: str
    participants: List[User]
    operations_log: List[Operation]
    kd_code_settings: Dict[str, Any]  # KD-Code generation parameters
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['participants'] = [asdict(user) for user in self.participants]
        result['operations_log'] = [op.to_dict() for op in self.operations_log]
        result['operation_type'] = self.operation_type.value if hasattr(self, 'operation_type') else None
        return result


class CollaborativeEditor:
    """
    Collaborative editor for KD-Code generation
    Implements operational transformation for real-time collaboration
    """
    
    def __init__(self):
        self.documents: Dict[str, CollaborativeDocument] = {}
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}  # user_id -> websocket
        self.document_sessions: Dict[str, List[str]] = {}  # doc_id -> list of user_ids
        self.locks: Dict[str, asyncio.Lock] = {}  # doc_id -> lock
    
    async def create_document(self, title: str, owner_id: str, initial_content: str = "", 
                             kd_code_settings: Dict[str, Any] = None) -> str:
        """
        Create a new collaborative document
        
        Args:
            title: Title of the document
            owner_id: ID of the document owner
            initial_content: Initial content of the document
            kd_code_settings: KD-Code generation parameters
        
        Returns:
            Document ID
        """
        doc_id = str(uuid.uuid4())
        
        if kd_code_settings is None:
            from kd_core.config import (
                DEFAULT_SEGMENTS_PER_RING, DEFAULT_ANCHOR_RADIUS, DEFAULT_RING_WIDTH,
                DEFAULT_SCALE_FACTOR, DEFAULT_MAX_CHARS
            )
            kd_code_settings = {
                'segments_per_ring': DEFAULT_SEGMENTS_PER_RING,
                'anchor_radius': DEFAULT_ANCHOR_RADIUS,
                'ring_width': DEFAULT_RING_WIDTH,
                'scale_factor': DEFAULT_SCALE_FACTOR,
                'max_chars': DEFAULT_MAX_CHARS
            }
        
        owner = User(
            user_id=owner_id,
            username=f"User_{owner_id[:8]}",
            color=self._generate_user_color(owner_id),
            join_time=time.time()
        )
        
        document = CollaborativeDocument(
            doc_id=doc_id,
            title=title,
            content=initial_content,
            created_at=time.time(),
            last_modified=time.time(),
            owner_id=owner_id,
            participants=[owner],
            operations_log=[],
            kd_code_settings=kd_code_settings
        )
        
        self.documents[doc_id] = document
        self.locks[doc_id] = asyncio.Lock()
        
        return doc_id
    
    async def join_document(self, doc_id: str, user_id: str, username: str = None) -> bool:
        """
        Join a collaborative document session
        
        Args:
            doc_id: Document ID to join
            user_id: User ID joining
            username: Optional username
        
        Returns:
            True if successful, False otherwise
        """
        if doc_id not in self.documents:
            return False
        
        async with self.locks[doc_id]:
            # Check if user is already in the document
            for participant in self.documents[doc_id].participants:
                if participant.user_id == user_id:
                    return True  # Already joined
            
            # Add user to participants
            user = User(
                user_id=user_id,
                username=username or f"User_{user_id[:8]}",
                color=self._generate_user_color(user_id),
                join_time=time.time()
            )
            
            self.documents[doc_id].participants.append(user)
            
            # Add to document session
            if doc_id not in self.document_sessions:
                self.document_sessions[doc_id] = []
            self.document_sessions[doc_id].append(user_id)
            
            # Broadcast join event
            await self.broadcast_to_document(
                doc_id,
                {
                    'type': OperationType.JOIN.value,
                    'user': asdict(user),
                    'timestamp': time.time()
                }
            )
            
            return True
    
    async def leave_document(self, doc_id: str, user_id: str):
        """
        Leave a collaborative document session
        
        Args:
            doc_id: Document ID to leave
            user_id: User ID leaving
        """
        if doc_id not in self.documents:
            return
        
        async with self.locks[doc_id]:
            # Remove user from participants
            self.documents[doc_id].participants = [
                u for u in self.documents[doc_id].participants 
                if u.user_id != user_id
            ]
            
            # Remove from document session
            if doc_id in self.document_sessions:
                self.document_sessions[doc_id] = [
                    uid for uid in self.document_sessions[doc_id] 
                    if uid != user_id
                ]
            
            # Broadcast leave event
            await self.broadcast_to_document(
                doc_id,
                {
                    'type': OperationType.LEAVE.value,
                    'user_id': user_id,
                    'timestamp': time.time()
                }
            )
    
    async def apply_operation(self, doc_id: str, operation: Operation):
        """
        Apply an operation to a document with operational transformation
        
        Args:
            doc_id: Document ID
            operation: Operation to apply
        """
        if doc_id not in self.documents:
            return
        
        async with self.locks[doc_id]:
            # Update document based on operation type
            doc = self.documents[doc_id]
            doc.last_modified = time.time()
            
            if operation.operation_type == OperationType.INSERT:
                if operation.position is not None and operation.text is not None:
                    doc.content = (
                        doc.content[:operation.position] + 
                        operation.text + 
                        doc.content[operation.position:]
                    )
            
            elif operation.operation_type == OperationType.DELETE:
                if operation.position is not None and operation.text is not None:
                    # Find the text to delete and remove it
                    start_pos = operation.position
                    end_pos = start_pos + len(operation.text)
                    doc.content = doc.content[:start_pos] + doc.content[end_pos:]
            
            elif operation.operation_type == OperationType.UPDATE:
                # For updating KD-Code settings
                if operation.text:
                    try:
                        settings_update = json.loads(operation.text)
                        doc.kd_code_settings.update(settings_update)
                    except json.JSONDecodeError:
                        pass  # Ignore invalid settings updates
            
            # Add operation to log
            operation.timestamp = time.time()
            doc.operations_log.append(operation)
            
            # Broadcast operation to all connected users
            await self.broadcast_to_document(
                doc_id,
                {
                    'type': operation.operation_type.value,
                    'operation': operation.to_dict(),
                    'timestamp': time.time()
                }
            )
    
    async def broadcast_to_document(self, doc_id: str, message: Dict[str, Any]):
        """
        Broadcast a message to all users in a document session
        
        Args:
            doc_id: Document ID
            message: Message to broadcast
        """
        if doc_id not in self.document_sessions:
            return
        
        message_json = json.dumps(message)
        
        # Send to all connected users in this document
        for user_id in self.document_sessions[doc_id]:
            if user_id in self.connections:
                try:
                    await self.connections[user_id].send(message_json)
                except websockets.exceptions.ConnectionClosed:
                    # Remove disconnected user
                    del self.connections[user_id]
    
    async def get_document_state(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a document
        
        Args:
            doc_id: Document ID
        
        Returns:
            Document state or None if document doesn't exist
        """
        if doc_id not in self.documents:
            return None
        
        doc = self.documents[doc_id]
        return {
            'doc_id': doc.doc_id,
            'title': doc.title,
            'content': doc.content,
            'created_at': doc.created_at,
            'last_modified': doc.last_modified,
            'owner_id': doc.owner_id,
            'participants': [asdict(user) for user in doc.participants],
            'kd_code_settings': doc.kd_code_settings,
            'operation_count': len(doc.operations_log)
        }
    
    def _generate_user_color(self, user_id: str) -> str:
        """
        Generate a consistent color for a user based on their ID
        
        Args:
            user_id: User ID
        
        Returns:
            Hex color string
        """
        # Use the first few characters of the user ID to generate a color
        hash_val = hash(user_id) % 0xFFFFFF
        return f"#{hash_val:06x}"
    
    async def send_chat_message(self, doc_id: str, user_id: str, message: str):
        """
        Send a chat message to all users in a document
        
        Args:
            doc_id: Document ID
            user_id: Sender's user ID
            message: Chat message
        """
        await self.broadcast_to_document(
            doc_id,
            {
                'type': OperationType.CHAT.value,
                'user_id': user_id,
                'message': message,
                'timestamp': time.time()
            }
        )
    
    async def update_user_selection(self, doc_id: str, user_id: str, start: int, end: int):
        """
        Update the text selection for a user
        
        Args:
            doc_id: Document ID
            user_id: User ID
            start: Selection start position
            end: Selection end position
        """
        await self.broadcast_to_document(
            doc_id,
            {
                'type': OperationType.SELECTION.value,
                'user_id': user_id,
                'selection': {'start': start, 'end': end},
                'timestamp': time.time()
            }
        )


# Global collaborative editor instance
collab_editor = CollaborativeEditor()


class CollaborationServer:
    """
    WebSocket server for handling collaborative editing sessions
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.editor = collab_editor
        self.websocket_server = None
    
    async def handle_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handle a new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        user_id = str(uuid.uuid4())
        self.editor.connections[user_id] = websocket
        
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
            if user_id in self.editor.connections:
                del self.editor.connections[user_id]
            
            # Remove user from any documents they were in
            for doc_id, session_users in self.editor.document_sessions.items():
                if user_id in session_users:
                    await self.editor.leave_document(doc_id, user_id)
    
    async def handle_message(self, user_id: str, data: Dict[str, Any]):
        """
        Handle incoming messages from clients
        
        Args:
            user_id: User ID of the sender
            data: Message data
        """
        msg_type = data.get('type')
        
        if msg_type == 'create_doc':
            title = data.get('title', 'Untitled')
            content = data.get('content', '')
            settings = data.get('settings')
            
            doc_id = await self.editor.create_document(title, user_id, content, settings)
            
            await self.editor.connections[user_id].send(json.dumps({
                'type': 'doc_created',
                'doc_id': doc_id
            }))
        
        elif msg_type == 'join_doc':
            doc_id = data.get('doc_id')
            username = data.get('username')
            
            success = await self.editor.join_document(doc_id, user_id, username)
            
            if success:
                # Send document state to new user
                state = await self.editor.get_document_state(doc_id)
                if state:
                    await self.editor.connections[user_id].send(json.dumps({
                        'type': 'doc_joined',
                        'state': state
                    }))
        
        elif msg_type == 'leave_doc':
            doc_id = data.get('doc_id')
            await self.editor.leave_document(doc_id, user_id)
        
        elif msg_type == 'operation':
            doc_id = data.get('doc_id')
            op_data = data.get('operation')
            
            if doc_id and op_data:
                try:
                    operation = Operation(
                        op_id=op_data['op_id'],
                        user_id=user_id,
                        operation_type=OperationType(op_data['operation_type']),
                        position=op_data.get('position'),
                        text=op_data.get('text')
                    )
                    
                    await self.editor.apply_operation(doc_id, operation)
                except (KeyError, ValueError):
                    await self.editor.connections[user_id].send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid operation data'
                    }))
        
        elif msg_type == 'chat':
            doc_id = data.get('doc_id')
            message = data.get('message')
            
            if doc_id and message:
                await self.editor.send_chat_message(doc_id, user_id, message)
        
        elif msg_type == 'selection':
            doc_id = data.get('doc_id')
            selection = data.get('selection', {})
            start = selection.get('start', 0)
            end = selection.get('end', 0)
            
            if doc_id:
                await self.editor.update_user_selection(doc_id, user_id, start, end)
    
    async def start_server(self):
        """Start the WebSocket server"""
        self.websocket_server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )
        print(f"Collaboration server started on {self.host}:{self.port}")
        
        # Keep the server running
        await self.websocket_server.wait_closed()
    
    def run_server(self):
        """Run the server in a separate thread"""
        def run():
            asyncio.run(self.start_server())
        
        server_thread = Thread(target=run, daemon=True)
        server_thread.start()
        return server_thread


# Functions for integration with the main application
async def create_collaborative_session(title: str, owner_id: str, initial_content: str = "") -> str:
    """
    Create a new collaborative editing session
    
    Args:
        title: Title of the session
        owner_id: Owner's user ID
        initial_content: Initial content for the KD-Code
    
    Returns:
        Session ID
    """
    return await collab_editor.create_document(title, owner_id, initial_content)


async def join_collaborative_session(session_id: str, user_id: str, username: str = None) -> bool:
    """
    Join a collaborative editing session
    
    Args:
        session_id: Session ID to join
        user_id: User ID joining
        username: Optional username
    
    Returns:
        True if successful, False otherwise
    """
    return await collab_editor.join_document(session_id, user_id, username)


async def send_operation_to_session(session_id: str, user_id: str, operation_type: str, 
                                  position: int = None, text: str = None):
    """
    Send an operation to a collaborative session
    
    Args:
        session_id: Session ID
        user_id: User ID performing the operation
        operation_type: Type of operation ('insert', 'delete', 'update')
        position: Position for the operation
        text: Text for the operation
    """
    operation = Operation(
        op_id=str(uuid.uuid4()),
        user_id=user_id,
        operation_type=OperationType(operation_type),
        position=position,
        text=text
    )
    
    await collab_editor.apply_operation(session_id, operation)


async def get_session_state(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current state of a collaborative session
    
    Args:
        session_id: Session ID
    
    Returns:
        Session state or None if session doesn't exist
    """
    return await collab_editor.get_document_state(session_id)


# Example usage
if __name__ == "__main__":
    import asyncio
    
    # Example of creating and using a collaborative session
    async def example():
        # Create a new collaborative session
        session_id = await create_collaborative_session(
            "My KD-Code Project", 
            "user123", 
            "Initial KD-Code content"
        )
        
        print(f"Created session: {session_id}")
        
        # Join the session
        joined = await join_collaborative_session(session_id, "user456", "Alice")
        print(f"Alice joined: {joined}")
        
        # Send an operation
        await send_operation_to_session(
            session_id, 
            "user123", 
            "insert", 
            position=5, 
            text=" collaborative"
        )
        
        # Get session state
        state = await get_session_state(session_id)
        if state:
            print(f"Session content: {state['content']}")
    
    # Run the example
    asyncio.run(example())