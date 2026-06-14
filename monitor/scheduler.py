"""
Smart Adaptive File Compression System — Background Scheduler
Runs periodic compression cycles as a background service.
Demonstrates OS Concept: Timer Interrupt / Cron Scheduler.
"""
import threading
import time
import os
from datetime import datetime

from database import get_db_connection, record_system_metrics, add_recommendation, log_compression, db_execute
from config import Config
from compressor.file_classifier import FileClassifier
from compressor.compress_engine import CompressionEngine, is_compressed
from compressor.compression_queue import compression_queue
from monitor.metadata_tracker import MetadataTracker


class CompressionScheduler:
    """
    Background compression scheduler.
    
    OS Concept: Timer Interrupt / Process Scheduler
    - Periodically scans folder, classifies files, and compresses eligible files
    - Similar to OS timer interrupts that trigger scheduler at regular intervals
    - Implements the full scan → classify → enqueue → compress cycle
    """
    
    def __init__(self, interval=None):
        self.interval = interval or Config.SCHEDULER_INTERVAL_SECONDS
        self._timer = None
        self._is_running = False
        self._cycle_count = 0
        self._last_run = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start the background scheduler."""
        if self._is_running:
            return
        
        self._is_running = True
        self._schedule_next()
        print(f"[SCHEDULER] Started (interval: {self.interval}s)")
    
    def stop(self):
        """Stop the background scheduler."""
        self._is_running = False
        if self._timer:
            self._timer.cancel()
        print("[SCHEDULER] Stopped")
    
    def _schedule_next(self):
        """Schedule the next compression cycle."""
        if self._is_running:
            self._timer = threading.Timer(self.interval, self._run_cycle)
            self._timer.daemon = True
            self._timer.start()
    
    def _run_cycle(self, schedule_next=True):
        """Execute one compression cycle."""
        with self._lock:
            try:
                self._cycle_count += 1
                self._last_run = datetime.now().isoformat()
                print(f"\n[SCHEDULER] -- Cycle #{self._cycle_count} --")
                
                # Step 1: Scan folder for metadata
                scan_result = MetadataTracker.scan_folder()
                print(f"[SCHEDULER] Scanned {scan_result['scanned']} files")
                
                # Step 2: Classify all files
                conn = get_db_connection()
                try:
                    files = conn.execute('SELECT * FROM files WHERE is_compressed = 0').fetchall()
                    files = [dict(f) for f in files]
                finally:
                    conn.close()
                
                classified = FileClassifier.batch_classify(files)
                
                # Update temperatures in database
                conn = get_db_connection()
                try:
                    for temp, file_list in classified.items():
                        for f in file_list:
                            conn.execute(
                                'UPDATE files SET temperature = ?, priority_score = ? WHERE id = ?',
                                (temp, f.get('priority_score', 0), f['id'])
                            )
                    conn.commit()
                finally:
                    conn.close()
                
                print(f"[SCHEDULER] Classification: Hot={len(classified['hot'])}, "
                      f"Warm={len(classified['warm'])}, Cold={len(classified['cold'])}, "
                      f"Archive={len(classified['archive'])}")
                
                # Step 3: Enqueue eligible files (Cold + Archive)
                enqueued = 0
                for temp in ['archive', 'cold', 'warm']:
                    for f in classified[temp]:
                        filepath = f['filepath']
                        if os.path.exists(filepath) and not is_compressed(filepath):
                            algo = FileClassifier.get_recommended_algorithm(
                                temp, f.get('file_category', 'other')
                            )
                            if algo:
                                task = compression_queue.add(
                                    file_id=f['id'],
                                    filepath=filepath,
                                    filename=f['filename'],
                                    priority_score=f.get('priority_score', 0),
                                    temperature=temp,
                                    algorithm=algo,
                                )
                                if task:
                                    enqueued += 1
                
                print(f"[SCHEDULER] Enqueued {enqueued} files for compression")
                
                # Step 4: Process compression queue (batch of 5)
                processed_count = 0
                if Config.AUTO_COMPRESS_ENABLED and not compression_queue.is_empty():
                    results = compression_queue.process_batch(
                        5, self._compress_and_log
                    )
                    processed_count = sum(1 for r in results if r['success'])
                    print(f"[SCHEDULER] Compressed {processed_count}/{len(results)} files")
                
                # Step 5: Generate recommendations
                self._generate_recommendations(classified, scan_result)
                
                # Step 6: Record system metrics
                record_system_metrics()
                
                return {
                    'success': True,
                    'scanned': scan_result['scanned'],
                    'classified': {k: len(v) for k, v in classified.items()},
                    'enqueued': enqueued,
                    'processed': processed_count,
                    'cycle': self._cycle_count
                }
                
            except Exception as e:
                print(f"[SCHEDULER ERROR] {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'cycle': self._cycle_count
                }
            
            finally:
                if schedule_next:
                    self._schedule_next()
    
    def _compress_and_log(self, filepath, algorithm):
        """Compress a file and log the operation."""
        result = CompressionEngine.compress(filepath, algorithm)
        
        # Update database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Find the file record
            row = cursor.execute(
                'SELECT id FROM files WHERE filepath = ?', (filepath,)
            ).fetchone()
            
            if row:
                file_id = row['id']
                compressed_path = os.path.normcase(os.path.abspath(result['compressed_path']))
                
                existing = cursor.execute(
                    'SELECT id FROM files WHERE filepath = ?', (compressed_path,)
                ).fetchone()
                
                if existing:
                    active_file_id = existing['id']
                    cursor.execute('''
                        UPDATE files SET 
                            is_compressed = 1,
                            compressed_size = ?,
                            compression_ratio = ?,
                            compression_algorithm = ?
                        WHERE id = ?
                    ''', (
                        result['compressed_size'],
                        result['ratio'],
                        result['algorithm'],
                        active_file_id,
                    ))
                    cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
                else:
                    active_file_id = file_id
                    cursor.execute('''
                        UPDATE files SET 
                            is_compressed = 1,
                            compressed_size = ?,
                            compression_ratio = ?,
                            compression_algorithm = ?,
                            filepath = ?
                        WHERE id = ?
                    ''', (
                        result['compressed_size'],
                        result['ratio'],
                        result['algorithm'],
                        compressed_path,
                        file_id,
                    ))
                conn.commit()
                
                log_compression(
                    file_id=active_file_id,
                    filename=os.path.basename(filepath),
                    operation='compress',
                    algorithm=result['algorithm'],
                    original_size=result['original_size'],
                    result_size=result['compressed_size'],
                    duration_ms=result['duration_ms'],
                )
        finally:
            conn.close()
        return result
    
    def _generate_recommendations(self, classified, scan_result):
        """Generate smart per-file recommendations based on classification results.
        
        Analyzes each file individually and recommends whether to compress or skip it,
        with specific reasoning based on the file's temperature, size, and access patterns.
        """
        # Clear old undismissed recommendations first to prevent stale recommendations
        db_execute('DELETE FROM recommendations WHERE is_dismissed = 0')
        
        # Get all files from database (both compressed and uncompressed)
        conn = get_db_connection()
        try:
            all_files = conn.execute('SELECT * FROM files').fetchall()
            all_files = [dict(f) for f in all_files]
        except Exception as e:
            print(f"[SCHEDULER ERROR] Failed to fetch files for recommendations: {e}")
            all_files = []
        finally:
            conn.close()
            
        if not all_files:
            return
            
        # Helper to format bytes
        def format_bytes(bytes_val):
            if bytes_val == 0:
                return '0 Bytes'
            import math
            k = 1024
            sizes = ['Bytes', 'KB', 'MB', 'GB']
            i = int(math.floor(math.log(max(bytes_val, 1)) / math.log(k)))
            i = min(i, len(sizes) - 1)
            return f"{bytes_val / (k ** i):.1f} {sizes[i]}"
        
        # Separate into uncompressed and already-compressed files
        uncompressed_files = [f for f in all_files if not f.get('is_compressed')]
        compressed_files = [f for f in all_files if f.get('is_compressed')]
        
        # ── Per-file recommendations for uncompressed files ──
        # Sort by priority_score descending (highest priority to compress first)
        uncompressed_files.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        for f in uncompressed_files:
            temp = f.get('temperature', 'warm')
            size_str = format_bytes(f.get('original_size', 0))
            filename = f.get('filename', 'unknown')
            access_count = f.get('access_count', 0)
            file_category = f.get('file_category', 'other')
            
            # Determine last access info
            la_str = 'never'
            days_since = None
            if f.get('last_accessed'):
                try:
                    dt = datetime.fromisoformat(f['last_accessed'])
                    days_since = (datetime.now() - dt).total_seconds() / 86400
                    if days_since < 1:
                        la_str = 'today'
                    elif days_since < 2:
                        la_str = 'yesterday'
                    else:
                        la_str = dt.strftime('%b %d, %Y')
                except Exception:
                    pass
            
            if temp == 'hot':
                # HOT files: recommend NOT compressing
                add_recommendation(
                    message=f"⚡ SKIP '{filename}' ({size_str}) — Hot file, accessed {access_count} times. Actively used, keep uncompressed for fast access.",
                    category='info',
                    icon='fire',
                    potential_savings=0,
                    action_type=None,
                    action_data=None,
                )
            elif temp == 'archive':
                # ARCHIVE files: strongly recommend compressing
                savings_est = int(f.get('original_size', 0) * 0.45)
                algo = FileClassifier.get_recommended_algorithm(temp, file_category)
                add_recommendation(
                    message=f"📦 COMPRESS '{filename}' ({size_str}) — Archive file, last accessed {la_str}. Not used for 30+ days. Best algorithm: {algo or 'zlib'}. Est. savings: {format_bytes(savings_est)}.",
                    category='savings',
                    icon='archive',
                    potential_savings=savings_est,
                    action_type='compress_file',
                    action_data=str(f['id']),
                )
            elif temp == 'cold':
                # COLD files: recommend compressing
                savings_est = int(f.get('original_size', 0) * 0.40)
                algo = FileClassifier.get_recommended_algorithm(temp, file_category)
                add_recommendation(
                    message=f"❄️ COMPRESS '{filename}' ({size_str}) — Cold file, rarely accessed (last: {la_str}). Recommend {algo or 'zlib'} compression. Est. savings: {format_bytes(savings_est)}.",
                    category='savings',
                    icon='snowflake',
                    potential_savings=savings_est,
                    action_type='compress_file',
                    action_data=str(f['id']),
                )
            elif temp == 'warm':
                # WARM files: suggest compressing with lighter algorithm
                savings_est = int(f.get('original_size', 0) * 0.30)
                algo = FileClassifier.get_recommended_algorithm(temp, file_category)
                if f.get('original_size', 0) > 10240:  # Only recommend if > 10KB
                    add_recommendation(
                        message=f"🌤️ CONSIDER '{filename}' ({size_str}) — Warm file, moderately accessed ({access_count}x, last: {la_str}). Light compression with {algo or 'zlib'} could save {format_bytes(savings_est)}.",
                        category='info',
                        icon='cloud',
                        potential_savings=savings_est,
                        action_type='compress_file',
                        action_data=str(f['id']),
                    )
                else:
                    add_recommendation(
                        message=f"🌤️ SKIP '{filename}' ({size_str}) — Warm file, too small for meaningful compression savings.",
                        category='info',
                        icon='cloud',
                        potential_savings=0,
                        action_type=None,
                        action_data=None,
                    )
        
        # ── Summary for already-compressed files ──
        if compressed_files:
            total_saved = sum(
                max(f.get('original_size', 0) - f.get('compressed_size', 0), 0)
                for f in compressed_files
            )
            add_recommendation(
                message=f"✅ {len(compressed_files)} file(s) already compressed, saving {format_bytes(total_saved)} total. These files are optimized.",
                category='info',
                icon='check',
                potential_savings=0,
                action_type=None,
                action_data=None,
            )
    
    def generate_recommendations_only(self):
        """Classify files and generate recommendations WITHOUT re-scanning the folder.
        
        Use this after an explicit scan to avoid double-scanning.
        """
        with self._lock:
            try:
                # Classify all uncompressed files from the database
                conn = get_db_connection()
                try:
                    files = conn.execute('SELECT * FROM files WHERE is_compressed = 0').fetchall()
                    files = [dict(f) for f in files]
                finally:
                    conn.close()
                
                from compressor.file_classifier import FileClassifier
                classified = FileClassifier.batch_classify(files)
                
                # Update temperatures in database
                conn = get_db_connection()
                try:
                    for temp, file_list in classified.items():
                        for f in file_list:
                            conn.execute(
                                'UPDATE files SET temperature = ?, priority_score = ? WHERE id = ?',
                                (temp, f.get('priority_score', 0), f['id'])
                            )
                    conn.commit()
                finally:
                    conn.close()
                
                # Generate recommendations
                self._generate_recommendations(classified, {'scanned': len(files)})
                
                # Record system metrics
                record_system_metrics()
                
                return {
                    'success': True,
                    'classified': {k: len(v) for k, v in classified.items()},
                }
            except Exception as e:
                print(f"[SCHEDULER ERROR] generate_recommendations_only: {e}")
                return {'success': False, 'error': str(e)}
    
    def run_now(self, sync=False):
        """Trigger an immediate compression cycle."""
        if sync:
            return self._run_cycle(schedule_next=False)
        else:
            thread = threading.Thread(target=self._run_cycle, args=(False,), daemon=True)
            thread.start()
            return {'status': 'started', 'cycle': self._cycle_count + 1}
    
    def get_status(self):
        """Get scheduler status."""
        return {
            'is_running': self._is_running,
            'interval_seconds': self.interval,
            'cycle_count': self._cycle_count,
            'last_run': self._last_run,
            'queue_size': compression_queue.size(),
            'auto_compress': Config.AUTO_COMPRESS_ENABLED,
        }
