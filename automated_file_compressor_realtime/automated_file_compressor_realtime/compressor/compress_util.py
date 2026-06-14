import zlib
import os

def compress_file(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    compressed_data = zlib.compress(data, level=9)
    compressed_path = filepath + ".zlib"
    with open(compressed_path, 'wb') as f:
        f.write(compressed_data)
    os.remove(filepath)
    return compressed_path

def decompress_file(filepath):
    if not filepath.endswith(".zlib"):
        return None
    with open(filepath, 'rb') as f:
        data = f.read()
    decompressed_data = zlib.decompress(data)
    original_path = filepath.replace(".zlib", "")
    with open(original_path, 'wb') as f:
        f.write(decompressed_data)
    os.remove(filepath)
    return original_path
