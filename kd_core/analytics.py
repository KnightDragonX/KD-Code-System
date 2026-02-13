"""
Usage Analytics Module for KD-Code System
Provides analytics and reporting functionality
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict


class UsageAnalytics:
    """Handles usage analytics and reporting for KD-Code system"""
    
    def __init__(self, db_path='analytics.db'):
        """
        Initialize the analytics system
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the analytics database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table for API usage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                user_ip TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                response_time REAL,
                status_code INTEGER,
                user_agent TEXT
            )
        ''')
        
        # Create table for KD-Code generation stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generation_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_length INTEGER,
                segments_per_ring INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                processing_time REAL,
                success BOOLEAN
            )
        ''')
        
        # Create table for scan stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                success BOOLEAN,
                processing_time REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_api_call(self, endpoint, method, user_ip, response_time, status_code, user_agent):
        """
        Log an API call for analytics
        
        Args:
            endpoint (str): API endpoint called
            method (str): HTTP method used
            user_ip (str): IP address of the user
            response_time (float): Time taken to process the request
            status_code (int): HTTP status code returned
            user_agent (str): User agent string
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_usage (endpoint, method, user_ip, response_time, status_code, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (endpoint, method, user_ip, response_time, status_code, user_agent))
        
        conn.commit()
        conn.close()
    
    def log_generation_event(self, text_length, segments_per_ring, processing_time, success):
        """
        Log a KD-Code generation event
        
        Args:
            text_length (int): Length of the input text
            segments_per_ring (int): Number of segments per ring used
            processing_time (float): Time taken to generate the code
            success (bool): Whether the generation was successful
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO generation_stats (text_length, segments_per_ring, processing_time, success)
            VALUES (?, ?, ?, ?)
        ''', (text_length, segments_per_ring, processing_time, success))
        
        conn.commit()
        conn.close()
    
    def log_scan_event(self, success, processing_time, error_message=None):
        """
        Log a KD-Code scan event
        
        Args:
            success (bool): Whether the scan was successful
            processing_time (float): Time taken to process the scan
            error_message (str, optional): Error message if scan failed
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scan_stats (success, processing_time, error_message)
            VALUES (?, ?, ?)
        ''', (success, processing_time, error_message))
        
        conn.commit()
        conn.close()
    
    def get_dashboard_data(self):
        """
        Get aggregated data for the analytics dashboard
        
        Returns:
            dict: Aggregated analytics data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get API usage counts
        cursor.execute('SELECT endpoint, COUNT(*) FROM api_usage GROUP BY endpoint')
        api_counts = dict(cursor.fetchall())
        
        # Get daily usage
        cursor.execute('''
            SELECT DATE(timestamp) as day, COUNT(*) 
            FROM api_usage 
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY day
        ''')
        daily_usage = cursor.fetchall()
        
        # Get success rates
        cursor.execute('SELECT COUNT(*) FROM generation_stats WHERE success = 1')
        successful_generations = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM generation_stats')
        total_generations = cursor.fetchone()[0]
        
        generation_success_rate = 0
        if total_generations > 0:
            generation_success_rate = (successful_generations / total_generations) * 100
        
        cursor.execute('SELECT COUNT(*) FROM scan_stats WHERE success = 1')
        successful_scans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scan_stats')
        total_scans = cursor.fetchone()[0]
        
        scan_success_rate = 0
        if total_scans > 0:
            scan_success_rate = (successful_scans / total_scans) * 100
        
        # Get average processing times
        cursor.execute('SELECT AVG(processing_time) FROM generation_stats WHERE success = 1')
        avg_gen_time = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT AVG(processing_time) FROM scan_stats WHERE success = 1')
        avg_scan_time = cursor.fetchone()[0] or 0
        
        # Get most popular parameters
        cursor.execute('''
            SELECT segments_per_ring, COUNT(*) as count
            FROM generation_stats
            GROUP BY segments_per_ring
            ORDER BY count DESC
            LIMIT 5
        ''')
        popular_segments = cursor.fetchall()
        
        # Get scan success/failure breakdown
        cursor.execute('SELECT success, COUNT(*) FROM scan_stats GROUP BY success')
        scan_outcomes = dict(cursor.fetchall())
        
        # Get recent scan errors
        cursor.execute('''
            SELECT error_message, COUNT(*) as count
            FROM scan_stats
            WHERE success = 0 AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY count DESC
            LIMIT 5
        ''')
        recent_errors = cursor.fetchall()
        
        # Get hourly usage patterns
        cursor.execute('''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM api_usage
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY strftime('%H', timestamp)
            ORDER BY hour
        ''')
        hourly_patterns = cursor.fetchall()
        
        conn.close()
        
        return {
            'api_calls': api_counts,
            'daily_usage': daily_usage,
            'hourly_patterns': hourly_patterns,
            'generation_success_rate': generation_success_rate,
            'scan_success_rate': scan_success_rate,
            'scan_outcomes': scan_outcomes,
            'recent_scan_errors': recent_errors,
            'average_generation_time': avg_gen_time,
            'average_scan_time': avg_scan_time,
            'popular_segments': popular_segments,
            'total_generations': total_generations,
            'total_scans': total_scans
        }
    
    def get_scan_success_rates(self):
        """
        Get detailed scan success/failure statistics
        
        Returns:
            dict: Scan success/failure statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get overall scan success rate
        cursor.execute('SELECT COUNT(*) FROM scan_stats')
        total_scans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scan_stats WHERE success = 1')
        successful_scans = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM scan_stats WHERE success = 0')
        failed_scans = cursor.fetchone()[0]
        
        success_rate = 0
        if total_scans > 0:
            success_rate = (successful_scans / total_scans) * 100
        
        # Get success rate by time period
        cursor.execute('''
            SELECT 
                DATE(timestamp) as day,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM scan_stats
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY day DESC
        ''')
        daily_breakdown = []
        for day, total, successful in cursor.fetchall():
            daily_breakdown.append({
                'date': day,
                'total_scans': total,
                'successful_scans': successful,
                'success_rate': (successful / total * 100) if total > 0 else 0
            })
        
        # Get error breakdown
        cursor.execute('''
            SELECT error_message, COUNT(*) as count
            FROM scan_stats
            WHERE success = 0 AND error_message IS NOT NULL
            GROUP BY error_message
            ORDER BY count DESC
        ''')
        error_breakdown = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_scans': total_scans,
            'successful_scans': successful_scans,
            'failed_scans': failed_scans,
            'overall_success_rate': success_rate,
            'daily_breakdown': daily_breakdown,
            'error_breakdown': error_breakdown
        }


    def get_performance_metrics(self):
        """
        Get performance metrics for the application
        
        Returns:
            dict: Performance metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get average response times by endpoint
        cursor.execute('''
            SELECT endpoint, AVG(response_time) as avg_response_time, COUNT(*) as total_requests
            FROM api_usage
            GROUP BY endpoint
            ORDER BY avg_response_time DESC
        ''')
        response_times = dict(cursor.fetchall())
        
        # Get slowest endpoints (above 1 second)
        cursor.execute('''
            SELECT endpoint, COUNT(*) as slow_requests
            FROM api_usage
            WHERE response_time > 1.0
            GROUP BY endpoint
        ''')
        slow_endpoints = dict(cursor.fetchall())
        
        # Get throughput (requests per minute)
        cursor.execute('''
            SELECT 
                strftime('%Y-%m-%d %H:%M', timestamp) as minute,
                COUNT(*) as requests_per_minute
            FROM api_usage
            WHERE timestamp >= datetime('now', '-1 hour')
            GROUP BY strftime('%Y-%m-%d %H:%M', timestamp)
            ORDER BY minute DESC
            LIMIT 60
        ''')
        throughput_data = cursor.fetchall()
        
        # Get 95th percentile response times
        cursor.execute('''
            SELECT endpoint, 
                   AVG(response_time) as avg_time,
                   MIN(response_time) as min_time,
                   MAX(response_time) as max_time
            FROM api_usage
            GROUP BY endpoint
        ''')
        response_stats = []
        for endpoint, avg_time, min_time, max_time in cursor.fetchall():
            response_stats.append({
                'endpoint': endpoint,
                'avg_response_time': avg_time or 0,
                'min_response_time': min_time or 0,
                'max_response_time': max_time or 0
            })
        
        # Get error rates
        cursor.execute('''
            SELECT endpoint, 
                   COUNT(*) as total_requests,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as error_count
            FROM api_usage
            GROUP BY endpoint
        ''')
        error_rates = []
        for endpoint, total, errors in cursor.fetchall():
            error_rate = (errors / total * 100) if total > 0 else 0
            error_rates.append({
                'endpoint': endpoint,
                'total_requests': total,
                'error_count': errors,
                'error_rate': error_rate
            })
        
        conn.close()
        
        return {
            'response_times': response_times,
            'slow_endpoints': slow_endpoints,
            'throughput_data': throughput_data,
            'response_stats': response_stats,
            'error_rates': error_rates
        }
    
    def generate_usage_report(self, start_date=None, end_date=None):
        """
        Generate a comprehensive usage report
        
        Args:
            start_date (str, optional): Start date in YYYY-MM-DD format
            end_date (str, optional): End date in YYYY-MM-DD format
        
        Returns:
            dict: Comprehensive usage report
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build date condition
        date_condition = ""
        params = []
        if start_date and end_date:
            date_condition = "WHERE timestamp BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            date_condition = "WHERE timestamp >= ?"
            params = [start_date]
        elif end_date:
            date_condition = "WHERE timestamp <= ?"
            params = [end_date]
        
        # Get total API calls
        cursor.execute(f'SELECT COUNT(*) FROM api_usage {date_condition}', params)
        total_api_calls = cursor.fetchone()[0]
        
        # Get API calls by endpoint
        cursor.execute(f'SELECT endpoint, COUNT(*) FROM api_usage {date_condition} GROUP BY endpoint', params)
        api_calls_by_endpoint = dict(cursor.fetchall())
        
        # Get total generations
        cursor.execute(f'SELECT COUNT(*) FROM generation_stats {date_condition}', params)
        total_generations = cursor.fetchone()[0]
        
        # Get successful generations
        cursor.execute(f'SELECT COUNT(*) FROM generation_stats WHERE success = 1 {date_condition}', params)
        successful_generations = cursor.fetchone()[0]
        
        # Get total scans
        cursor.execute(f'SELECT COUNT(*) FROM scan_stats {date_condition}', params)
        total_scans = cursor.fetchone()[0]
        
        # Get successful scans
        cursor.execute(f'SELECT COUNT(*) FROM scan_stats WHERE success = 1 {date_condition}', params)
        successful_scans = cursor.fetchone()[0]
        
        # Get average processing times
        cursor.execute(f'SELECT AVG(processing_time) FROM generation_stats WHERE success = 1 {date_condition}', params)
        avg_generation_time = cursor.fetchone()[0] or 0
        
        cursor.execute(f'SELECT AVG(processing_time) FROM scan_stats WHERE success = 1 {date_condition}', params)
        avg_scan_time = cursor.fetchone()[0] or 0
        
        # Get most active hours
        cursor.execute(f'''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM api_usage {date_condition}
            GROUP BY strftime('%H', timestamp)
            ORDER BY count DESC
            LIMIT 5
        ''', params)
        most_active_hours = cursor.fetchall()
        
        # Get most popular segments per ring
        cursor.execute(f'''
            SELECT segments_per_ring, COUNT(*) as count
            FROM generation_stats {date_condition}
            GROUP BY segments_per_ring
            ORDER BY count DESC
            LIMIT 5
        ''', params)
        popular_segments = cursor.fetchall()
        
        # Get error breakdown
        cursor.execute(f'''
            SELECT status_code, COUNT(*) as count
            FROM api_usage
            WHERE status_code >= 400 {date_condition}
            GROUP BY status_code
            ORDER BY count DESC
        ''', params)
        error_breakdown = cursor.fetchall()
        
        conn.close()
        
        # Calculate success rates
        generation_success_rate = (successful_generations / total_generations * 100) if total_generations > 0 else 0
        scan_success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
        
        return {
            'report_period': {
                'start_date': start_date or 'Beginning of time',
                'end_date': end_date or 'Current time'
            },
            'summary': {
                'total_api_calls': total_api_calls,
                'total_generations': total_generations,
                'successful_generations': successful_generations,
                'generation_success_rate': generation_success_rate,
                'total_scans': total_scans,
                'successful_scans': successful_scans,
                'scan_success_rate': scan_success_rate,
                'average_generation_time': avg_generation_time,
                'average_scan_time': avg_scan_time
            },
            'details': {
                'api_calls_by_endpoint': api_calls_by_endpoint,
                'most_active_hours': most_active_hours,
                'popular_segments': popular_segments,
                'error_breakdown': error_breakdown
            }
        }


