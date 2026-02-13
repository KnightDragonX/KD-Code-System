"""
Code Lifecycle Management System for KD-Code System
Manages the complete lifecycle of KD-Codes from creation to archival
"""

import json
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import hashlib
import logging


class CodeStatus(Enum):
    """Status of a KD-Code in its lifecycle"""
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ARCHIVED = "archived"
    SCANNED = "scanned"


class CodeLifecycleManager:
    """
    Manages the complete lifecycle of KD-Codes
    """
    
    def __init__(self, db_path: str = "kd_codes_lifecycle.db"):
        """
        Initialize the lifecycle manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                encoded_content TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_scanned_at TIMESTAMP,
                scan_count INTEGER DEFAULT 0,
                creator_id TEXT,
                tags TEXT,
                metadata TEXT,
                access_key TEXT
            )
        ''')
        
        # Create scan history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scanner_ip TEXT,
                scanner_user_agent TEXT,
                result TEXT,
                FOREIGN KEY (code_id) REFERENCES codes (code_id)
            )
        ''')
        
        # Create access logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                action TEXT NOT NULL,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                performer_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (code_id) REFERENCES codes (code_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_code(self, content: str, creator_id: str = None, expires_in_days: int = None, 
                   tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """
        Create a new KD-Code with lifecycle tracking
        
        Args:
            content: Content to encode in the KD-Code
            creator_id: ID of the user creating the code
            expires_in_days: Number of days until expiration (None for no expiration)
            tags: List of tags for categorization
            metadata: Additional metadata for the code
        
        Returns:
            Code ID
        """
        code_id = str(uuid.uuid4())
        access_key = hashlib.sha256(f"{code_id}_{content}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Calculate expiration date if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO codes 
            (code_id, content, status, created_at, expires_at, creator_id, tags, metadata, access_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code_id, content, CodeStatus.ACTIVE.value, 
            datetime.now().isoformat(), 
            expires_at.isoformat() if expires_at else None,
            creator_id, 
            json.dumps(tags) if tags else None,
            json.dumps(metadata) if metadata else None,
            access_key
        ))
        
        # Log the creation event
        cursor.execute('''
            INSERT INTO access_logs (code_id, action, performer_id)
            VALUES (?, ?, ?)
        ''', (code_id, 'create', creator_id))
        
        conn.commit()
        conn.close()
        
        return code_id
    
    def get_code_info(self, code_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific code
        
        Args:
            code_id: ID of the code to retrieve
        
        Returns:
            Code information or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code_id, content, status, created_at, expires_at, 
                   last_scanned_at, scan_count, creator_id, tags, metadata
            FROM codes WHERE code_id = ?
        ''', (code_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'code_id': row[0],
            'content': row[1],
            'status': row[2],
            'created_at': row[3],
            'expires_at': row[4],
            'last_scanned_at': row[5],
            'scan_count': row[6],
            'creator_id': row[7],
            'tags': json.loads(row[8]) if row[8] else [],
            'metadata': json.loads(row[9]) if row[9] else {}
        }
    
    def update_code_status(self, code_id: str, new_status: CodeStatus, reason: str = None) -> bool:
        """
        Update the status of a code
        
        Args:
            code_id: ID of the code to update
            new_status: New status for the code
            reason: Reason for the status change (optional)
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update status
        cursor.execute('''
            UPDATE codes SET status = ? WHERE code_id = ?
        ''', (new_status.value, code_id))
        
        if cursor.rowcount > 0:
            # Log the status change
            action_desc = f"status_change_to_{new_status.value}"
            if reason:
                action_desc += f"_reason_{reason}"
            
            cursor.execute('''
                INSERT INTO access_logs (code_id, action)
                VALUES (?, ?)
            ''', (code_id, action_desc))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def record_scan(self, code_id: str, scanner_ip: str = None, 
                   scanner_user_agent: str = None, result: str = None) -> bool:
        """
        Record a scan event for a code
        
        Args:
            code_id: ID of the code being scanned
            scanner_ip: IP address of the scanner
            scanner_user_agent: User agent of the scanner
            result: Result of the scan
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update scan count and last scanned time
        cursor.execute('''
            UPDATE codes 
            SET scan_count = scan_count + 1, last_scanned_at = ?
            WHERE code_id = ?
        ''', (datetime.now().isoformat(), code_id))
        
        if cursor.rowcount > 0:
            # Insert scan history record
            cursor.execute('''
                INSERT INTO scan_history (code_id, scanned_at, scanner_ip, scanner_user_agent, result)
                VALUES (?, ?, ?, ?, ?)
            ''', (code_id, datetime.now().isoformat(), scanner_ip, scanner_user_agent, result))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def get_scan_history(self, code_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get scan history for a code
        
        Args:
            code_id: ID of the code
            limit: Maximum number of records to return
        
        Returns:
            List of scan history records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT scanned_at, scanner_ip, scanner_user_agent, result
            FROM scan_history
            WHERE code_id = ?
            ORDER BY scanned_at DESC
            LIMIT ?
        ''', (code_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'scanned_at': row[0],
                'scanner_ip': row[1],
                'scanner_user_agent': row[2],
                'result': row[3]
            }
            for row in rows
        ]
    
    def get_codes_by_creator(self, creator_id: str, status: CodeStatus = None) -> List[Dict[str, Any]]:
        """
        Get all codes created by a specific user
        
        Args:
            creator_id: ID of the creator
            status: Optional status filter
        
        Returns:
            List of codes created by the user
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT code_id, content, status, created_at, expires_at, scan_count FROM codes WHERE creator_id = ?"
        params = [creator_id]
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'code_id': row[0],
                'content': row[1][:50] + "..." if len(row[1]) > 50 else row[1],  # Truncate content
                'status': row[2],
                'created_at': row[3],
                'expires_at': row[4],
                'scan_count': row[5]
            }
            for row in rows
        ]
    
    def get_expired_codes(self) -> List[str]:
        """
        Get all codes that have expired
        
        Returns:
            List of expired code IDs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code_id FROM codes 
            WHERE expires_at IS NOT NULL 
            AND expires_at < ? 
            AND status = ?
        ''', (datetime.now().isoformat(), CodeStatus.ACTIVE.value))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def cleanup_expired_codes(self, dry_run: bool = False) -> int:
        """
        Automatically expire codes that have passed their expiration date
        
        Args:
            dry_run: If True, only count how many would be affected
        
        Returns:
            Number of codes that were expired
        """
        expired_codes = self.get_expired_codes()
        
        if not dry_run:
            for code_id in expired_codes:
                self.update_code_status(code_id, CodeStatus.EXPIRED, "Automatic expiration")
        
        return len(expired_codes)
    
    def search_codes(self, query: str = None, tags: List[str] = None, 
                    creator_id: str = None, status: CodeStatus = None) -> List[Dict[str, Any]]:
        """
        Search for codes based on various criteria
        
        Args:
            query: Text query to search in content
            tags: Tags to filter by
            creator_id: Creator ID to filter by
            status: Status to filter by
        
        Returns:
            List of matching codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        base_query = "SELECT code_id, content, status, created_at, expires_at, scan_count, creator_id, tags FROM codes WHERE 1=1"
        params = []
        
        if query:
            base_query += " AND content LIKE ?"
            params.append(f"%{query}%")
        
        if creator_id:
            base_query += " AND creator_id = ?"
            params.append(creator_id)
        
        if status:
            base_query += " AND status = ?"
            params.append(status.value)
        
        if tags:
            # This is a simplified tag search - in a real implementation you'd want more sophisticated tag matching
            base_query += " AND ("
            tag_conditions = []
            for i, tag in enumerate(tags):
                tag_conditions.append(f"tags LIKE ?")
                params.append(f"%{tag}%")
            base_query += " OR ".join(tag_conditions) + ")"
        
        base_query += " ORDER BY created_at DESC"
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'code_id': row[0],
                'content': row[1][:50] + "..." if len(row[1]) > 50 else row[1],  # Truncate content
                'status': row[2],
                'created_at': row[3],
                'expires_at': row[4],
                'scan_count': row[5],
                'creator_id': row[6],
                'tags': json.loads(row[7]) if row[7] else []
            }
            for row in rows
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lifecycle statistics
        
        Returns:
            Statistics about code lifecycle
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total codes
        cursor.execute("SELECT COUNT(*) FROM codes")
        total_codes = cursor.fetchone()[0]
        
        # Codes by status
        cursor.execute("SELECT status, COUNT(*) FROM codes GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        # Total scans
        cursor.execute("SELECT SUM(scan_count) FROM codes")
        total_scans = cursor.fetchone()[0] or 0
        
        # Recently created codes (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM codes WHERE created_at > ?", (week_ago,))
        recent_codes = cursor.fetchone()[0]
        
        # Recently scanned codes (last 7 days)
        cursor.execute("""
            SELECT COUNT(DISTINCT code_id) FROM scan_history 
            WHERE scanned_at > ?
        """, (week_ago,))
        recently_scanned = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_codes': total_codes,
            'status_distribution': status_counts,
            'total_scans': total_scans,
            'recently_created': recent_codes,
            'recently_scanned': recently_scanned,
            'active_codes': status_counts.get(CodeStatus.ACTIVE.value, 0),
            'expired_codes': status_counts.get(CodeStatus.EXPIRED.value, 0),
            'revoked_codes': status_counts.get(CodeStatus.REVOKED.value, 0)
        }


