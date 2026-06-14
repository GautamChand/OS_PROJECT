import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .manager import load_access_data, save_access_data

# Absolute path to monitored_folder
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MONITOR_DIR = os.path.join(PROJECT_ROOT, "monitored_folder")

class FileAccessHandler(FileSystemEventHandler):
    def on_modified(self, event):
     if not event.is_directory:
        filename = os.path.basename(event.src_path)
        # Ignore already compressed files
        if filename.endswith(".zlib"):
            return
        access_data = load_access_data()
        access_data[filename] = access_data.get(filename, 0) + 1
        save_access_data(access_data)
        print(f"[ACCESS DETECTED] {filename} accessed ({access_data[filename]} times)")


def start_file_monitor():
    event_handler = FileAccessHandler()
    observer = Observer()
    observer.schedule(event_handler, MONITOR_DIR, recursive=False)
    observer.start()
    print(f"Watching folder: {MONITOR_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
