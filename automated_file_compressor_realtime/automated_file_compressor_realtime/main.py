from compressor.manager import start_automation
from compressor.file_watcher import start_file_monitor
import threading

def main():
    print("=== Real-Time Automated File Compression System ===")

    # Start file watcher in background
    watcher_thread = threading.Thread(target=start_file_monitor, daemon=True)
    watcher_thread.start()

    try:
        start_automation()
    except KeyboardInterrupt:
        print("\nStopped automation.")

if __name__ == "__main__":
    main()
