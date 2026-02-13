"""
Predictive Analytics Module for KD-Code System
Implements predictive analytics for code usage patterns and trends
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import json
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import pickle
import os
import logging


class KDCodePredictiveAnalytics:
    """
    Predictive analytics system for KD-Code usage patterns
    """
    
    def __init__(self, db_path: str = "kd_codes_lifecycle.db"):
        """
        Initialize the predictive analytics system
        
        Args:
            db_path: Path to the database with usage data
        """
        self.db_path = db_path
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = "models/predictive_analytics_model.pkl"
        self.scaler_path = "models/predictive_analytics_scaler.pkl"
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
    
    def extract_features(self, historical_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract features from historical data for training
        
        Args:
            historical_data: List of historical usage records
        
        Returns:
            Tuple of (features, targets) for model training
        """
        features = []
        targets = []
        
        for record in historical_data:
            # Extract temporal features
            created_at = datetime.fromisoformat(record['created_at'])
            day_of_week = created_at.weekday()
            hour_of_day = created_at.hour
            day_of_month = created_at.day
            month = created_at.month
            
            # Extract usage features
            scan_count = record.get('scan_count', 0)
            days_since_creation = (datetime.now() - created_at).days
            has_expired = record.get('status') == 'expired'
            creator_id_hash = hash(record.get('creator_id', '')) % 10000
            content_length = len(record.get('content', ''))
            
            # Extract categorical features (as numerical)
            status_map = {'draft': 0, 'active': 1, 'expired': 2, 'revoked': 3, 'archived': 4, 'scanned': 5}
            status_value = status_map.get(record.get('status', 'active'), 1)
            
            # Create feature vector
            feature_vector = [
                day_of_week,
                hour_of_day,
                day_of_month,
                month,
                scan_count,
                days_since_creation,
                int(has_expired),
                creator_id_hash,
                content_length,
                status_value
            ]
            
            features.append(feature_vector)
            
            # Target: predict future scan count or engagement
            # For this example, we'll predict scan count in the next period
            targets.append(scan_count)
        
        return np.array(features), np.array(targets)
    
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from the database
        
        Returns:
            Tuple of (features, targets) for model training
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Query historical data from the codes table
        cursor.execute('''
            SELECT code_id, content, status, created_at, scan_count, creator_id
            FROM codes
            WHERE created_at >= date('now', '-90 days')  -- Last 90 days of data
        ''')
        
        records = []
        for row in cursor.fetchall():
            records.append({
                'code_id': row[0],
                'content': row[1],
                'status': row[2],
                'created_at': row[3],
                'scan_count': row[4],
                'creator_id': row[5]
            })
        
        conn.close()
        
        if not records:
            self.logger.warning("No historical data found for training")
            return np.array([]), np.array([])
        
        return self.extract_features(records)
    
    def train_model(self):
        """
        Train the predictive model on historical data
        """
        self.logger.info("Starting model training for predictive analytics")
        
        # Prepare training data
        features, targets = self.prepare_training_data()
        
        if len(features) == 0:
            self.logger.warning("Insufficient data for training")
            return
        
        # Split data for training and testing
        if len(features) < 10:  # Need at least 10 samples to split
            X_train, X_test, y_train, y_test = features, features, targets, targets
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test) if len(X_test) > 0 else X_train_scaled
        
        # Train the model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate the model
        y_pred = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        self.logger.info(f"Model trained - MAE: {mae:.4f}, MSE: {mse:.4f}, R²: {r2:.4f}")
        
        # Mark as trained
        self.is_trained = True
        
        # Save the model
        self.save_model()
    
    def save_model(self):
        """Save the trained model and scaler to disk"""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            
            self.logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
    
    def load_model(self) -> bool:
        """
        Load a pre-trained model from disk
        
        Returns:
            True if model was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                
                self.is_trained = True
                self.logger.info("Pre-trained model loaded successfully")
                return True
            else:
                self.logger.warning("Model files not found")
                return False
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return False
    
    def predict_code_popularity(self, code_info: Dict) -> Dict[str, float]:
        """
        Predict the popularity/usage of a code based on its characteristics
        
        Args:
            code_info: Dictionary with code information
        
        Returns:
            Dictionary with prediction results
        """
        if not self.is_trained:
            self.logger.warning("Model not trained, returning default predictions")
            return {
                'predicted_scan_count': 10.0,
                'confidence': 0.5,
                'trend': 'neutral',
                'recommendation': 'standard_processing'
            }
        
        # Extract features from code info
        created_at = datetime.fromisoformat(code_info.get('created_at', datetime.now().isoformat()))
        day_of_week = created_at.weekday()
        hour_of_day = created_at.hour
        day_of_month = created_at.day
        month = created_at.month
        
        scan_count = code_info.get('scan_count', 0)
        days_since_creation = (datetime.now() - created_at).days
        has_expired = code_info.get('status') == 'expired'
        creator_id_hash = hash(code_info.get('creator_id', '')) % 10000
        content_length = len(code_info.get('content', ''))
        
        status_map = {'draft': 0, 'active': 1, 'expired': 2, 'revoked': 3, 'archived': 4, 'scanned': 5}
        status_value = status_map.get(code_info.get('status', 'active'), 1)
        
        # Create feature vector
        feature_vector = np.array([[
            day_of_week,
            hour_of_day,
            day_of_month,
            month,
            scan_count,
            days_since_creation,
            int(has_expired),
            creator_id_hash,
            content_length,
            status_value
        ]])
        
        # Scale features
        feature_scaled = self.scaler.transform(feature_vector)
        
        # Make prediction
        predicted_scan_count = self.model.predict(feature_scaled)[0]
        
        # Calculate confidence based on prediction variance
        confidence = min(1.0, max(0.0, 1.0 - (abs(predicted_scan_count - scan_count) / max(scan_count, 1))))
        
        # Determine trend
        if predicted_scan_count > scan_count * 1.5:
            trend = 'increasing'
        elif predicted_scan_count < scan_count * 0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Generate recommendation
        if predicted_scan_count > 50:
            recommendation = 'high_priority_processing'
        elif predicted_scan_count > 20:
            recommendation = 'standard_processing'
        else:
            recommendation = 'low_priority_processing'
        
        return {
            'predicted_scan_count': float(predicted_scan_count),
            'confidence': float(confidence),
            'trend': trend,
            'recommendation': recommendation
        }
    
    def predict_usage_trends(self, days_ahead: int = 30) -> Dict[str, List[float]]:
        """
        Predict overall usage trends for the system
        
        Args:
            days_ahead: Number of days to predict ahead
        
        Returns:
            Dictionary with trend predictions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get daily usage data for the past 90 days
        cursor.execute('''
            SELECT 
                date(created_at) as day,
                COUNT(*) as daily_codes,
                SUM(scan_count) as daily_scans
            FROM codes
            WHERE created_at >= date('now', '-90 days')
            GROUP BY date(created_at)
            ORDER BY day
        ''')
        
        daily_data = cursor.fetchall()
        conn.close()
        
        if len(daily_data) < 10:
            # Not enough data, return default trend
            return {
                'dates': [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days_ahead)],
                'predicted_codes': [50.0] * days_ahead,  # Default prediction
                'predicted_scans': [200.0] * days_ahead,  # Default prediction
                'confidence': 0.5
            }
        
        # Prepare time series data
        dates = []
        codes_count = []
        scans_count = []
        
        for day, codes, scans in daily_data:
            dates.append(datetime.strptime(day, '%Y-%m-%d'))
            codes_count.append(codes)
            scans_count.append(scans)
        
        # Create features for time series prediction
        # Using simple approach: day of year, day of week, month, etc.
        ts_features = []
        for i, date in enumerate(dates):
            ts_features.append([
                date.timetuple().tm_yday,  # Day of year
                date.weekday(),           # Day of week
                date.month,               # Month
                i,                        # Sequential day number
                codes_count[i],           # Previous codes count
                scans_count[i]            # Previous scans count
            ])
        
        # For simplicity, we'll use a linear trend model for this example
        # In a real implementation, you'd use more sophisticated time series models
        X = np.array(ts_features)
        y_codes = np.array(codes_count)
        y_scans = np.array(scans_count)
        
        # Fit models
        code_model = LinearRegression()
        scan_model = LinearRegression()
        
        code_model.fit(X, y_codes)
        scan_model.fit(X, y_scans)
        
        # Predict future values
        future_dates = []
        predicted_codes = []
        predicted_scans = []
        
        last_date = dates[-1] if dates else datetime.now()
        last_features = X[-1] if len(X) > 0 else np.array([0, 0, 0, 0, 50, 200])  # Default values
        
        for i in range(1, days_ahead + 1):
            future_date = last_date + timedelta(days=i)
            future_dates.append(future_date.strftime('%Y-%m-%d'))
            
            # Update features for prediction
            future_feature = last_features.copy()
            future_feature[0] = future_date.timetuple().tm_yday  # Day of year
            future_feature[1] = future_date.weekday()           # Day of week
            future_feature[2] = future_date.month               # Month
            future_feature[3] = len(dates) + i                  # Sequential day number
            
            # Predict
            pred_code = code_model.predict([future_feature])[0]
            pred_scan = scan_model.predict([future_feature])[0]
            
            # Ensure non-negative predictions
            pred_code = max(0, pred_code)
            pred_scan = max(0, pred_scan)
            
            predicted_codes.append(pred_code)
            predicted_scans.append(pred_scan)
        
        return {
            'dates': future_dates,
            'predicted_codes': predicted_codes,
            'predicted_scans': predicted_scans,
            'confidence': 0.7  # Default confidence for this simple model
        }
    
    def get_insights(self) -> Dict[str, any]:
        """
        Get analytical insights about code usage patterns
        
        Returns:
            Dictionary with analytical insights
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get various metrics
        cursor.execute("SELECT COUNT(*) FROM codes")
        total_codes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM codes WHERE status = 'active'")
        active_codes = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(scan_count) FROM codes")
        total_scans = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(scan_count) FROM codes WHERE scan_count > 0")
        avg_scans_per_code = cursor.fetchone()[0] or 0
        
        # Get most popular creators
        cursor.execute('''
            SELECT creator_id, COUNT(*) as code_count, SUM(scan_count) as total_scans
            FROM codes
            GROUP BY creator_id
            ORDER BY total_scans DESC
            LIMIT 5
        ''')
        top_creators = cursor.fetchall()
        
        # Get most scanned codes
        cursor.execute('''
            SELECT code_id, content, scan_count
            FROM codes
            ORDER BY scan_count DESC
            LIMIT 5
        ''')
        top_codes = cursor.fetchall()
        
        # Get daily activity patterns
        cursor.execute('''
            SELECT 
                strftime('%H', created_at) as hour,
                COUNT(*) as codes_created
            FROM codes
            GROUP BY strftime('%H', created_at)
            ORDER BY hour
        ''')
        hourly_patterns = cursor.fetchall()
        
        # Get weekly activity patterns
        cursor.execute('''
            SELECT 
                CASE strftime('%w', created_at)
                    WHEN '0' THEN 'Sunday'
                    WHEN '1' THEN 'Monday'
                    WHEN '2' THEN 'Tuesday'
                    WHEN '3' THEN 'Wednesday'
                    WHEN '4' THEN 'Thursday'
                    WHEN '5' THEN 'Friday'
                    WHEN '6' THEN 'Saturday'
                END as day,
                COUNT(*) as codes_created
            FROM codes
            GROUP BY strftime('%w', created_at)
            ORDER BY min(strftime('%w', created_at))
        ''')
        weekly_patterns = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_codes': total_codes,
            'active_codes': active_codes,
            'total_scans': total_scans,
            'avg_scans_per_code': avg_scans_per_code,
            'top_creators': [{'creator_id': row[0], 'code_count': row[1], 'total_scans': row[2]} for row in top_creators],
            'top_codes': [{'code_id': row[0], 'content_snippet': row[1][:50] + '...', 'scan_count': row[2]} for row in top_codes],
            'hourly_patterns': [{'hour': row[0], 'codes_created': row[1]} for row in hourly_patterns],
            'weekly_patterns': [{'day': row[0], 'codes_created': row[1]} for row in weekly_patterns]
        }


# Global predictive analytics instance
predictive_analytics = KDCodePredictiveAnalytics()


def initialize_predictive_analytics(db_path: str = "kd_codes_lifecycle.db"):
    """
    Initialize the predictive analytics system
    
    Args:
        db_path: Path to the database
    """
    global predictive_analytics
    predictive_analytics = KDCodePredictiveAnalytics(db_path)
    
    # Try to load existing model, otherwise train a new one
    if not predictive_analytics.load_model():
        predictive_analytics.train_model()


def predict_code_performance(code_info: Dict) -> Dict[str, float]:
    """
    Predict the performance of a code based on its characteristics
    
    Args:
        code_info: Dictionary with code information
    
    Returns:
        Prediction results
    """
    return predictive_analytics.predict_code_popularity(code_info)


def predict_system_trends(days_ahead: int = 30) -> Dict[str, List[float]]:
    """
    Predict system-wide usage trends
    
    Args:
        days_ahead: Number of days to predict ahead
    
    Returns:
        Trend predictions
    """
    return predictive_analytics.predict_usage_trends(days_ahead)


def get_analytical_insights() -> Dict[str, any]:
    """
    Get analytical insights about code usage
    
    Returns:
        Analytical insights
    """
    return predictive_analytics.get_insights()


# Example usage
if __name__ == "__main__":
    # Initialize the predictive analytics system
    initialize_predictive_analytics()
    
    # Example: Predict performance for a new code
    sample_code_info = {
        'code_id': 'test_code_123',
        'content': 'Sample content for prediction',
        'status': 'active',
        'created_at': datetime.now().isoformat(),
        'scan_count': 5,
        'creator_id': 'user_abc'
    }
    
    prediction = predict_code_performance(sample_code_info)
    print(f"Prediction for sample code: {prediction}")
    
    # Example: Predict system trends
    trends = predict_system_trends(14)  # Predict next 14 days
    print(f"Predicted trends for next 14 days: {len(trends['dates'])} days")
    
    # Example: Get analytical insights
    insights = get_analytical_insights()
    print(f"Total codes in system: {insights['total_codes']}")
    print(f"Active codes: {insights['active_codes']}")
    print(f"Top creators: {insights['top_creators'][:3]}")  # Show top 3