# Global analytics instance
analytics = UsageAnalytics()


def log_api_usage(endpoint, method, user_ip, response_time, status_code, user_agent):
    """Convenience function to log API usage"""
    analytics.log_api_call(endpoint, method, user_ip, response_time, status_code, user_agent)


def log_generation(text_length, segments_per_ring, processing_time, success):
    """Convenience function to log generation event"""
    analytics.log_generation_event(text_length, segments_per_ring, processing_time, success)


def log_scan(success, processing_time, error_message=None):
    """Convenience function to log scan event"""
    analytics.log_scan_event(success, processing_time, error_message)


def get_analytics_dashboard():
    """Convenience function to get dashboard data"""
    return analytics.get_dashboard_data()


def get_performance_metrics():
    """Convenience function to get performance metrics"""
    return analytics.get_performance_metrics()


def generate_usage_report(start_date=None, end_date=None):
    """Convenience function to generate usage report"""
    return analytics.generate_usage_report(start_date, end_date)


# Example usage
if __name__ == "__main__":
    # Example of logging events
    log_api_usage("/api/generate", "POST", "192.168.1.1", 0.25, 200, "Mozilla/5.0...")
    log_generation(25, 16, 0.5, True)
    log_scan(True, 0.8)
    
    # Get dashboard data
    dashboard_data = get_analytics_dashboard()
    print(json.dumps(dashboard_data, indent=2, default=str))