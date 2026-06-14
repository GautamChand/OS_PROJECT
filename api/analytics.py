"""
Smart Adaptive File Compression System — Analytics API
Provides data for charts and detailed analysis.
"""
from flask import Blueprint, jsonify
from database import get_db_connection, db_execute
from ml.predictor import access_predictor

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/access-frequency')
def access_frequency():
    """Get most and least accessed files."""
    most = db_execute('''
        SELECT filename, access_count, temperature, original_size, file_category
        FROM files
        ORDER BY access_count DESC
        LIMIT 10
    ''', fetch_all=True)
    
    least = db_execute('''
        SELECT filename, access_count, temperature, original_size, file_category
        FROM files
        WHERE access_count > 0
        ORDER BY access_count ASC
        LIMIT 10
    ''', fetch_all=True)
    
    return jsonify({
        'most_accessed': most or [],
        'least_accessed': least or [],
    })


@analytics_bp.route('/file-types')
def file_type_distribution():
    """Get file distribution by type/category."""
    conn = get_db_connection()
    try:
        types = conn.execute('''
            SELECT 
                file_category,
                COUNT(*) as count,
                COALESCE(SUM(original_size), 0) as total_size,
                COALESCE(AVG(original_size), 0) as avg_size,
                COALESCE(SUM(CASE WHEN is_compressed = 1 THEN 1 ELSE 0 END), 0) as compressed_count
            FROM files
            WHERE file_category IS NOT NULL
            GROUP BY file_category
            ORDER BY total_size DESC
        ''').fetchall()
        
        return jsonify([dict(t) for t in types])
    finally:
        conn.close()


@analytics_bp.route('/compression-efficiency')
def compression_efficiency():
    """Get compression efficiency by algorithm."""
    conn = get_db_connection()
    try:
        efficiency = conn.execute('''
            SELECT 
                algorithm,
                COUNT(*) as operations,
                COALESCE(AVG(CASE WHEN original_size > 0 
                    THEN CAST(savings_bytes AS REAL) / original_size * 100 
                    ELSE 0 END), 0) as avg_savings_percent,
                COALESCE(SUM(savings_bytes), 0) as total_savings,
                COALESCE(AVG(duration_ms), 0) as avg_duration_ms
            FROM compression_log
            WHERE operation = 'compress'
            GROUP BY algorithm
        ''').fetchall()
        
        return jsonify([dict(e) for e in efficiency])
    finally:
        conn.close()


@analytics_bp.route('/storage-timeline')
def storage_timeline():
    """Get storage metrics over time."""
    metrics = db_execute('''
        SELECT 
            recorded_at,
            total_files,
            total_size,
            compressed_size,
            space_saved,
            avg_compression_ratio,
            hot_count, warm_count, cold_count, archive_count
        FROM system_metrics
        ORDER BY recorded_at ASC
        LIMIT 100
    ''', fetch_all=True)
    
    return jsonify(metrics or [])


@analytics_bp.route('/predictions')
def get_predictions():
    """Get ML predictions for all files."""
    files = db_execute(
        'SELECT * FROM files WHERE is_compressed = 0 ORDER BY access_count DESC',
        fetch_all=True
    )
    
    if not files:
        return jsonify({
            'predictions': [],
            'model_status': access_predictor.get_status(),
        })
    
    predictions = access_predictor.predict_batch(files)
    
    return jsonify({
        'predictions': predictions,
        'model_status': access_predictor.get_status(),
    })


@analytics_bp.route('/train-model', methods=['POST'])
def train_model():
    """Trigger ML model training."""
    success = access_predictor.train()
    return jsonify({
        'success': success,
        'status': access_predictor.get_status(),
    })


@analytics_bp.route('/os-concepts')
def os_concepts():
    """Get OS concepts demonstrated by the system."""
    return jsonify([
        {
            'concept': 'Process Scheduling',
            'feature': 'File Temperature Classification',
            'description': 'Files are classified like OS processes with priority levels (Hot=Interactive, Warm=Normal, Cold=Background, Archive=Idle). Similar to multilevel priority queue scheduling.',
            'icon': '⚡',
        },
        {
            'concept': 'Priority Queue / CPU Scheduling',
            'feature': 'Compression Queue',
            'description': 'Files are enqueued for compression using a priority queue (min-heap). Archive files get highest priority, hot files are never queued. Mirrors CPU scheduling algorithms.',
            'icon': '📊',
        },
        {
            'concept': 'Daemon Process',
            'feature': 'Background File Watcher',
            'description': 'The file monitor runs as a background daemon thread, continuously watching for file system events. Similar to OS system services like cron or systemd.',
            'icon': '👁️',
        },
        {
            'concept': 'File System Metadata (Inode)',
            'feature': 'Access Time Tracking',
            'description': 'Uses os.stat() to read inode-level metadata: st_atime (access time), st_mtime (modification time), st_size. Core to how OS manages file systems.',
            'icon': '📁',
        },
        {
            'concept': 'Timer Interrupt',
            'feature': 'Auto-Compression Scheduler',
            'description': 'Periodic compression cycles are triggered by timer interrupts (threading.Timer). Similar to OS timer interrupts that preempt processes.',
            'icon': '⏰',
        },
        {
            'concept': 'Memory Management',
            'feature': 'Storage Analytics',
            'description': 'Tracks total storage, used storage, and fragmentation. Similar to OS memory management tracking allocation, free space, and fragmentation.',
            'icon': '💾',
        },
        {
            'concept': 'Page Replacement (LRU/LFU)',
            'feature': 'ML-Based Access Prediction',
            'description': 'Predicts future file access using historical patterns. Similar to how OS page replacement algorithms (LRU, LFU, Optimal) predict which pages to evict.',
            'icon': '🧠',
        },
        {
            'concept': 'Virtual Memory',
            'feature': 'Compression Simulation',
            'description': 'Estimates storage savings without actual compression. Like virtual memory, it projects resource usage without physical allocation.',
            'icon': '🔮',
        },
        {
            'concept': 'Cache Management',
            'feature': 'File Temperature System',
            'description': 'Hot files = cached (fast access, no compression). Archive files = swapped to disk (compressed). Mirrors CPU cache hierarchy (L1/L2/L3/RAM/Disk).',
            'icon': '🗄️',
        },
        {
            'concept': 'Resource Allocation',
            'feature': 'Multi-Algorithm Selection',
            'description': 'System chooses optimal compression algorithm per file type and temperature. Like OS resource allocation matching CPU/memory to process needs.',
            'icon': '⚙️',
        },
    ])