# Global lifecycle manager instance
lifecycle_manager = CodeLifecycleManager()


def initialize_lifecycle_management(db_path: str = "kd_codes_lifecycle.db"):
    """
    Initialize the code lifecycle management system
    
    Args:
        db_path: Path to the database file
    """
    global lifecycle_manager
    lifecycle_manager = CodeLifecycleManager(db_path)


def create_lifecycle_tracked_code(content: str, creator_id: str = None, 
                                expires_in_days: int = None, tags: List[str] = None, 
                                metadata: Dict[str, Any] = None) -> str:
    """
    Create a new KD-Code with lifecycle tracking
    
    Args:
        content: Content to encode
        creator_id: ID of the creator
        expires_in_days: Days until expiration
        tags: Tags for categorization
        metadata: Additional metadata
    
    Returns:
        Code ID
    """
    return lifecycle_manager.create_code(content, creator_id, expires_in_days, tags, metadata)


def get_code_lifecycle_info(code_id: str) -> Optional[Dict[str, Any]]:
    """
    Get lifecycle information for a code
    
    Args:
        code_id: ID of the code
    
    Returns:
        Code lifecycle information or None if not found
    """
    return lifecycle_manager.get_code_info(code_id)


def update_code_lifecycle_status(code_id: str, new_status: CodeStatus, reason: str = None) -> bool:
    """
    Update the lifecycle status of a code
    
    Args:
        code_id: ID of the code
        new_status: New status
        reason: Reason for status change
    
    Returns:
        True if successful, False otherwise
    """
    return lifecycle_manager.update_code_status(code_id, new_status, reason)


