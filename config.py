"""
Smart Adaptive File Compression System — Configuration
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smartcompress-secret-key-2026')
    DEBUG = True
    
    # Database
    DATABASE_DIR = os.path.join(BASE_DIR, 'data')
    DATABASE_PATH = os.path.join(DATABASE_DIR, 'smartcompress.db')
    
    # Monitored Folder
    DEFAULT_MONITOR_DIR = os.path.join(BASE_DIR, 'monitored_folder')
    
    # ── File Temperature Thresholds ──────────────────────────
    # Hot: Frequently accessed, never compressed
    HOT_ACCESS_COUNT = 10          # accessed more than 10 times
    HOT_RECENCY_HOURS = 24        # accessed within last 24 hours
    
    # Warm: Occasionally accessed, moderate compression
    WARM_ACCESS_COUNT = 4          # accessed 4-10 times
    WARM_RECENCY_DAYS = 7          # accessed within last 7 days
    
    # Cold: Rarely accessed, high compression
    COLD_ACCESS_COUNT = 1          # accessed 1-3 times
    COLD_RECENCY_DAYS = 30         # accessed within last 30 days
    
    # Archive: Not accessed for a long period, maximum compression
    ARCHIVE_RECENCY_DAYS = 30      # not accessed for 30+ days
    
    # ── Compression Settings ────────────────────────────────
    COMPRESSION_ALGORITHMS = ['zlib', 'bz2', 'huffman']
    DEFAULT_ALGORITHM = 'auto'     # auto-selects best algorithm
    
    # Compression levels by temperature
    COMPRESSION_LEVELS = {
        'hot': 0,       # never compress
        'warm': 3,      # light compression (zlib level 3)
        'cold': 6,      # moderate compression (zlib level 6)
        'archive': 9,   # maximum compression (zlib level 9)
    }
    
    # ── Background Scheduler ────────────────────────────────
    SCHEDULER_INTERVAL_SECONDS = 60    # run compression cycle every 60s
    AUTO_COMPRESS_ENABLED = True
    
    # ── Machine Learning ────────────────────────────────────
    ML_MIN_TRAINING_RECORDS = 50       # minimum access records before ML kicks in
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'data', 'access_predictor.joblib')
    ML_PREDICTION_THRESHOLD = 0.3      # probability threshold for "will access soon"
    
    # ── File Type Categories ────────────────────────────────
    FILE_TYPES = {
        'text': ['.txt', '.csv', '.log', '.json', '.xml', '.md', '.html', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
        'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'binary': ['.exe', '.dll', '.so', '.bin', '.dat'],
    }
    
    @classmethod
    def get_file_category(cls, filename):
        """Get the category of a file based on its extension."""
        ext = os.path.splitext(filename)[1].lower()
        for category, extensions in cls.FILE_TYPES.items():
            if ext in extensions:
                return category
        return 'other'
    
    @classmethod
    def ensure_directories(cls):
        """Create required directories if they don't exist."""
        os.makedirs(cls.DATABASE_DIR, exist_ok=True)
        os.makedirs(cls.DEFAULT_MONITOR_DIR, exist_ok=True)
