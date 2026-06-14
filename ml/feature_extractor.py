"""
Smart Adaptive File Compression System — Feature Extractor
Extracts numerical features from file metadata for ML prediction.
Demonstrates OS Concept: Page Replacement (LRU/LFU) — analyzing access patterns.
"""
from datetime import datetime
from config import Config


class FeatureExtractor:
    """
    Extracts ML features from file metadata.
    
    OS Concept: Access Pattern Analysis
    - Similar to how OS tracks page access patterns for replacement algorithms
    - Features capture temporal locality, frequency, and file characteristics
    """
    
    # File category encoding
    CATEGORY_MAP = {
        'text': 0, 'image': 1, 'document': 2, 'video': 3,
        'audio': 4, 'archive': 5, 'binary': 6, 'other': 7,
    }
    
    @staticmethod
    def extract(file_metadata, access_history=None):
        """
        Extract features from a file's metadata.
        
        Features:
            1. access_count — total number of accesses
            2. days_since_last_access — recency
            3. file_size_kb — file size in KB
            4. file_category_encoded — numerical category
            5. avg_access_interval_hours — average time between accesses
            6. hour_of_last_access — time-of-day pattern (0-23)
            7. modification_frequency — how often file is modified
            8. days_since_creation — age of file
        
        Returns:
            list of 8 numerical features
        """
        now = datetime.now()
        
        # Feature 1: Access count
        access_count = file_metadata.get('access_count', 0)
        
        # Feature 2: Days since last access
        last_accessed = file_metadata.get('last_accessed')
        if last_accessed:
            try:
                la = datetime.fromisoformat(str(last_accessed))
                days_since_access = (now - la).total_seconds() / 86400
            except (ValueError, TypeError):
                days_since_access = 365
        else:
            days_since_access = 365
        
        # Feature 3: File size in KB
        file_size_kb = file_metadata.get('original_size', 0) / 1024
        
        # Feature 4: File category encoded
        file_category = file_metadata.get('file_category', 'other')
        category_encoded = FeatureExtractor.CATEGORY_MAP.get(file_category, 7)
        
        # Feature 5: Average access interval (hours)
        if access_history and len(access_history) >= 2:
            intervals = []
            sorted_history = sorted(access_history, key=lambda x: x.get('accessed_at', ''))
            for i in range(1, len(sorted_history)):
                try:
                    t1 = datetime.fromisoformat(str(sorted_history[i-1]['accessed_at']))
                    t2 = datetime.fromisoformat(str(sorted_history[i]['accessed_at']))
                    interval_hours = (t2 - t1).total_seconds() / 3600
                    intervals.append(interval_hours)
                except (ValueError, TypeError):
                    continue
            avg_interval = sum(intervals) / len(intervals) if intervals else 999
        else:
            avg_interval = 999 if access_count == 0 else 24
        
        # Feature 6: Hour of last access (0-23)
        if last_accessed:
            try:
                la = datetime.fromisoformat(str(last_accessed))
                hour_of_access = la.hour
            except (ValueError, TypeError):
                hour_of_access = 12
        else:
            hour_of_access = 12
        
        # Feature 7: Modification frequency (modifications per day since creation)
        created_at = file_metadata.get('created_at')
        if created_at:
            try:
                ca = datetime.fromisoformat(str(created_at))
                days_alive = max((now - ca).total_seconds() / 86400, 1)
            except (ValueError, TypeError):
                days_alive = 30
        else:
            days_alive = 30
        
        modification_freq = access_count / days_alive
        
        # Feature 8: Days since creation
        days_since_creation = days_alive
        
        return [
            access_count,
            round(days_since_access, 2),
            round(file_size_kb, 2),
            category_encoded,
            round(avg_interval, 2),
            hour_of_access,
            round(modification_freq, 4),
            round(days_since_creation, 2),
        ]
    
    @staticmethod
    def get_feature_names():
        """Get the names of the features for display."""
        return [
            'access_count',
            'days_since_last_access',
            'file_size_kb',
            'file_category_encoded',
            'avg_access_interval_hours',
            'hour_of_last_access',
            'modification_frequency',
            'days_since_creation',
        ]
