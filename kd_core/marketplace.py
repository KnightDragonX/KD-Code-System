"""
KD-Code Marketplace Module
Enables sharing and discovery of KD-Codes in a marketplace
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import os
import logging
from enum import Enum


class CodeCategory(Enum):
    """Categories for KD-Codes in the marketplace"""
    GENERAL = "general"
    BUSINESS = "business"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    SECURITY = "security"
    ARTISTIC = "artistic"
    TECHNICAL = "technical"
    PROMOTIONAL = "promotional"


class CodeVisibility(Enum):
    """Visibility settings for shared codes"""
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"
    SHARED = "shared"


class KDCodeMarketplace:
    """
    Marketplace for sharing and discovering KD-Codes
    """
    
    def __init__(self, db_path: str = "kd_codes_marketplace.db"):
        """
        Initialize the marketplace
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_database()
        self.logger = logging.getLogger(__name__)
    
    def init_database(self):
        """Initialize the marketplace database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create marketplace codes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marketplace_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                encoded_content TEXT NOT NULL,
                original_content TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                visibility TEXT DEFAULT 'public',
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                view_count INTEGER DEFAULT 0,
                download_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0,
                license_type TEXT DEFAULT 'CC0',
                expiration_date TIMESTAMP,
                is_featured BOOLEAN DEFAULT FALSE,
                is_verified BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create user favorites table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                code_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code_id) REFERENCES marketplace_codes (code_id)
            )
        ''')
        
        # Create user ratings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                code_id TEXT NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                review TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code_id) REFERENCES marketplace_codes (code_id)
            )
        ''')
        
        # Create code sharing permissions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_sharing_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                permission_type TEXT NOT NULL,  -- 'view', 'download', 'modify'
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (code_id) REFERENCES marketplace_codes (code_id)
            )
        ''')
        
        # Create code analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS code_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- 'view', 'download', 'scan', 'share'
                user_id TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (code_id) REFERENCES marketplace_codes (code_id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_category ON marketplace_codes(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_visibility ON marketplace_codes(visibility)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_creator ON marketplace_codes(creator_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_featured ON marketplace_codes(is_featured)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_code_rating ON marketplace_codes(rating)')
        
        conn.commit()
        conn.close()
    
    def publish_code_to_marketplace(self, 
                                  code_id: str, 
                                  title: str, 
                                  description: str = None,
                                  category: CodeCategory = CodeCategory.GENERAL,
                                  visibility: CodeVisibility = CodeVisibility.PUBLIC,
                                  tags: List[str] = None,
                                  license_type: str = 'CC0',
                                  expiration_days: int = None) -> bool:
        """
        Publish a KD-Code to the marketplace
        
        Args:
            code_id: ID of the existing code to publish
            title: Title for the marketplace listing
            description: Description for the marketplace listing
            category: Category for the code
            visibility: Visibility setting for the code
            tags: List of tags for discovery
            license_type: License type for the code
            expiration_days: Days until the listing expires (None for no expiration)
        
        Returns:
            True if successful, False otherwise
        """
        # In a real implementation, we would fetch the existing code from the main codes table
        # For this example, we'll assume the code exists and we're just creating a marketplace listing
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if code already exists in marketplace
        cursor.execute('SELECT code_id FROM marketplace_codes WHERE code_id = ?', (code_id,))
        if cursor.fetchone():
            conn.close()
            return False  # Already published
        
        # Calculate expiration date if specified
        expiration_date = None
        if expiration_days:
            expiration_date = (datetime.now() + timedelta(days=expiration_days)).isoformat()
        
        try:
            cursor.execute('''
                INSERT INTO marketplace_codes 
                (code_id, title, description, encoded_content, original_content, 
                 creator_id, category, visibility, tags, license_type, expiration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                code_id, title, description, "", "",  # encoded/original content would come from main codes table
                "anonymous", category.value, visibility.value,
                json.dumps(tags) if tags else None,
                license_type, expiration_date
            ))
            
            conn.commit()
            conn.close()
            self.logger.info(f"Published code {code_id} to marketplace")
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error publishing code to marketplace: {e}")
            conn.close()
            return False
    
    def get_marketplace_codes(self, 
                            category: CodeCategory = None, 
                            search_query: str = None,
                            tags: List[str] = None,
                            limit: int = 20,
                            offset: int = 0,
                            sort_by: str = 'created_at',
                            sort_order: str = 'DESC') -> List[Dict[str, Any]]:
        """
        Get codes from the marketplace with filtering and pagination
        
        Args:
            category: Category to filter by
            search_query: Text to search in title/description
            tags: Tags to filter by
            limit: Number of results to return
            offset: Offset for pagination
            sort_by: Field to sort by ('created_at', 'rating', 'view_count', 'download_count')
            sort_order: Sort order ('ASC' or 'DESC')
        
        Returns:
            List of marketplace codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query with filters
        query = '''
            SELECT code_id, title, description, creator_id, category, 
                   created_at, view_count, download_count, rating, rating_count
            FROM marketplace_codes
            WHERE visibility = 'public'
        '''
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category.value)
        
        if search_query:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        
        if tags:
            # This is a simplified tag search - in a real implementation you'd want more sophisticated tag matching
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            query += f" AND ({tag_conditions})"
            params.extend([f"%{tag}%" for tag in tags])
        
        # Add sorting
        valid_sort_fields = ['created_at', 'rating', 'view_count', 'download_count']
        if sort_by not in valid_sort_fields:
            sort_by = 'created_at'
        
        valid_sort_orders = ['ASC', 'DESC']
        if sort_order.upper() not in valid_sort_orders:
            sort_order = 'DESC'
        
        query += f" ORDER BY {sort_by} {sort_order}"
        
        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for code_id, title, description, creator_id, category, created_at, view_count, download_count, rating, rating_count in rows:
            codes.append({
                'code_id': code_id,
                'title': title,
                'description': description,
                'creator_id': creator_id,
                'category': category,
                'created_at': created_at,
                'view_count': view_count,
                'download_count': download_count,
                'rating': rating,
                'rating_count': rating_count
            })
        
        return codes
    
    def get_code_details(self, code_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a marketplace code
        
        Args:
            code_id: ID of the code to retrieve
        
        Returns:
            Code details or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code_id, title, description, creator_id, category, 
                   visibility, tags, created_at, view_count, download_count, 
                   rating, rating_count, license_type, expiration_date
            FROM marketplace_codes
            WHERE code_id = ?
        ''', (code_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'code_id': row[0],
            'title': row[1],
            'description': row[2],
            'creator_id': row[3],
            'category': row[4],
            'visibility': row[5],
            'tags': json.loads(row[6]) if row[6] else [],
            'created_at': row[7],
            'view_count': row[8],
            'download_count': row[9],
            'rating': row[10],
            'rating_count': row[11],
            'license_type': row[12],
            'expiration_date': row[13]
        }
    
    def increment_view_count(self, code_id: str):
        """
        Increment the view count for a code
        
        Args:
            code_id: ID of the code to increment views for
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE marketplace_codes
            SET view_count = view_count + 1
            WHERE code_id = ?
        ''', (code_id,))
        
        conn.commit()
        conn.close()
    
    def increment_download_count(self, code_id: str):
        """
        Increment the download count for a code
        
        Args:
            code_id: ID of the code to increment downloads for
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE marketplace_codes
            SET download_count = download_count + 1
            WHERE code_id = ?
        ''', (code_id,))
        
        conn.commit()
        conn.close()
    
    def add_user_rating(self, code_id: str, user_id: str, rating: int, review: str = None) -> bool:
        """
        Add a user rating for a code
        
        Args:
            code_id: ID of the code to rate
            user_id: ID of the user rating
            rating: Rating (1-5)
            review: Optional review text
        
        Returns:
            True if successful, False otherwise
        """
        if rating < 1 or rating > 5:
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user has already rated this code
            cursor.execute('''
                SELECT id FROM user_ratings WHERE user_id = ? AND code_id = ?
            ''', (user_id, code_id))
            
            if cursor.fetchone():
                # Update existing rating
                cursor.execute('''
                    UPDATE user_ratings
                    SET rating = ?, review = ?, created_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND code_id = ?
                ''', (rating, review, user_id, code_id))
            else:
                # Insert new rating
                cursor.execute('''
                    INSERT INTO user_ratings (user_id, code_id, rating, review)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, code_id, rating, review))
            
            # Recalculate average rating
            cursor.execute('''
                SELECT AVG(rating), COUNT(*) FROM user_ratings WHERE code_id = ?
            ''', (code_id,))
            
            avg_rating, count = cursor.fetchone()
            avg_rating = avg_rating or 0.0
            
            # Update the code's rating
            cursor.execute('''
                UPDATE marketplace_codes
                SET rating = ?, rating_count = ?
                WHERE code_id = ?
            ''', (avg_rating, count, code_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding user rating: {e}")
            conn.close()
            return False
    
    def add_to_favorites(self, code_id: str, user_id: str) -> bool:
        """
        Add a code to a user's favorites
        
        Args:
            code_id: ID of the code to favorite
            user_id: ID of the user favoriting
        
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if already favorited
            cursor.execute('''
                SELECT id FROM user_favorites WHERE user_id = ? AND code_id = ?
            ''', (user_id, code_id))
            
            if cursor.fetchone():
                conn.close()
                return False  # Already favorited
            
            # Add to favorites
            cursor.execute('''
                INSERT INTO user_favorites (user_id, code_id)
                VALUES (?, ?)
            ''', (user_id, code_id))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            self.logger.error(f"Error adding to favorites: {e}")
            conn.close()
            return False
    
    def get_user_favorites(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get a user's favorite codes
        
        Args:
            user_id: ID of the user
            limit: Number of results to return
            offset: Offset for pagination
        
        Returns:
            List of favorite codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT mc.code_id, mc.title, mc.description, mc.creator_id, 
                   mc.category, mc.created_at, mc.view_count, mc.download_count,
                   mc.rating, mc.rating_count
            FROM user_favorites uf
            JOIN marketplace_codes mc ON uf.code_id = mc.code_id
            WHERE uf.user_id = ?
            ORDER BY uf.added_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        favorites = []
        for code_id, title, description, creator_id, category, created_at, view_count, download_count, rating, rating_count in rows:
            favorites.append({
                'code_id': code_id,
                'title': title,
                'description': description,
                'creator_id': creator_id,
                'category': category,
                'created_at': created_at,
                'view_count': view_count,
                'download_count': download_count,
                'rating': rating,
                'rating_count': rating_count
            })
        
        return favorites
    
    def get_top_rated_codes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the top-rated codes in the marketplace
        
        Args:
            limit: Number of codes to return
        
        Returns:
            List of top-rated codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code_id, title, description, creator_id, category, 
                   created_at, view_count, download_count, rating, rating_count
            FROM marketplace_codes
            WHERE visibility = 'public' AND rating_count >= 3
            ORDER BY rating DESC, rating_count DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for code_id, title, description, creator_id, category, created_at, view_count, download_count, rating, rating_count in rows:
            codes.append({
                'code_id': code_id,
                'title': title,
                'description': description,
                'creator_id': creator_id,
                'category': category,
                'created_at': created_at,
                'view_count': view_count,
                'download_count': download_count,
                'rating': rating,
                'rating_count': rating_count
            })
        
        return codes
    
    def get_most_popular_codes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most popular codes based on download/view counts
        
        Args:
            limit: Number of codes to return
        
        Returns:
            List of most popular codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code_id, title, description, creator_id, category, 
                   created_at, view_count, download_count, rating, rating_count
            FROM marketplace_codes
            WHERE visibility = 'public'
            ORDER BY (download_count * 2 + view_count) DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for code_id, title, description, creator_id, category, created_at, view_count, download_count, rating, rating_count in rows:
            codes.append({
                'code_id': code_id,
                'title': title,
                'description': description,
                'creator_id': creator_id,
                'category': category,
                'created_at': created_at,
                'view_count': view_count,
                'download_count': download_count,
                'rating': rating,
                'rating_count': rating_count
            })
        
        return codes
    
    def get_featured_codes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get featured codes in the marketplace
        
        Args:
            limit: Number of codes to return
        
        Returns:
            List of featured codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT code_id, title, description, creator_id, category, 
                   created_at, view_count, download_count, rating, rating_count
            FROM marketplace_codes
            WHERE visibility = 'public' AND is_featured = 1
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for code_id, title, description, creator_id, category, created_at, view_count, download_count, rating, rating_count in rows:
            codes.append({
                'code_id': code_id,
                'title': title,
                'description': description,
                'creator_id': creator_id,
                'category': category,
                'created_at': created_at,
                'view_count': view_count,
                'download_count': download_count,
                'rating': rating,
                'rating_count': rating_count
            })
        
        return codes
    
    def search_codes(self, query: str, category: CodeCategory = None, 
                    tags: List[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for codes in the marketplace
        
        Args:
            query: Search query string
            category: Category to filter by
            tags: Tags to filter by
            limit: Number of results to return
        
        Returns:
            List of matching codes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query_parts = query.split()
        search_conditions = []
        search_params = []
        
        # Build search conditions for each query part
        for part in query_parts:
            search_conditions.append("(title LIKE ? OR description LIKE ? OR original_content LIKE ?)")
            search_params.extend([f"%{part}%", f"%{part}%", f"%{part}%"])
        
        search_clause = " AND ".join(search_conditions)
        
        base_query = f'''
            SELECT code_id, title, description, creator_id, category, 
                   created_at, view_count, download_count, rating, rating_count
            FROM marketplace_codes
            WHERE visibility = 'public'
            AND ({search_clause})
        '''
        
        params = search_params[:]
        
        if category:
            base_query += " AND category = ?"
            params.append(category.value)
        
        if tags:
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            base_query += f" AND ({tag_conditions})"
            params.extend([f"%{tag}%" for tag in tags])
        
        base_query += " ORDER BY (rating * rating_count + view_count) DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        conn.close()
        
        codes = []
        for code_id, title, description, creator_id, category, created_at, view_count, download_count, rating, rating_count in rows:
            codes.append({
                'code_id': code_id,
                'title': title,
                'description': description,
                'creator_id': creator_id,
                'category': category,
                'created_at': created_at,
                'view_count': view_count,
                'download_count': download_count,
                'rating': rating,
                'rating_count': rating_count
            })
        
        return codes


# Global marketplace instance
marketplace = KDCodeMarketplace()


def publish_code_to_marketplace(code_id: str, title: str, description: str = None,
                               category: CodeCategory = CodeCategory.GENERAL,
                               visibility: CodeVisibility = CodeVisibility.PUBLIC,
                               tags: List[str] = None, license_type: str = 'CC0',
                               expiration_days: int = None) -> bool:
    """
    Publish a KD-Code to the marketplace
    
    Args:
        code_id: ID of the existing code to publish
        title: Title for the listing
        description: Description for the listing
        category: Category for the code
        visibility: Visibility setting
        tags: Tags for discovery
        license_type: License type
        expiration_days: Days until expiration (None for no expiration)
    
    Returns:
        True if successful, False otherwise
    """
    return marketplace.publish_code_to_marketplace(
        code_id, title, description, category, visibility, tags, 
        license_type, expiration_days
    )


def get_marketplace_codes(category: CodeCategory = None, search_query: str = None,
                         tags: List[str] = None, limit: int = 20, offset: int = 0,
                         sort_by: str = 'created_at', sort_order: str = 'DESC') -> List[Dict[str, Any]]:
    """
    Get codes from the marketplace with filtering and pagination
    
    Args:
        category: Category to filter by
        search_query: Text to search
        tags: Tags to filter by
        limit: Number of results
        offset: Pagination offset
        sort_by: Field to sort by
        sort_order: Sort order ('ASC' or 'DESC')
    
    Returns:
        List of marketplace codes
    """
    return marketplace.get_marketplace_codes(
        category, search_query, tags, limit, offset, sort_by, sort_order
    )


def get_code_details(code_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a marketplace code
    
    Args:
        code_id: ID of the code to retrieve
    
    Returns:
        Code details or None if not found
    """
    return marketplace.get_code_details(code_id)


def increment_code_views(code_id: str):
    """Increment the view count for a code"""
    marketplace.increment_view_count(code_id)


def increment_code_downloads(code_id: str):
    """Increment the download count for a code"""
    marketplace.increment_download_count(code_id)


def add_user_rating(code_id: str, user_id: str, rating: int, review: str = None) -> bool:
    """
    Add a user rating for a code
    
    Args:
        code_id: ID of the code to rate
        user_id: ID of the user rating
        rating: Rating (1-5)
        review: Optional review text
    
    Returns:
        True if successful, False otherwise
    """
    return marketplace.add_user_rating(code_id, user_id, rating, review)


def add_code_to_favorites(code_id: str, user_id: str) -> bool:
    """
    Add a code to a user's favorites
    
    Args:
        code_id: ID of the code to favorite
        user_id: ID of the user
    
    Returns:
        True if successful, False otherwise
    """
    return marketplace.add_to_favorites(code_id, user_id)


def get_user_favorites(user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get a user's favorite codes
    
    Args:
        user_id: ID of the user
        limit: Number of results
        offset: Pagination offset
    
    Returns:
        List of favorite codes
    """
    return marketplace.get_user_favorites(user_id, limit, offset)


def get_top_rated_codes(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the top-rated codes in the marketplace
    
    Args:
        limit: Number of codes to return
    
    Returns:
        List of top-rated codes
    """
    return marketplace.get_top_rated_codes(limit)


def get_most_popular_codes(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the most popular codes based on download/view counts
    
    Args:
        limit: Number of codes to return
    
    Returns:
        List of most popular codes
    """
    return marketplace.get_most_popular_codes(limit)


def get_featured_codes(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get featured codes in the marketplace
    
    Args:
        limit: Number of codes to return
    
    Returns:
        List of featured codes
    """
    return marketplace.get_featured_codes(limit)


def search_marketplace_codes(query: str, category: CodeCategory = None, 
                           tags: List[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search for codes in the marketplace
    
    Args:
        query: Search query string
        category: Category to filter by
        tags: Tags to filter by
        limit: Number of results to return
    
    Returns:
        List of matching codes
    """
    return marketplace.search_codes(query, category, tags, limit)


# Example usage
if __name__ == "__main__":
    # Example of using the marketplace
    print("Initializing KD-Code Marketplace...")
    
    # Publish a sample code to the marketplace
    success = publish_code_to_marketplace(
        code_id="sample_code_123",
        title="Sample Business Card KD-Code",
        description="A KD-Code containing contact information for a business card",
        category=CodeCategory.BUSINESS,
        tags=["business", "contact", "card"],
        license_type="CC0"
    )
    
    if success:
        print("Successfully published code to marketplace")
        
        # Get codes from marketplace
        codes = get_marketplace_codes(limit=5)
        print(f"Found {len(codes)} codes in marketplace")
        
        # Get top rated codes
        top_rated = get_top_rated_codes(limit=3)
        print(f"Top rated codes: {len(top_rated)}")
        
        # Get most popular codes
        popular = get_most_popular_codes(limit=3)
        print(f"Most popular codes: {len(popular)}")
        
        # Search for codes
        search_results = search_marketplace_codes("business", limit=5)
        print(f"Search results for 'business': {len(search_results)}")
    else:
        print("Failed to publish code to marketplace")