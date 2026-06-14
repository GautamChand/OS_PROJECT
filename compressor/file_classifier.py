"""
Smart Adaptive File Compression System — File Classifier
Classifies files into temperature categories: Hot, Warm, Cold, Archive.
Demonstrates OS Concept: Priority-based Process Scheduling.
"""
from datetime import datetime, timedelta
from config import Config


class FileClassifier:
    """
    Classifies files into temperature categories based on access patterns.
    
    OS Concept: Priority Scheduling
    - Similar to how an OS assigns priority levels to processes
    - Hot = High priority (interactive), never compressed
    - Warm = Medium priority, light compression
    - Cold = Low priority, heavy compression
    - Archive = Background priority, maximum compression
    """
    
    TEMPERATURE_WEIGHTS = {
        'recency': 0.4,
        'frequency': 0.4,
        'size': 0.2,
    }
    
    @staticmethod
    def classify(file_metadata):
        """
        Classify a file based on its metadata.
        
        Args:
            file_metadata: dict with keys:
                - access_count (int)
                - last_accessed (datetime string or None)
                - original_size (int, bytes)
                
        Returns:
            str: 'hot', 'warm', 'cold', or 'archive'
        """
        access_count = file_metadata.get('access_count', 0)
        last_accessed_str = file_metadata.get('last_accessed')
        
        # Parse last_accessed
        now = datetime.now()
        if last_accessed_str:
            try:
                last_accessed = datetime.fromisoformat(str(last_accessed_str))
            except (ValueError, TypeError):
                last_accessed = None
        else:
            last_accessed = None
        
        # Calculate days since last access
        if last_accessed:
            days_since_access = (now - last_accessed).total_seconds() / 86400
        else:
            days_since_access = 999  # Never accessed → treat as very old
        
        hours_since_access = days_since_access * 24
        
        # ── Classification Logic ─────────────────────────────
        
        # Hot: Frequently accessed or recently accessed within Config.HOT_RECENCY_HOURS
        if access_count >= Config.HOT_ACCESS_COUNT or hours_since_access <= Config.HOT_RECENCY_HOURS:
            return 'hot'
        
        # Warm: Moderately accessed or recently accessed within Config.WARM_RECENCY_DAYS
        if access_count >= Config.WARM_ACCESS_COUNT or days_since_access <= Config.WARM_RECENCY_DAYS:
            return 'warm'
        
        # Cold: Accessed occasionally or recently accessed within Config.COLD_RECENCY_DAYS
        if access_count >= Config.COLD_ACCESS_COUNT or days_since_access <= Config.COLD_RECENCY_DAYS:
            return 'cold'
        
        # Archive: No recent access at all, or never accessed since monitoring (access_count == 0)
        return 'archive'
    
    @staticmethod
    def get_priority_score(file_metadata):
        """
        Calculate a priority score for compression scheduling.
        Higher score = higher priority for compression.
        
        Score formula: temperature_weight * (1 / (access_count + 1)) * log(file_size)
        """
        import math
        
        temperature = FileClassifier.classify(file_metadata)
        access_count = file_metadata.get('access_count', 0)
        file_size = file_metadata.get('original_size', 1)
        
        temp_weights = {
            'hot': 0,        # Never compress hot files
            'warm': 2,
            'cold': 3,
            'archive': 4,
        }
        
        weight = temp_weights.get(temperature, 1)
        frequency_factor = 1 / (access_count + 1)
        size_factor = math.log2(max(file_size, 1)) / 20  # normalize
        
        score = weight * frequency_factor * size_factor
        return round(score, 4)
    
    @staticmethod
    def get_compression_level(temperature):
        """Get the recommended compression level for a temperature."""
        return Config.COMPRESSION_LEVELS.get(temperature, 6)
    
    @staticmethod
    def get_recommended_algorithm(temperature, file_category):
        """
        Get the recommended compression algorithm based on temperature and file type.
        
        Demonstrates: Resource allocation — matching algorithm to workload characteristics.
        """
        if temperature == 'hot':
            return None  # Don't compress hot files
        
        # Text files benefit most from Huffman
        if file_category == 'text':
            if temperature == 'archive':
                return 'bz2'      # Maximum compression for old text
            return 'huffman'       # Good for text
        
        # Already compressed formats
        if file_category in ('archive', 'video', 'audio', 'image'):
            return 'zlib'          # Fast, won't gain much anyway
        
        # Binary and documents
        if temperature == 'archive':
            return 'bz2'          # Best ratio for archive
        elif temperature == 'cold':
            return 'bz2'          # Good ratio
        
        return 'zlib'             # Default: fast, decent ratio
    
    @staticmethod
    def get_temperature_color(temperature):
        """Get the display color for a temperature badge."""
        colors = {
            'hot': '#ef4444',
            'warm': '#f59e0b',
            'cold': '#3b82f6',
            'archive': '#6b7280',
        }
        return colors.get(temperature, '#6b7280')
    
    @staticmethod
    def get_temperature_icon(temperature):
        """Get the icon name for a temperature."""
        icons = {
            'hot': '🔥',
            'warm': '🌤️',
            'cold': '❄️',
            'archive': '📦',
        }
        return icons.get(temperature, '📄')
    
    @staticmethod
    def batch_classify(files_metadata):
        """
        Classify a batch of files.
        
        Args:
            files_metadata: list of dicts with file metadata
            
        Returns:
            dict: {temperature: [file_metadata, ...]}
        """
        classified = {'hot': [], 'warm': [], 'cold': [], 'archive': []}
        
        for file_meta in files_metadata:
            temp = FileClassifier.classify(file_meta)
            file_meta['temperature'] = temp
            file_meta['priority_score'] = FileClassifier.get_priority_score(file_meta)
            classified[temp].append(file_meta)
        
        return classified
