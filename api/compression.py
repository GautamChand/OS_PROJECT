"""
Smart Adaptive File Compression System — Compression API
Handles compress, decompress, simulate, and benchmark operations.
"""
import os
import sqlite3
from flask import Blueprint, jsonify, request, current_app
from database import get_db_connection, db_execute, log_compression
from compressor.compress_engine import CompressionEngine, is_compressed
from compressor.compression_queue import compression_queue
from compressor.simulator import CompressionSimulator
from config import Config

compression_bp = Blueprint('compression', __name__, url_prefix='/api/compress')


@compression_bp.route('/file', methods=['POST'])
def compress_file():
    """Compress a single file."""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        algorithm = data.get('algorithm', 'auto')
        
        if not file_id:
            return jsonify({'error': 'file_id is required'}), 400
        
        # Get file info
        file_info = db_execute(
            'SELECT * FROM files WHERE id = ?', (file_id,), fetch_one=True
        )
        
        if not file_info:
            return jsonify({'error': 'File not found'}), 404
        
        if file_info['is_compressed']:
            return jsonify({'error': 'File is already compressed'}), 400
        
        filepath = file_info['filepath']
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found on disk'}), 404
        
        result = CompressionEngine.compress(filepath, algorithm)
        
        # Update database with duplicate and race condition handling
        normalized_path = os.path.normcase(os.path.abspath(result['compressed_path']))
        conn = get_db_connection()
        try:
            try:
                existing = conn.execute(
                    'SELECT id FROM files WHERE filepath = ?', (normalized_path,)
                ).fetchone()
                
                if existing:
                    active_file_id = existing['id']
                    conn.execute('''
                        UPDATE files SET 
                            is_compressed = 1,
                            compressed_size = ?,
                            compression_ratio = ?,
                            compression_algorithm = ?
                        WHERE id = ?
                    ''', (result['compressed_size'], result['ratio'], result['algorithm'], active_file_id))
                    conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
                else:
                    active_file_id = file_id
                    conn.execute('''
                        UPDATE files SET 
                            is_compressed = 1,
                            compressed_size = ?,
                            compression_ratio = ?,
                            compression_algorithm = ?,
                            filepath = ?
                        WHERE id = ?
                    ''', (result['compressed_size'], result['ratio'], result['algorithm'],
                          normalized_path, file_id))
                conn.commit()
            except sqlite3.IntegrityError:
                # Race condition: the background watcher inserted the compressed file row 
                # in the split second between SELECT and UPDATE/COMMIT.
                conn.rollback()
                existing = conn.execute(
                    'SELECT id FROM files WHERE filepath = ?', (normalized_path,)
                ).fetchone()
                if existing:
                    active_file_id = existing['id']
                    conn.execute('''
                        UPDATE files SET 
                            is_compressed = 1,
                            compressed_size = ?,
                            compression_ratio = ?,
                            compression_algorithm = ?
                        WHERE id = ?
                    ''', (result['compressed_size'], result['ratio'], result['algorithm'], active_file_id))
                    conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
                    conn.commit()
                else:
                    raise
        finally:
            conn.close()
        
        log_compression(
            file_id=active_file_id,
            filename=file_info['filename'],
            operation='compress',
            algorithm=result['algorithm'],
            original_size=result['original_size'],
            result_size=result['compressed_size'],
            duration_ms=result['duration_ms'],
        )
        
        # Update recommendations without re-scanning
        try:
            if hasattr(current_app, 'scheduler') and current_app.scheduler:
                current_app.scheduler.generate_recommendations_only()
        except Exception as e:
            print(f"[ERROR] Failed to update recommendations: {e}")
            
        return jsonify({
            'success': True,
            'result': result,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@compression_bp.route('/batch', methods=['POST'])
def compress_batch():
    """Compress files by temperature category."""
    try:
        data = request.get_json()
        temperature = data.get('temperature', 'cold')
        algorithm = data.get('algorithm', 'auto')
        
        files = db_execute(
            'SELECT * FROM files WHERE temperature = ? AND is_compressed = 0',
            (temperature,), fetch_all=True
        )
        
        if not files:
            return jsonify({'message': f'No uncompressed {temperature} files found', 'compressed': 0})
        
        results = []
        for file_info in files:
            filepath = file_info['filepath']
            if os.path.exists(filepath):
                try:
                    result = CompressionEngine.compress(filepath, algorithm)
                    
                    normalized_path = os.path.normcase(os.path.abspath(result['compressed_path']))
                    conn = get_db_connection()
                    try:
                        try:
                            existing = conn.execute(
                                'SELECT id FROM files WHERE filepath = ?', (normalized_path,)
                            ).fetchone()
                            
                            if existing:
                                active_file_id = existing['id']
                                conn.execute('''
                                    UPDATE files SET 
                                        is_compressed = 1,
                                        compressed_size = ?,
                                        compression_ratio = ?,
                                        compression_algorithm = ?
                                    WHERE id = ?
                                ''', (result['compressed_size'], result['ratio'], result['algorithm'], active_file_id))
                                conn.execute('DELETE FROM files WHERE id = ?', (file_info['id'],))
                            else:
                                active_file_id = file_info['id']
                                conn.execute('''
                                    UPDATE files SET 
                                        is_compressed = 1,
                                        compressed_size = ?,
                                        compression_ratio = ?,
                                        compression_algorithm = ?,
                                        filepath = ?
                                    WHERE id = ?
                                ''', (result['compressed_size'], result['ratio'], result['algorithm'],
                                      normalized_path, file_info['id']))
                            conn.commit()
                        except sqlite3.IntegrityError:
                            conn.rollback()
                            existing = conn.execute(
                                'SELECT id FROM files WHERE filepath = ?', (normalized_path,)
                            ).fetchone()
                            if existing:
                                active_file_id = existing['id']
                                conn.execute('''
                                    UPDATE files SET 
                                        is_compressed = 1,
                                        compressed_size = ?,
                                        compression_ratio = ?,
                                        compression_algorithm = ?
                                    WHERE id = ?
                                ''', (result['compressed_size'], result['ratio'], result['algorithm'], active_file_id))
                                conn.execute('DELETE FROM files WHERE id = ?', (file_info['id'],))
                                conn.commit()
                            else:
                                raise
                    finally:
                        conn.close()
                    
                    log_compression(
                        file_id=active_file_id,
                        filename=file_info['filename'],
                        operation='compress',
                        algorithm=result['algorithm'],
                        original_size=result['original_size'],
                        result_size=result['compressed_size'],
                        duration_ms=result['duration_ms'],
                    )
                    
                    results.append({'success': True, 'filename': file_info['filename'], 'result': result})
                except Exception as e:
                    results.append({'success': False, 'filename': file_info['filename'], 'error': str(e)})
        
        # Update recommendations without re-scanning
        try:
            if hasattr(current_app, 'scheduler') and current_app.scheduler:
                current_app.scheduler.generate_recommendations_only()
        except Exception as e:
            print(f"[ERROR] Failed to update recommendations: {e}")
            
        return jsonify({
            'compressed': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'results': results,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@compression_bp.route('/simulate', methods=['POST'])
def simulate_compression():
    """Simulate compression to estimate savings."""
    try:
        data = request.get_json() or {}
        folder_path = data.get('folder_path', Config.DEFAULT_MONITOR_DIR)
        
        result = CompressionSimulator.simulate_folder(folder_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@compression_bp.route('/decompress', methods=['POST'])
def decompress_file():
    """Decompress a file."""
    try:
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'file_id is required'}), 400
        
        file_info = db_execute(
            'SELECT * FROM files WHERE id = ?', (file_id,), fetch_one=True
        )
        
        if not file_info:
            return jsonify({'error': 'File not found'}), 404
        
        if not file_info['is_compressed']:
            return jsonify({'error': 'File is not compressed'}), 400
        
        filepath = file_info['filepath']
        if not os.path.exists(filepath):
            return jsonify({'error': 'Compressed file not found on disk'}), 404
        
        result = CompressionEngine.decompress(filepath)
        
        from datetime import datetime
        current_time = datetime.now().isoformat()
        normalized_path = os.path.normcase(os.path.abspath(result['decompressed_path']))
        conn = get_db_connection()
        try:
            try:
                # Check if there is already a record for the decompressed path (inserted by watcher)
                existing = conn.execute(
                    'SELECT id FROM files WHERE filepath = ?', (normalized_path,)
                ).fetchone()
                
                if existing:
                    active_file_id = existing['id']
                    conn.execute('''
                        UPDATE files SET 
                            is_compressed = 0,
                            compressed_size = 0,
                            compression_ratio = 0,
                            compression_algorithm = NULL,
                            last_accessed = ?,
                            access_count = access_count + 1
                        WHERE id = ?
                    ''', (current_time, active_file_id))
                    # Delete the old compressed record to avoid duplicates
                    conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
                else:
                    active_file_id = file_id
                    conn.execute('''
                        UPDATE files SET 
                            is_compressed = 0,
                            compressed_size = 0,
                            compression_ratio = 0,
                            compression_algorithm = NULL,
                            filepath = ?,
                            last_accessed = ?,
                            access_count = access_count + 1
                        WHERE id = ?
                    ''', (normalized_path, current_time, file_id))
                conn.commit()
            except sqlite3.IntegrityError:
                # Race condition: the background watcher inserted the decompressed file row 
                # in the split second between SELECT and UPDATE/COMMIT.
                conn.rollback()
                existing = conn.execute(
                    'SELECT id FROM files WHERE filepath = ?', (normalized_path,)
                ).fetchone()
                if existing:
                    active_file_id = existing['id']
                    conn.execute('''
                        UPDATE files SET 
                            is_compressed = 0,
                            compressed_size = 0,
                            compression_ratio = 0,
                            compression_algorithm = NULL,
                            last_accessed = ?,
                            access_count = access_count + 1
                        WHERE id = ?
                    ''', (current_time, active_file_id))
                    conn.execute('DELETE FROM files WHERE id = ?', (file_id,))
                    conn.commit()
                else:
                    raise
        finally:
            conn.close()
        
        log_compression(
            file_id=active_file_id,
            filename=file_info['filename'],
            operation='decompress',
            algorithm=file_info.get('compression_algorithm', 'unknown'),
            original_size=result['compressed_size'],
            result_size=result['original_size'],
            duration_ms=result['duration_ms'],
        )
        
        # Update recommendations without re-scanning
        try:
            if hasattr(current_app, 'scheduler') and current_app.scheduler:
                current_app.scheduler.generate_recommendations_only()
        except Exception as e:
            print(f"[ERROR] Failed to update recommendations: {e}")
            
        return jsonify({
            'success': True,
            'result': result,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@compression_bp.route('/queue')
def get_queue():
    """Get the current compression queue state."""
    return jsonify(compression_queue.get_queue_state())


@compression_bp.route('/benchmark/<int:file_id>')
def benchmark_file(file_id):
    """Benchmark all algorithms on a file."""
    try:
        file_info = db_execute(
            'SELECT * FROM files WHERE id = ?', (file_id,), fetch_one=True
        )
        
        if not file_info:
            return jsonify({'error': 'File not found'}), 404
        
        filepath = file_info['filepath']
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found on disk'}), 404
        
        if file_info['is_compressed']:
            return jsonify({'error': 'Cannot benchmark compressed file'}), 400
        
        results = CompressionEngine.benchmark(filepath)
        return jsonify({
            'filename': file_info['filename'],
            'original_size': file_info['original_size'],
            'results': results,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
