"""
Smart Adaptive File Compression System — Dashboard API
Provides storage overview, recommendations, and activity data.
"""
from flask import Blueprint, jsonify
from database import get_db_connection, db_execute, record_system_metrics

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@dashboard_bp.route('/overview')
def get_overview():
    """Get storage overview statistics."""
    conn = get_db_connection()
    try:
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total_files,
                COALESCE(SUM(original_size), 0) as total_original_size,
                COALESCE(SUM(CASE WHEN is_compressed = 1 THEN compressed_size ELSE original_size END), 0) as current_size,
                COALESCE(SUM(CASE WHEN is_compressed = 1 THEN original_size - compressed_size ELSE 0 END), 0) as space_saved,
                COALESCE(SUM(CASE WHEN is_compressed = 1 THEN 1 ELSE 0 END), 0) as compressed_count,
                COALESCE(SUM(CASE WHEN is_compressed = 0 THEN 1 ELSE 0 END), 0) as uncompressed_count
            FROM files
        ''').fetchone()
        
        total = stats['total_original_size'] or 1
        
        return jsonify({
            'total_files': stats['total_files'],
            'total_storage': stats['total_original_size'],
            'used_storage': stats['current_size'],
            'space_saved': stats['space_saved'],
            'compression_ratio': round(stats['current_size'] / total * 100, 1) if total > 0 else 0,
            'compressed_count': stats['compressed_count'],
            'uncompressed_count': stats['uncompressed_count'],
            'savings_percent': round(stats['space_saved'] / total * 100, 1) if total > 0 else 0,
        })
    finally:
        conn.close()


@dashboard_bp.route('/file-temperatures')
def get_file_temperatures():
    """Get file count by temperature category."""
    conn = get_db_connection()
    try:
        temps = conn.execute('''
            SELECT temperature, 
                   COUNT(*) as count, 
                   COALESCE(SUM(original_size), 0) as total_size
            FROM files
            GROUP BY temperature
            ORDER BY 
                CASE temperature 
                    WHEN 'hot' THEN 1 
                    WHEN 'warm' THEN 2 
                    WHEN 'cold' THEN 3 
                    WHEN 'archive' THEN 4 
                END
        ''').fetchall()
        
        result = {
            'hot': {'count': 0, 'size': 0},
            'warm': {'count': 0, 'size': 0},
            'cold': {'count': 0, 'size': 0},
            'archive': {'count': 0, 'size': 0},
        }
        
        for row in temps:
            temp = row['temperature']
            if temp in result:
                result[temp] = {'count': row['count'], 'size': row['total_size']}
        
        return jsonify(result)
    finally:
        conn.close()


@dashboard_bp.route('/recent-activity')
def get_recent_activity():
    """Get the most recent compression operations."""
    activities = db_execute('''
        SELECT cl.*, f.temperature
        FROM compression_log cl
        LEFT JOIN files f ON cl.file_id = f.id
        ORDER BY cl.performed_at DESC
        LIMIT 20
    ''', fetch_all=True)
    
    return jsonify(activities or [])


@dashboard_bp.route('/recommendations')
def get_recommendations():
    """Get smart recommendations."""
    recs = db_execute('''
        SELECT * FROM recommendations 
        WHERE is_dismissed = 0
        ORDER BY potential_savings DESC, created_at DESC
        LIMIT 10
    ''', fetch_all=True)
    
    return jsonify(recs or [])


@dashboard_bp.route('/recommendations/dismiss/<int:rec_id>', methods=['POST'])
def dismiss_recommendation(rec_id):
    """Dismiss a recommendation."""
    db_execute('UPDATE recommendations SET is_dismissed = 1 WHERE id = ?', (rec_id,))
    return jsonify({'success': True})


@dashboard_bp.route('/system-metrics')
def get_system_metrics():
    """Get historical system metrics for charts."""
    metrics = db_execute('''
        SELECT * FROM system_metrics
        ORDER BY recorded_at DESC
        LIMIT 50
    ''', fetch_all=True)
    
    return jsonify(metrics or [])
