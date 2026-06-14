"""
Smart Adaptive File Compression System — File Watcher
Real-time file system monitoring using watchdog.
Demonstrates OS Concept: Daemon Process — runs continuously in background.
"""
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

from database import get_db_connection, record_access, upsert_file
from config import Config
from compressor.compress_engine import COMPRESSED_EXTENSION


class SmartFileHandler(FileSystemEventHandler):
    """
    Enhanced file system event handler.
    
    OS Concept: Interrupt Handler / Daemon Process
    - Runs as a background daemon monitoring file system events
    - Similar to OS interrupt handlers that respond to I/O events
    - Tracks file access patterns for intelligent compression decisions
    """
    
    def __init__(self, on_event_callback=None):
        super().__init__()
        self.on_event_callback = on_event_callback
        self._last_events = {}  # debounce rapid events
    
    def _should_process(self, filepath):
        """Debounce rapid-fire events for the same file (within 2 seconds)."""
        now = time.time()
        last = self._last_events.get(filepath, 0)
        if now - last < 2:
            return False
        self._last_events[filepath] = now
        return True
    
    def _is_ignorable(self, filepath):
        """Check if the file should be ignored."""
        filename = os.path.basename(filepath)
        # Ignore hidden files and temp files
        return (
            filename.startswith('.') or
            filename.endswith('.tmp') or
            filename.endswith('.swp') or
            filename == 'desktop.ini' or
            filename == 'Thumbs.db'
        )
    
    def _handle_event(self, event, action_type):
        """Common event handling logic."""
        if event.is_directory:
            return
        
        filepath = os.path.normcase(os.path.abspath(event.src_path))
        
        if self._is_ignorable(filepath):
            return
        
        if not self._should_process(filepath):
            return
        
        filename = os.path.basename(filepath)
        
        try:
            # Update or create file record in database
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                
                # Ignore events for files that have modification times in the past (backdated sample files)
                if time.time() - stat.st_mtime > 5 and not filename.endswith(COMPRESSED_EXTENSION):
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
                    print(f"[WATCHER] Ignored access update for backdated file: {filename}")
                    return
                
                # Check if it's a compressed file. Parse its header!
                if filename.endswith(COMPRESSED_EXTENSION):
                    import struct
                    from compressor.compress_engine import MAGIC_HEADERS
                    try:
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
                                    
                                    # Get file_id and record access
                                    conn = get_db_connection()
                                    try:
                                        cursor = conn.cursor()
                                        row = cursor.execute(
                                            'SELECT id FROM files WHERE filepath = ?', (filepath,)
                                        ).fetchone()
                                    finally:
                                        conn.close()
                                    
                                    if row:
                                        record_access(row['id'], action_type)
                                    
                                    # Notify callback (for SSE/WebSocket)
                                    if self.on_event_callback:
                                        self.on_event_callback({
                                            'type': action_type,
                                            'filename': decompressed_filename,
                                            'filepath': filepath,
                                            'timestamp': datetime.now().isoformat(),
                                        })
                                    print(f"[WATCHER] {action_type.upper()} (Compressed): {decompressed_filename}")
                                    return
                    except Exception as e:
                        print(f"[WATCHER ERROR] Failed to parse compressed file {filename}: {e}")
                
                # Standard uncompressed file flow:
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
                
                # Get file_id and record access
                conn = get_db_connection()
                try:
                    cursor = conn.cursor()
                    row = cursor.execute(
                        'SELECT id FROM files WHERE filepath = ?', (filepath,)
                    ).fetchone()
                finally:
                    conn.close()
                
                if row:
                    record_access(row['id'], action_type)
            
            # Notify callback (for SSE/WebSocket)
            if self.on_event_callback:
                self.on_event_callback({
                    'type': action_type,
                    'filename': filename,
                    'filepath': filepath,
                    'timestamp': datetime.now().isoformat(),
                })
            
            print(f"[WATCHER] {action_type.upper()}: {filename}")
            
        except Exception as e:
            print(f"[WATCHER ERROR] {filename}: {e}")
    
    def on_modified(self, event):
        self._handle_event(event, 'modified')
    
    def on_created(self, event):
        self._handle_event(event, 'created')
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        filepath = os.path.normcase(os.path.abspath(event.src_path))
        filename = os.path.basename(filepath)
        
        if self._is_ignorable(filepath):
            return
        
        try:
            # Mark file as deleted in database
            conn = get_db_connection()
            try:
                conn.execute('DELETE FROM files WHERE filepath = ?', (filepath,))
                conn.commit()
            finally:
                conn.close()
            
            if self.on_event_callback:
                self.on_event_callback({
                    'type': 'deleted',
                    'filename': filename,
                    'filepath': filepath,
                    'timestamp': datetime.now().isoformat(),
                })
            
            print(f"[WATCHER] DELETED: {filename}")
        except Exception as e:
            print(f"[WATCHER ERROR] Delete {filename}: {e}")
    
    def on_moved(self, event):
        if event.is_directory:
            return
        
        old_path = os.path.normcase(os.path.abspath(event.src_path))
        new_path = os.path.normcase(os.path.abspath(event.dest_path))
        new_filename = os.path.basename(new_path)
        
        try:
            conn = get_db_connection()
            try:
                conn.execute(
                    'UPDATE files SET filepath = ?, filename = ? WHERE filepath = ?',
                    (new_path, new_filename, old_path)
                )
                conn.commit()
            finally:
                conn.close()
            
            print(f"[WATCHER] MOVED: {os.path.basename(old_path)} → {new_filename}")
        except Exception as e:
            print(f"[WATCHER ERROR] Move: {e}")


class FileWatcher:
    """
    Manages the watchdog observer for folder monitoring.
    
    OS Concept: Background Service / Daemon
    - Runs as a background thread monitoring the file system
    - Similar to OS services that run persistently
    """
    
    def __init__(self, folder_path=None, on_event_callback=None):
        self.folder_path = folder_path or Config.DEFAULT_MONITOR_DIR
        self.observer = None
        self.handler = SmartFileHandler(on_event_callback)
        self.is_running = False
    
    def start(self):
        """Start watching the folder."""
        if self.is_running:
            return
        
        os.makedirs(self.folder_path, exist_ok=True)
        
        self.observer = Observer()
        self.observer.schedule(self.handler, self.folder_path, recursive=True)
        self.observer.start()
        self.is_running = True
        print(f"[WATCHER] Started monitoring: {self.folder_path}")
    
    def stop(self):
        """Stop watching the folder."""
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.is_running = False
            print("[WATCHER] Stopped monitoring")
    
    def change_folder(self, new_path):
        """Change the monitored folder."""
        was_running = self.is_running
        if was_running:
            self.stop()
        self.folder_path = new_path
        if was_running:
            self.start()
    
    def get_status(self):
        """Get the current watcher status."""
        return {
            'is_running': self.is_running,
            'folder_path': self.folder_path,
            'folder_exists': os.path.exists(self.folder_path),
        }
