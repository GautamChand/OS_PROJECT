"""
Smart Adaptive File Compression System — Database Layer
SQLite database setup, schema management, and helper functions.
"""
import sqlite3
import os
from datetime import datetime
from config import Config


def get_db_connection():
    """Create and return a database connection with row factory."""
    Config.ensure_directories()
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize the database with schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ── Files Table ──────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL UNIQUE,
            file_type TEXT,
            file_category TEXT,
            original_size INTEGER DEFAULT 0,
            compressed_size INTEGER DEFAULT 0,
            compression_ratio REAL DEFAULT 0.0,
            compression_algorithm TEXT,
            temperature TEXT DEFAULT 'warm',
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            last_modified TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_compressed BOOLEAN DEFAULT 0,
            predicted_next_access TIMESTAMP,
            priority_score REAL DEFAULT 0.0
        )
    ''')
    
    # ── Access History Table ─────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action_type TEXT,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )
    ''')
    
    # ── Compression Log Table ────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compression_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            filename TEXT,
            operation TEXT,
            algorithm TEXT,
            original_size INTEGER,
            result_size INTEGER,
            savings_bytes INTEGER,
            duration_ms REAL,
            performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL
        )
    ''')
    
    # ── System Metrics Table ─────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_files INTEGER DEFAULT 0,
            total_size INTEGER DEFAULT 0,
            compressed_size INTEGER DEFAULT 0,
            space_saved INTEGER DEFAULT 0,
            avg_compression_ratio REAL DEFAULT 0.0,
            hot_count INTEGER DEFAULT 0,
            warm_count INTEGER DEFAULT 0,
            cold_count INTEGER DEFAULT 0,
            archive_count INTEGER DEFAULT 0,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ── Recommendations Table ────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            category TEXT DEFAULT 'info',
            icon TEXT DEFAULT 'info',
            potential_savings INTEGER DEFAULT 0,
            action_type TEXT,
            action_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_dismissed BOOLEAN DEFAULT 0
        )
    ''')
    
    # ── Indexes ──────────────────────────────────────────────
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_temperature ON files(temperature)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_filepath ON files(filepath)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_history_file_id ON access_history(file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_compression_log_file_id ON compression_log(file_id)')
    
    conn.commit()
    conn.close()


# ── Helper Functions ─────────────────────────────────────────

def db_execute(query, params=(), fetch_one=False, fetch_all=False):
    """Execute a database query and optionally fetch results."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch_one:
            result = cursor.fetchone()
            return dict(result) if result else None
        elif fetch_all:
            results = cursor.fetchall()
            return [dict(row) for row in results]
        else:
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()


def db_execute_many(query, params_list):
    """Execute a query with multiple parameter sets."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.executemany(query, params_list)
        conn.commit()
    finally:
        conn.close()


def upsert_file(filepath, filename, file_type, file_category, size, last_accessed, last_modified,
                is_compressed=0, compressed_size=0, compression_ratio=0.0, compression_algorithm=None):
    """Insert or update a file record."""
    import os
    filepath = os.path.normcase(os.path.abspath(filepath))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO files (filepath, filename, file_type, file_category, original_size, last_accessed, last_modified,
                               is_compressed, compressed_size, compression_ratio, compression_algorithm)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filepath) DO UPDATE SET
                filename = excluded.filename,
                file_type = excluded.file_type,
                file_category = excluded.file_category,
                original_size = excluded.original_size,
                last_accessed = CASE 
                    WHEN files.last_accessed IS NULL THEN excluded.last_accessed
                    WHEN excluded.last_accessed IS NULL THEN files.last_accessed
                    ELSE MAX(files.last_accessed, excluded.last_accessed)
                END,
                last_modified = CASE 
                    WHEN files.last_modified IS NULL THEN excluded.last_modified
                    WHEN excluded.last_modified IS NULL THEN files.last_modified
                    ELSE MAX(files.last_modified, excluded.last_modified)
                END,
                is_compressed = excluded.is_compressed,
                compressed_size = excluded.compressed_size,
                compression_ratio = excluded.compression_ratio,
                compression_algorithm = excluded.compression_algorithm
        ''', (filepath, filename, file_type, file_category, size, last_accessed, last_modified,
              is_compressed, compressed_size, compression_ratio, compression_algorithm))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def record_access(file_id, action_type='read'):
    """Record a file access event."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO access_history (file_id, action_type) VALUES (?, ?)',
            (file_id, action_type)
        )
        cursor.execute(
            'UPDATE files SET access_count = access_count + 1, last_accessed = ? WHERE id = ?',
            (datetime.now().isoformat(), file_id)
        )
        conn.commit()
    finally:
        conn.close()


def log_compression(file_id, filename, operation, algorithm, original_size, result_size, duration_ms):
    """Log a compression/decompression operation."""
    savings = original_size - result_size if operation == 'compress' else 0
    return db_execute(
        '''INSERT INTO compression_log 
           (file_id, filename, operation, algorithm, original_size, result_size, savings_bytes, duration_ms)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (file_id, filename, operation, algorithm, original_size, result_size, savings, duration_ms)
    )


def record_system_metrics():
    """Take a snapshot of current system metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        stats = cursor.execute('''
            SELECT 
                COUNT(*) as total_files,
                COALESCE(SUM(original_size), 0) as total_size,
                COALESCE(SUM(CASE WHEN is_compressed = 1 THEN compressed_size ELSE original_size END), 0) as compressed_size,
                COALESCE(SUM(CASE WHEN is_compressed = 1 THEN original_size - compressed_size ELSE 0 END), 0) as space_saved,
                COALESCE(AVG(CASE WHEN is_compressed = 1 AND original_size > 0 THEN CAST(compressed_size AS REAL) / original_size ELSE NULL END), 0) as avg_ratio,
                COALESCE(SUM(CASE WHEN temperature = 'hot' THEN 1 ELSE 0 END), 0) as hot_count,
                COALESCE(SUM(CASE WHEN temperature = 'warm' THEN 1 ELSE 0 END), 0) as warm_count,
                COALESCE(SUM(CASE WHEN temperature = 'cold' THEN 1 ELSE 0 END), 0) as cold_count,
                COALESCE(SUM(CASE WHEN temperature = 'archive' THEN 1 ELSE 0 END), 0) as archive_count
            FROM files
        ''').fetchone()
        
        cursor.execute('''
            INSERT INTO system_metrics 
            (total_files, total_size, compressed_size, space_saved, avg_compression_ratio,
             hot_count, warm_count, cold_count, archive_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            stats['total_files'], stats['total_size'], stats['compressed_size'],
            stats['space_saved'], stats['avg_ratio'],
            stats['hot_count'], stats['warm_count'], stats['cold_count'], stats['archive_count']
        ))
        conn.commit()
    finally:
        conn.close()


def add_recommendation(message, category='info', icon='info', potential_savings=0, action_type=None, action_data=None):
    """Add a smart recommendation."""
    # Check if similar recommendation already exists (undismissed)
    existing = db_execute(
        'SELECT id FROM recommendations WHERE message = ? AND is_dismissed = 0',
        (message,), fetch_one=True
    )
    if not existing:
        return db_execute(
            '''INSERT INTO recommendations (message, category, icon, potential_savings, action_type, action_data)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (message, category, icon, potential_savings, action_type, action_data)
        )
    return None
