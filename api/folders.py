"""
Smart Adaptive File Compression System — Folders API
Manages monitored folder selection and file listing.
"""
import os
from flask import Blueprint, jsonify, request
from database import db_execute, get_db_connection
from config import Config
from monitor.metadata_tracker import MetadataTracker

folders_bp = Blueprint('folders', __name__, url_prefix='/api/folders')


@folders_bp.route('/current')
def get_current_folder():
    """Get info about the currently monitored folder."""
    folder_path = Config.DEFAULT_MONITOR_DIR
    
    if os.path.exists(folder_path):
        total_files = 0
        total_size = 0
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_files += 1
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
        
        return jsonify({
            'path': folder_path,
            'exists': True,
            'total_files': total_files,
            'total_size': total_size,
        })
    
    return jsonify({
        'path': folder_path,
        'exists': False,
        'total_files': 0,
        'total_size': 0,
    })


@folders_bp.route('/set', methods=['POST'])
def set_folder():
    """Change the monitored folder."""
    data = request.get_json()
    folder_path = data.get('path')
    
    if not folder_path:
        return jsonify({'error': 'path is required'}), 400
    
    folder_path = os.path.abspath(folder_path)
    
    if not os.path.exists(folder_path):
        return jsonify({'error': f'Folder does not exist: {folder_path}'}), 404
    
    if not os.path.isdir(folder_path):
        return jsonify({'error': 'Path is not a directory'}), 400
    
    Config.DEFAULT_MONITOR_DIR = folder_path
    
    # Clean up database files and recommendations completely to focus only on this new folder
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM files')
        conn.execute('DELETE FROM recommendations')
        conn.commit()
    finally:
        conn.close()
    
    # Update the watcher path dynamically
    try:
        from flask import current_app
        if hasattr(current_app, 'file_watcher') and current_app.file_watcher:
            current_app.file_watcher.change_folder(folder_path)
    except Exception as e:
        print(f"[ERROR] Failed to change watcher folder: {e}")
    
    # Trigger a scan
    result = MetadataTracker.scan_folder(folder_path)
    
    # Classify files and generate recommendations WITHOUT re-scanning
    try:
        from flask import current_app
        if hasattr(current_app, 'scheduler') and current_app.scheduler:
            current_app.scheduler.generate_recommendations_only()
    except Exception as e:
        print(f"[ERROR] Failed to generate recommendations: {e}")
    
    return jsonify({
        'success': True,
        'path': folder_path,
        'scan_result': result,
    })


@folders_bp.route('/scan')
def scan_folder():
    """Trigger a full folder scan."""
    result = MetadataTracker.scan_folder()
    
    # Use generate_recommendations_only to classify and generate recommendations
    # WITHOUT re-scanning the folder (which we just did above)
    try:
        from flask import current_app
        if hasattr(current_app, 'scheduler') and current_app.scheduler:
            rec_result = current_app.scheduler.generate_recommendations_only()
            if rec_result and rec_result.get('classified'):
                result['classification'] = rec_result['classified']
    except Exception as e:
        print(f"[ERROR] Failed to generate recommendations: {e}")
        
    return jsonify(result)


@folders_bp.route('/files')
def list_files():
    """List all tracked files with metadata."""
    sort_by = request.args.get('sort', 'filename')
    order = request.args.get('order', 'asc')
    temperature = request.args.get('temperature')
    
    query = 'SELECT * FROM files'
    params = []
    
    if temperature:
        query += ' WHERE temperature = ?'
        params.append(temperature)
    
    # Validate sort column
    valid_sorts = ['filename', 'original_size', 'access_count', 'last_accessed', 'temperature', 'priority_score']
    if sort_by in valid_sorts:
        direction = 'DESC' if order.lower() == 'desc' else 'ASC'
        query += f' ORDER BY {sort_by} {direction}'
    else:
        query += ' ORDER BY filename ASC'
    
    files = db_execute(query, tuple(params), fetch_all=True)
    
    return jsonify(files or [])


@folders_bp.route('/stats')
def folder_stats():
    """Get comprehensive folder statistics."""
    stats = MetadataTracker.get_folder_stats()
    return jsonify(stats)
