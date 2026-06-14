"""
Smart Adaptive File Compression System — Metadata Tracker
Scans folders and tracks OS-level file metadata.
Demonstrates OS Concept: File System Management — inode metadata (atime, mtime, ctime).
"""
import os
from datetime import datetime
from database import upsert_file, get_db_connection, db_execute, record_access
from config import Config


class MetadataTracker:
    """
    Scans and tracks file system metadata.
    
    OS Concept: File System Metadata / Inode
    - Uses os.stat() to read inode-level metadata
    - Tracks: st_atime (access time), st_mtime (modify time), st_ctime (create time), st_size
    - Similar to how OS maintains inode tables for file system management
    """
    
    @staticmethod
    def scan_folder(folder_path=None):
        """
        Perform a full scan of a folder, updating metadata for all files.
        
        Returns:
            dict with scan results summary
        """
        folder_path = folder_path or Config.DEFAULT_MONITOR_DIR
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            return {'scanned': 0, 'folder': folder_path, 'error': None}
        
        # Check current Windows wallpaper to update its access time
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Control Panel\Desktop')
            wallpaper_path, _ = winreg.QueryValueEx(key, 'Wallpaper')
            winreg.CloseKey(key)
            
            if wallpaper_path:
                normalized_wallpaper = os.path.normcase(os.path.abspath(wallpaper_path))
                normalized_folder = os.path.normcase(os.path.abspath(folder_path))
                if os.path.exists(normalized_wallpaper) and normalized_wallpaper.startswith(normalized_folder):
                    conn = get_db_connection()
                    try:
                        row = conn.execute('SELECT id, last_accessed FROM files WHERE filepath = ?', (normalized_wallpaper,)).fetchone()
                        if row:
                            file_id = row['id']
                            last_acc = row['last_accessed']
                            
                            # Debounce registry-based access updates (only update if last accessed > 30s ago)
                            should_update = True
                            if last_acc:
                                try:
                                    last_acc_dt = datetime.fromisoformat(last_acc)
                                    if (datetime.now() - last_acc_dt).total_seconds() < 30:
                                        should_update = False
                                except Exception:
                                    pass
                                    
                            if should_update:
                                record_access(file_id, 'read')
                                print(f"[METADATA] Detected active wallpaper slideshow access: {os.path.basename(normalized_wallpaper)}")
                    finally:
                        conn.close()
        except Exception:
            pass
        
        scanned = 0
        errors = []
        total_size = 0
        
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                filepath = os.path.normcase(os.path.abspath(os.path.join(root, filename)))
                
                # Handle compressed files by reading their headers
                if filename.endswith('.sc'):
                    try:
                        import struct
                        from compressor.compress_engine import MAGIC_HEADERS
                        stat = os.stat(filepath)
                        with open(filepath, 'rb') as f:
                            magic = f.read(4)
                            if len(magic) == 4:
                                algorithm = None
                                for algo, header in MAGIC_HEADERS.items():
                                    if magic == header:
                                        algorithm = algo
                                        break
                                if algorithm:
                                    original_size = struct.unpack('>Q', f.read(8))[0]
                                    compressed_size = stat.st_size
                                    ratio = compressed_size / original_size if original_size > 0 else 1.0
                                    decompressed_filename = filename[:-3]  # remove '.sc'
                                    file_type = os.path.splitext(decompressed_filename)[1].lower()
                                    file_category = Config.get_file_category(decompressed_filename)
                                    
                                    upsert_file(
                                        filepath=filepath,
                                        filename=decompressed_filename,
                                        file_type=file_type,
                                        file_category=file_category,
                                        size=original_size,
                                        last_accessed=datetime.fromtimestamp(stat.st_atime).isoformat(),
                                        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                        is_compressed=1,
                                        compressed_size=compressed_size,
                                        compression_ratio=ratio,
                                        compression_algorithm=algorithm
                                    )
                                    total_size += original_size
                                    scanned += 1
                                    continue
                    except Exception as e:
                        errors.append({'file': filename, 'error': f"Failed to read compressed header: {e}"})
                    continue
                
                try:
                    stat = os.stat(filepath)
                    file_type = os.path.splitext(filename)[1].lower()
                    file_category = Config.get_file_category(filename)
                    
                    upsert_file(
                        filepath=filepath,
                        filename=filename,
                        file_type=file_type,
                        file_category=file_category,
                        size=stat.st_size,
                        last_accessed=datetime.fromtimestamp(stat.st_atime).isoformat(),
                        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    )
                    
                    total_size += stat.st_size
                    scanned += 1
                    
                except Exception as e:
                    errors.append({'file': filename, 'error': str(e)})
        
        # Clean up files from database that are no longer on disk or are outside the current monitored folder
        conn = get_db_connection()
        try:
            db_files = conn.execute('SELECT id, filepath FROM files').fetchall()
            dead_file_ids = []
            normalized_monitor_dir = os.path.normcase(os.path.abspath(folder_path))
            
            for row in db_files:
                norm_fp = os.path.normcase(os.path.abspath(row['filepath']))
                try:
                    is_inside = os.path.commonpath([normalized_monitor_dir, norm_fp]) == normalized_monitor_dir
                except ValueError:
                    is_inside = False
                
                if not os.path.exists(norm_fp) or not is_inside:
                    dead_file_ids.append(row['id'])
            
            if dead_file_ids:
                placeholders = ','.join('?' for _ in dead_file_ids)
                conn.execute(f'DELETE FROM files WHERE id IN ({placeholders})', dead_file_ids)
                # Also delete associated recommendations
                conn.execute(f'DELETE FROM recommendations WHERE action_type = "compress_file" AND action_data IN ({placeholders})', dead_file_ids)
                conn.commit()
                print(f"[METADATA] Cleaned up {len(dead_file_ids)} stale files from database")
        except Exception as e:
            print(f"[METADATA ERROR] Failed to clean up stale files: {e}")
        finally:
            conn.close()
        
        return {
            'scanned': scanned,
            'total_size': total_size,
            'folder': folder_path,
            'errors': errors,
        }
    
    @staticmethod
    def update_metadata(filepath):
        """Update metadata for a single file."""
        if not os.path.exists(filepath):
            return None
        
        try:
            stat = os.stat(filepath)
            filename = os.path.basename(filepath)
            file_type = os.path.splitext(filename)[1].lower()
            file_category = Config.get_file_category(filename)
            
            upsert_file(
                filepath=filepath,
                filename=filename,
                file_type=file_type,
                file_category=file_category,
                size=stat.st_size,
                last_accessed=datetime.fromtimestamp(stat.st_atime).isoformat(),
                last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            )
            
            return {
                'filename': filename,
                'size': stat.st_size,
                'last_accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_stale_files(days=30):
        """
        Get files that haven't been accessed for N days.
        
        OS Concept: LRU Cache Eviction
        - Similar to how OS identifies least recently used pages for eviction
        """
        return db_execute(
            '''SELECT * FROM files 
               WHERE is_compressed = 0 
               AND (last_accessed IS NULL OR 
                    julianday('now') - julianday(last_accessed) > ?)
               ORDER BY last_accessed ASC''',
            (days,), fetch_all=True
        )
    
    @staticmethod
    def get_large_files(min_size_bytes=1048576):
        """Get files larger than min_size (default 1MB)."""
        return db_execute(
            '''SELECT * FROM files 
               WHERE original_size >= ? AND is_compressed = 0
               ORDER BY original_size DESC''',
            (min_size_bytes,), fetch_all=True
        )
    
    @staticmethod
    def get_folder_stats(folder_path=None):
        """
        Get comprehensive statistics for a monitored folder.
        
        OS Concept: File System Statistics
        - Similar to df/du commands in Unix
        """
        folder_path = folder_path or Config.DEFAULT_MONITOR_DIR
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Overall stats
            stats = cursor.execute('''
                SELECT 
                    COUNT(*) as total_files,
                    COALESCE(SUM(original_size), 0) as total_original_size,
                    COALESCE(SUM(CASE WHEN is_compressed = 1 THEN compressed_size ELSE original_size END), 0) as current_size,
                    COALESCE(SUM(CASE WHEN is_compressed = 1 THEN original_size - compressed_size ELSE 0 END), 0) as space_saved,
                    COALESCE(SUM(CASE WHEN is_compressed = 1 THEN 1 ELSE 0 END), 0) as compressed_count,
                    COALESCE(SUM(CASE WHEN is_compressed = 0 THEN 1 ELSE 0 END), 0) as uncompressed_count
                FROM files
            ''').fetchone()
            
            # Temperature distribution
            temps = cursor.execute('''
                SELECT temperature, COUNT(*) as count, COALESCE(SUM(original_size), 0) as total_size
                FROM files
                GROUP BY temperature
            ''').fetchall()
            
            # File type distribution
            types = cursor.execute('''
                SELECT file_category, COUNT(*) as count, COALESCE(SUM(original_size), 0) as total_size
                FROM files
                GROUP BY file_category
            ''').fetchall()
            
            total_original = stats['total_original_size'] or 1
            
            return {
                'folder_path': folder_path,
                'total_files': stats['total_files'],
                'total_original_size': stats['total_original_size'],
                'current_size': stats['current_size'],
                'space_saved': stats['space_saved'],
                'compression_ratio': round(stats['current_size'] / total_original, 4) if total_original > 0 else 0,
                'compressed_count': stats['compressed_count'],
                'uncompressed_count': stats['uncompressed_count'],
                'temperature_distribution': {row['temperature']: {'count': row['count'], 'size': row['total_size']} for row in temps},
                'file_type_distribution': {row['file_category']: {'count': row['count'], 'size': row['total_size']} for row in types if row['file_category']},
            }
        finally:
            conn.close()