def record_code_scan_event(code_id: str, scanner_ip: str = None, 
                         scanner_user_agent: str = None, result: str = None) -> bool:
    """
    Record a scan event in the lifecycle
    
    Args:
        code_id: ID of the code being scanned
        scanner_ip: IP address of scanner
        scanner_user_agent: User agent of scanner
        result: Scan result
    
    Returns:
        True if successful, False otherwise
    """
    return lifecycle_manager.record_scan(code_id, scanner_ip, scanner_user_agent, result)


def get_code_scan_history(code_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get scan history for a code
    
    Args:
        code_id: ID of the code
        limit: Maximum records to return
    
    Returns:
        List of scan history records
    """
    return lifecycle_manager.get_scan_history(code_id, limit)


def get_user_codes(creator_id: str, status: CodeStatus = None) -> List[Dict[str, Any]]:
    """
    Get codes created by a user
    
    Args:
        creator_id: ID of the creator
        status: Optional status filter
    
    Returns:
        List of user's codes
    """
    return lifecycle_manager.get_codes_by_creator(creator_id, status)


def search_lifecycle_codes(query: str = None, tags: List[str] = None, 
                         creator_id: str = None, status: CodeStatus = None) -> List[Dict[str, Any]]:
    """
    Search codes in the lifecycle system
    
    Args:
        query: Text query
        tags: Tags to filter by
        creator_id: Creator ID to filter by
        status: Status to filter by
    
    Returns:
        List of matching codes
    """
    return lifecycle_manager.search_codes(query, tags, creator_id, status)


def get_lifecycle_statistics() -> Dict[str, Any]:
    """
    Get lifecycle management statistics
    
    Returns:
        Statistics about code lifecycle
    """
    return lifecycle_manager.get_statistics()


def cleanup_expired_codes(dry_run: bool = False) -> int:
    """
    Cleanup expired codes
    
    Args:
        dry_run: If True, only count how many would be affected
    
    Returns:
        Number of codes that were expired
    """
    return lifecycle_manager.cleanup_expired_codes(dry_run)


# Example usage
if __name__ == "__main__":
    # Initialize the lifecycle management system
    initialize_lifecycle_management()
    
    # Create a test code
    code_id = create_lifecycle_tracked_code(
        "Test content for lifecycle management",
        creator_id="user123",
        expires_in_days=30,
        tags=["test", "important"],
        metadata={"category": "demo", "priority": "high"}
    )
    
    print(f"Created code with ID: {code_id}")
    
    # Get code information
    info = get_code_lifecycle_info(code_id)
    print(f"Code info: {info}")
    
    # Record a scan event
    success = record_code_scan_event(code_id, scanner_ip="192.168.1.100", result="Success")
    print(f"Recorded scan: {success}")
    
    # Get scan history
    history = get_code_scan_history(code_id)
    print(f"Scan history: {history}")
    
    # Get user codes
    user_codes = get_user_codes("user123")
    print(f"User codes: {user_codes}")
    
    # Get lifecycle statistics
    stats = get_lifecycle_statistics()
    print(f"Lifecycle stats: {stats}")