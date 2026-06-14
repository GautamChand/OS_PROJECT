"""
Smart Adaptive File Compression System — Multi-Algorithm Compression Engine
Supports zlib, bz2, and custom Huffman encoding.
Demonstrates resource allocation — choosing optimal strategy per workload (OS concept).
"""
import zlib
import bz2
import os
import time
import struct

from .huffman import compress_huffman, decompress_huffman


# Magic bytes to identify compression algorithm in compressed files
MAGIC_HEADERS = {
    'zlib': b'SCZL',       # SmartCompress Zlib
    'bz2': b'SCBZ',        # SmartCompress BZ2
    'huffman': b'SCHF',    # SmartCompress Huffman
}

COMPRESSED_EXTENSION = '.sc'  # SmartCompress extension


class CompressionEngine:
    """
    Multi-algorithm compression engine.
    
    Demonstrates OS Concept: Resource Allocation
    - Selects optimal compression algorithm based on file characteristics
    - Similar to how an OS allocates CPU/memory based on process needs
    """
    
    @staticmethod
    def compress(filepath, algorithm='auto', level=None):
        """
        Compress a file using the specified algorithm.
        
        Args:
            filepath: Path to the file to compress.
            algorithm: 'zlib', 'bz2', 'huffman', or 'auto' (default).
            level: Compression level (1-9, only for zlib/bz2). None = default.
        
        Returns:
            dict with keys: compressed_path, original_size, compressed_size,
                           ratio, algorithm, duration_ms
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        original_size = len(data)
        
        if original_size == 0:
            return {
                'compressed_path': filepath,
                'original_size': 0,
                'compressed_size': 0,
                'ratio': 0.0,
                'algorithm': 'none',
                'duration_ms': 0.0,
            }
        
        # Auto-select algorithm
        if algorithm == 'auto':
            algorithm = CompressionEngine.get_best_algorithm(filepath, data)
        
        start_time = time.time()
        
        if algorithm == 'zlib':
            comp_level = level if level is not None else 6
            compressed_data = zlib.compress(data, comp_level)
        elif algorithm == 'bz2':
            comp_level = level if level is not None else 9
            compressed_data = bz2.compress(data, comp_level)
        elif algorithm == 'huffman':
            compressed_data = compress_huffman(data)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Write compressed file with magic header
        compressed_path = filepath + COMPRESSED_EXTENSION
        with open(compressed_path, 'wb') as f:
            # Header: [magic(4)][original_size(8)]
            f.write(MAGIC_HEADERS[algorithm])
            f.write(struct.pack('>Q', original_size))
            f.write(compressed_data)
        
        compressed_size = os.path.getsize(compressed_path)
        
        # Remove original file
        os.remove(filepath)
        
        return {
            'compressed_path': compressed_path,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': compressed_size / original_size if original_size > 0 else 0,
            'algorithm': algorithm,
            'duration_ms': round(duration_ms, 2),
        }
    
    @staticmethod
    def decompress(filepath):
        """
        Decompress a file. Auto-detects the algorithm from the header.
        
        Returns:
            dict with keys: decompressed_path, compressed_size, original_size, duration_ms
        """
        if not filepath.endswith(COMPRESSED_EXTENSION):
            raise ValueError(f"Not a SmartCompress file: {filepath}")
        
        with open(filepath, 'rb') as f:
            magic = f.read(4)
            original_size = struct.unpack('>Q', f.read(8))[0]
            compressed_data = f.read()
        
        # Detect algorithm from magic header
        algorithm = None
        for algo, header in MAGIC_HEADERS.items():
            if magic == header:
                algorithm = algo
                break
        
        if algorithm is None:
            raise ValueError(f"Unknown compression format in: {filepath}")
        
        start_time = time.time()
        
        if algorithm == 'zlib':
            data = zlib.decompress(compressed_data)
        elif algorithm == 'bz2':
            data = bz2.decompress(compressed_data)
        elif algorithm == 'huffman':
            data = decompress_huffman(compressed_data)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Write decompressed file
        decompressed_path = filepath[:-len(COMPRESSED_EXTENSION)]
        with open(decompressed_path, 'wb') as f:
            f.write(data)
        
        compressed_size = os.path.getsize(filepath)
        os.remove(filepath)
        
        return {
            'decompressed_path': decompressed_path,
            'compressed_size': compressed_size,
            'original_size': len(data),
            'duration_ms': round(duration_ms, 2),
        }
    
    @staticmethod
    def get_best_algorithm(filepath, data=None):
        """
        Test all algorithms and return the one with the best compression ratio.
        Uses sampling for large files (first 8KB) to speed up selection.
        """
        if data is None:
            with open(filepath, 'rb') as f:
                data = f.read()
        
        # Use sample for large files
        sample = data[:8192] if len(data) > 8192 else data
        
        if len(sample) == 0:
            return 'zlib'
        
        results = {}
        
        try:
            results['zlib'] = len(zlib.compress(sample, 6))
        except Exception:
            results['zlib'] = len(sample)
        
        try:
            results['bz2'] = len(bz2.compress(sample, 9))
        except Exception:
            results['bz2'] = len(sample)
        
        try:
            results['huffman'] = len(compress_huffman(sample))
        except Exception:
            results['huffman'] = len(sample)
        
        return min(results, key=results.get)
    
    @staticmethod
    def benchmark(filepath):
        """
        Benchmark all compression algorithms on a file.
        
        Returns:
            list of dicts with algorithm, compressed_size, ratio, duration_ms
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        original_size = len(data)
        if original_size == 0:
            return []
        
        results = []
        
        for algo in ['zlib', 'bz2', 'huffman']:
            start = time.time()
            try:
                if algo == 'zlib':
                    compressed = zlib.compress(data, 6)
                elif algo == 'bz2':
                    compressed = bz2.compress(data, 9)
                elif algo == 'huffman':
                    compressed = compress_huffman(data)
                
                duration = (time.time() - start) * 1000
                comp_size = len(compressed)
                
                results.append({
                    'algorithm': algo,
                    'original_size': original_size,
                    'compressed_size': comp_size,
                    'ratio': round(comp_size / original_size, 4),
                    'savings_percent': round((1 - comp_size / original_size) * 100, 2),
                    'duration_ms': round(duration, 2),
                })
            except Exception as e:
                results.append({
                    'algorithm': algo,
                    'original_size': original_size,
                    'compressed_size': original_size,
                    'ratio': 1.0,
                    'savings_percent': 0.0,
                    'duration_ms': 0.0,
                    'error': str(e),
                })
        
        return results


def is_compressed(filepath):
    """Check if a file is already compressed by SmartCompress."""
    return filepath.endswith(COMPRESSED_EXTENSION)
