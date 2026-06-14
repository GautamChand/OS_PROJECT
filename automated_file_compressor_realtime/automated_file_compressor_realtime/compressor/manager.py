import os
import time
import pickle
from .compress_util import compress_file

# Absolute path to the project root (two levels up from this file)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Paths
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MONITOR_DIR = os.path.join(PROJECT_ROOT, "monitored_folder")

# Make sure folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MONITOR_DIR, exist_ok=True)

LOG_PATH = os.path.join(DATA_DIR, "access_log.pkl")
ACCESS_THRESHOLD = 3

def load_access_data():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'rb') as f:
            return pickle.load(f)
    return {}

def save_access_data(data):
    with open(LOG_PATH, 'wb') as f:
        pickle.dump(data, f)

def compress_infrequent_files():
    access_data = load_access_data()
    for file in os.listdir(MONITOR_DIR):
        path = os.path.join(MONITOR_DIR, file)
        if os.path.isfile(path) and not file.endswith(".zlib"):
            count = access_data.get(file, 0)
            if count < ACCESS_THRESHOLD:
                print(f"[ACCESS DETECTED] {file} accessed ({count} times)")
                compressed_path = compress_file(path)
                print(f"[COMPRESSED] {file} -> {os.path.basename(compressed_path)}")


def start_automation():
    print("Starting background compression... (Ctrl+C to stop)")
    while True:
        for i in range(500, 0, -10):
            print(f"Next compression in {i} seconds...", end="\r")
            time.sleep(10)
        compress_infrequent_files()
        