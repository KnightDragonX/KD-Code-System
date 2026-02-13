"""
Code Versioning and History System for KD-Code System
Manages versioning and history of KD-Codes throughout their lifecycle
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib
import os


class KDCodeVersionManager:
    """
    Manages versioning and history of KD-Codes
    """
    
    def __init__(self, db_path: str = "kd_codes_versions.db"):
        """
        Initialize the version manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables for versioning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create codes table with versioning support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                encoded_content TEXT,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                creator_id TEXT,
                parent_code_id TEXT,  -- For tracking code lineage
                metadata TEXT
            )
        ''')
        
        # Create version history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                encoded_content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creator_id TEXT,
                change_reason TEXT,
                FOREIGN KEY (code_id) REFERENCES codes (code_id)
            )
        ''')
        
        # Create code relationships table (for tracking derivatives, forks, etc.)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_code_id TEXT NOT NULL,
                child_code_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,  -- 'fork', 'derivative', 'revision', 'merge'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Create code tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                FOREIGN KEY (code_id) REFERENCES codes (code_id)
            )
        ''')
        
        # Create code history events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_history_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- 'created', 'updated', 'scanned', 'deleted', 'status_changed'
                event_data TEXT,  -- JSON string with event-specific data
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                performed_by TEXT,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (code_id) REFERENCES codes (code_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_new_code(self, content: str, creator_id: str = None, 
                       parent_code_id: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new KD-Code with version tracking
        
        Args:
            content: Content to encode in the KD-Code
            creator_id: ID of the user creating the code
            parent_code_id: ID of the parent code (if this is a derivative)
            metadata: Additional metadata for the code
        
        Returns:
            Code ID of the newly created code
        """
        code_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert the new code
        cursor.execute('''
            INSERT INTO codes (code_id, content, creator_id, parent_code_id, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (code_id, content, creator_id, parent_code_id, json.dumps(metadata) if metadata else None))
        
        # Create initial version entry
        cursor.execute('''
            INSERT INTO code_versions (code_id, version_number, content, creator_id, change_reason)
            VALUES (?, 1, ?, ?, 'Initial creation')
        ''', (code_id, content, creator_id))
        
        # Log creation event
        cursor.execute('''
            INSERT INTO code_history_events (code_id, event_type, performed_by)
            VALUES (?, 'created', ?)
        ''', (code_id, creator_id))
        
        conn.commit()
        conn.close()
        
        return code_id
    
    def update_code_content(self, code_id: str, new_content: str, 
                           performer_id: str = None, change_reason: str = None) -> bool:
        """
        Update the content of an existing code and create a new version
        
        Args:
            code_id: ID of the code to update
            new_content: New content for the code
            performer_id: ID of the user performing the update
            change_reason: Reason for the change
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current version
        cursor.execute('SELECT version FROM codes WHERE code_id = ?', (code_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False
        
        current_version = result[0]
        new_version = current_version + 1
        
        # Update the main code record
        cursor.execute('''
            UPDATE codes 
            SET content = ?, version = ?, updated_at = CURRENT_TIMESTAMP
            WHERE code_id = ?
        ''', (new_content, new_version, code_id))
        
        # Create new version entry
        cursor.execute('''
            INSERT INTO code_versions (code_id, version_number, content, creator_id, change_reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (code_id, new_version, new_content, performer_id, change_reason or 'Content update'))
        
        # Log update event
        event_data = json.dumps({
            'old_version': current_version,
            'new_version': new_version,
            'change_reason': change_reason
        })
        
        cursor.execute('''
            INSERT INTO code_history_events (code_id, event_type, event_data, performed_by)
            VALUES (?, 'updated', ?, ?)
        ''', (code_id, event_data, performer_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_code_history(self, code_id: str) -> List[Dict[str, Any]]:
        """
        Get the complete history of a code
        
        Args:
            code_id: ID of the code to get history for
        
        Returns:
            List of history events for the code
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_type, event_data, created_at, performed_by
            FROM code_history_events
            WHERE code_id = ?
            ORDER BY created_at DESC
        ''', (code_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for event_type, event_data, created_at, performed_by in rows:
            event = {
                'event_type': event_type,
                'created_at': created_at,
                'performed_by': performed_by
            }
            
            if event_data:
                try:
                    event['event_data'] = json.loads(event_data)
                except json.JSONDecodeError:
                    event['event_data'] = event_data
            
            history.append(event)
        
        return history
    
    def get_code_versions(self, code_id: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a code
        
        Args:
            code_id: ID of the code to get versions for
        
        Returns:
            List of code versions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT version_number, content, encoded_content, created_at, creator_id, change_reason
            FROM code_versions
            WHERE code_id = ?
            ORDER BY version_number ASC
        ''', (code_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        versions = []
        for version_num, content, encoded_content, created_at, creator_id, change_reason in rows:
            versions.append({
                'version_number': version_num,
                'content': content,
                'encoded_content': encoded_content,
                'created_at': created_at,
                'creator_id': creator_id,
                'change_reason': change_reason
            })
        
        return versions
    
    def get_code_at_version(self, code_id: str, version_number: int) -> Optional[Dict[str, Any]]:
        """
        Get the content of a code at a specific version
        
        Args:
            code_id: ID of the code
            version_number: Version number to retrieve
        
        Returns:
            Code content at the specified version, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT version_number, content, encoded_content, created_at, creator_id, change_reason
            FROM code_versions
            WHERE code_id = ? AND version_number = ?
        ''', (code_id, version_number))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'version_number': row[0],
            'content': row[1],
            'encoded_content': row[2],
            'created_at': row[3],
            'creator_id': row[4],
            'change_reason': row[5]
        }
    
    def fork_code(self, original_code_id: str, new_content: str = None, 
                 creator_id: str = None, fork_reason: str = None) -> str:
        """
        Create a fork of an existing code
        
        Args:
            original_code_id: ID of the code to fork
            new_content: New content for the fork (if different from original)
            creator_id: ID of the user creating the fork
            fork_reason: Reason for forking the code
        
        Returns:
            Code ID of the new forked code
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the original code content if new_content is not provided
        if new_content is None:
            cursor.execute('SELECT content FROM codes WHERE code_id = ?', (original_code_id,))
            result = cursor.fetchone()
            if result:
                new_content = result[0]
            else:
                conn.close()
                return None
        
        # Create the new forked code
        forked_code_id = self.create_new_code(
            content=new_content,
            creator_id=creator_id,
            parent_code_id=original_code_id,
            metadata={'forked_from': original_code_id, 'fork_reason': fork_reason}
        )
        
        # Create relationship record
        cursor.execute('''
            INSERT INTO code_relationships (parent_code_id, child_code_id, relationship_type, created_at, metadata)
            VALUES (?, ?, 'fork', CURRENT_TIMESTAMP, ?)
        ''', (original_code_id, forked_code_id, json.dumps({'reason': fork_reason})))
        
        # Log fork event
        cursor.execute('''
            INSERT INTO code_history_events (code_id, event_type, event_data, performed_by)
            VALUES (?, 'forked', ?, ?)
        ''', (forked_code_id, json.dumps({'original_code_id': original_code_id}), creator_id))
        
        conn.commit()
        conn.close()
        
        return forked_code_id
    
    def add_tag_to_code(self, code_id: str, tag_name: str, added_by: str = None) -> bool:
        """
        Add a tag to a code
        
        Args:
            code_id: ID of the code to tag
            tag_name: Tag to add
            added_by: User who added the tag
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO code_tags (code_id, tag_name, created_by)
                VALUES (?, ?, ?)
            ''', (code_id, tag_name, added_by))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def get_codes_by_tag(self, tag_name: str) -> List[Dict[str, Any]]:
        """
        Get all codes with a specific tag
        
        Args:
            tag_name: Tag to search for
        
        Returns:
            List of codes with the specified tag
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.code_id, c.content, c.version, c.created_at, c.creator_id
            FROM codes c
            JOIN code_tags ct ON c.code_id = ct.code_id
            WHERE ct.tag_name = ?
            ORDER BY c.created_at DESC
        ''', (tag_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for code_id, content, version, created_at, creator_id in rows:
            codes.append({
                'code_id': code_id,
                'content': content[:50] + "..." if len(content) > 50 else content,  # Truncate for display
                'version': version,
                'created_at': created_at,
                'creator_id': creator_id
            })
        
        return codes
    
    def get_derivative_codes(self, parent_code_id: str) -> List[Dict[str, Any]]:
        """
        Get all codes that are derivatives of a parent code
        
        Args:
            parent_code_id: ID of the parent code
        
        Returns:
            List of derivative codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cr.child_code_id, c.content, c.version, c.created_at, c.creator_id
            FROM code_relationships cr
            JOIN codes c ON cr.child_code_id = c.code_id
            WHERE cr.parent_code_id = ?
            ORDER BY c.created_at DESC
        ''', (parent_code_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        derivatives = []
        for code_id, content, version, created_at, creator_id in rows:
            derivatives.append({
                'code_id': code_id,
                'content': content[:50] + "..." if len(content) > 50 else content,
                'version': version,
                'created_at': created_at,
                'creator_id': creator_id
            })
        
        return derivatives
    
    def get_code_lineage(self, code_id: str) -> Dict[str, Any]:
        """
        Get the complete lineage of a code (ancestors and descendants)
        
        Args:
            code_id: ID of the code to get lineage for
        
        Returns:
            Dictionary with ancestors and descendants
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get ancestors (recursive)
        ancestors = []
        current_parent = code_id
        
        while True:
            cursor.execute('''
                SELECT parent_code_id FROM codes WHERE code_id = ?
            ''', (current_parent,))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                break
            
            parent_id = result[0]
            cursor.execute('''
                SELECT code_id, content, version, created_at, creator_id
                FROM codes WHERE code_id = ?
            ''', (parent_id,))
            parent_data = cursor.fetchone()
            
            if parent_data:
                ancestors.append({
                    'code_id': parent_data[0],
                    'content': parent_data[1][:50] + "..." if len(parent_data[1]) > 50 else parent_data[1],
                    'version': parent_data[2],
                    'created_at': parent_data[3],
                    'creator_id': parent_data[4]
                })
                current_parent = parent_id
            else:
                break
        
        # Get descendants
        descendants = self.get_derivative_codes(code_id)
        
        conn.close()
        
        return {
            'ancestors': ancestors,
            'descendants': descendants
        }
    
    def compare_versions(self, code_id: str, version1: int, version2: int) -> Dict[str, Any]:
        """
        Compare two versions of a code
        
        Args:
            code_id: ID of the code
            version1: First version to compare
            version2: Second version to compare
        
        Returns:
            Comparison results
        """
        v1_data = self.get_code_at_version(code_id, version1)
        v2_data = self.get_code_at_version(code_id, version2)
        
        if not v1_data or not v2_data:
            return {'error': 'One or both versions not found'}
        
        # Simple text comparison
        content1 = v1_data['content']
        content2 = v2_data['content']
        
        # Find differences
        diff = self._compute_diff(content1, content2)
        
        return {
            'version1': v1_data,
            'version2': v2_data,
            'differences': diff,
            'is_different': content1 != content2
        }
    
    def _compute_diff(self, text1: str, text2: str) -> List[Dict[str, Any]]:
        """
        Compute differences between two texts
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            List of differences
        """
        # This is a simplified diff algorithm
        # In a real implementation, you might use a more sophisticated diff algorithm
        if text1 == text2:
            return []
        
        # For now, return a simple difference indication
        return [{
            'type': 'content_change',
            'position': 0,
            'old_value': text1,
            'new_value': text2
        }]


# Global version manager instance
version_manager = KDCodeVersionManager()


def create_versioned_code(content: str, creator_id: str = None, 
                         parent_code_id: str = None, metadata: Dict[str, Any] = None) -> str:
    """
    Create a new versioned KD-Code
    
    Args:
        content: Content to encode
        creator_id: ID of the creator
        parent_code_id: Parent code ID (if this is a derivative)
        metadata: Additional metadata
    
    Returns:
        Code ID of the created code
    """
    return version_manager.create_new_code(content, creator_id, parent_code_id, metadata)


def update_code_version(code_id: str, new_content: str, performer_id: str = None, 
                       change_reason: str = None) -> bool:
    """
    Update a code creating a new version
    
    Args:
        code_id: ID of the code to update
        new_content: New content for the code
        performer_id: ID of the user performing the update
        change_reason: Reason for the change
    
    Returns:
        True if successful, False otherwise
    """
    return version_manager.update_code_content(code_id, new_content, performer_id, change_reason)


def get_code_history(code_id: str) -> List[Dict[str, Any]]:
    """
    Get history of a code
    
    Args:
        code_id: ID of the code
    
    Returns:
        List of history events
    """
    return version_manager.get_code_history(code_id)


def get_code_versions(code_id: str) -> List[Dict[str, Any]]:
    """
    Get all versions of a code
    
    Args:
        code_id: ID of the code
    
    Returns:
        List of code versions
    """
    return version_manager.get_code_versions(code_id)


def get_code_at_version(code_id: str, version_number: int) -> Optional[Dict[str, Any]]:
    """
    Get a specific version of a code
    
    Args:
        code_id: ID of the code
        version_number: Version number to retrieve
    
    Returns:
        Code content at the specified version
    """
    return version_manager.get_code_at_version(code_id, version_number)


def fork_code(original_code_id: str, new_content: str = None, 
             creator_id: str = None, fork_reason: str = None) -> str:
    """
    Create a fork of an existing code
    
    Args:
        original_code_id: ID of the code to fork
        new_content: New content for the fork
        creator_id: ID of the creator
        fork_reason: Reason for forking
    
    Returns:
        Code ID of the forked code
    """
    return version_manager.fork_code(original_code_id, new_content, creator_id, fork_reason)


def add_tag_to_code(code_id: str, tag_name: str, added_by: str = None) -> bool:
    """
    Add a tag to a code
    
    Args:
        code_id: ID of the code
        tag_name: Tag to add
        added_by: User who added the tag
    
    Returns:
        True if successful, False otherwise
    """
    return version_manager.add_tag_to_code(code_id, tag_name, added_by)


def get_codes_by_tag(tag_name: str) -> List[Dict[str, Any]]:
    """
    Get codes by tag
    
    Args:
        tag_name: Tag to search for
    
    Returns:
        List of codes with the tag
    """
    return version_manager.get_codes_by_tag(tag_name)


def get_derivative_codes(parent_code_id: str) -> List[Dict[str, Any]]:
    """
    Get derivative codes of a parent code
    
    Args:
        parent_code_id: ID of the parent code
    
    Returns:
        List of derivative codes
    """
    return version_manager.get_derivative_codes(parent_code_id)


def get_code_lineage(code_id: str) -> Dict[str, Any]:
    """
    Get the lineage of a code (ancestors and descendants)
    
    Args:
        code_id: ID of the code
    
    Returns:
        Dictionary with ancestors and descendants
    """
    return version_manager.get_code_lineage(code_id)


def compare_code_versions(code_id: str, version1: int, version2: int) -> Dict[str, Any]:
    """
    Compare two versions of a code
    
    Args:
        code_id: ID of the code
        version1: First version to compare
        version2: Second version to compare
    
    Returns:
        Comparison results
    """
    return version_manager.compare_versions(code_id, version1, version2)


# Example usage
if __name__ == "__main__":
    # Example of using the versioning system
    print("Initializing KD-Code versioning system...")
    
    # Create a new code
    code_id = create_versioned_code("Initial version of my KD-Code", creator_id="user123")
    print(f"Created code with ID: {code_id}")
    
    # Update the code to create a new version
    success = update_code_version(code_id, "Updated version of my KD-Code", 
                                 performer_id="user123", change_reason="Content improvement")
    print(f"Updated code: {success}")
    
    # Get all versions of the code
    versions = get_code_versions(code_id)
    print(f"Number of versions: {len(versions)}")
    
    # Get the history of the code
    history = get_code_history(code_id)
    print(f"History events: {len(history)}")
    
    # Fork the code
    forked_code_id = fork_code(code_id, new_content="Forked version with modifications", 
                              creator_id="user456", fork_reason="Customization needed")
    print(f"Forked code with ID: {forked_code_id}")
    
    # Add a tag to the original code
    tag_success = add_tag_to_code(code_id, "important", added_by="user123")
    print(f"Added tag to code: {tag_success}")
    
    # Get codes by tag
    tagged_codes = get_codes_by_tag("important")
    print(f"Codes with 'important' tag: {len(tagged_codes)}")
    
    # Get lineage
    lineage = get_code_lineage(code_id)
    print(f"Original code has {len(lineage['ancestors'])} ancestors and {len(lineage['descendants'])} descendants")
    
    # Compare versions
    comparison = compare_code_versions(code_id, 1, 2)
    print(f"Are versions 1 and 2 different? {comparison.get('is_different', False)}")