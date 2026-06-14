"""
Smart Adaptive File Compression System — Compression Simulator
Estimates compression savings without actually compressing files.
Demonstrates OS Concept: Virtual Memory — estimating without actual allocation.
"""
import os
import zlib
import bz2
import time
from .huffman import compress_huffman
from config import Config


class CompressionSimulator:
    """
    Simulates compression to estimate savings before committing.
    
    OS Concept: Virtual Memory / Simulation
    - Like virtual memory, this estimates resource usage without actual allocation
    - Users can preview storage savings before running compression
    - Uses sampling (first 4KB) to predict compression ratios efficiently
    """
    
    SAMPLE_SIZE = 4096  # 4KB sample for estimation
    
    @staticmethod
    def estimate_ratio(data, algorithm='zlib'):
        """Estimate compression ratio using a data sample."""
        if not data:
            return 1.0
        
        sample = data[:CompressionSimulator.SAMPLE_SIZE]
        
        try:
            if algorithm == 'zlib':
                compressed = zlib.compress(sample, 6)
            elif algorithm == 'bz2':
                compressed = bz2.compress(sample, 9)
            elif algorithm == 'huffman':
                compressed = compress_huffman(sample)
            else:
                return 1.0
            
            return len(compressed) / len(sample)
        except Exception:
            return 1.0
    
    @staticmethod
    def simulate_file(filepath):
        """
        Simulate compression for a single file.
        
        Returns:
            dict with estimated savings per algorithm
        """
        if not os.path.exists(filepath):
            return None
        
        original_size = os.path.getsize(filepath)
        if original_size == 0:
            return {
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'original_size': 0,
                'estimates': {},
                'best_algorithm': None,
                'best_savings': 0,
            }
        
        # Read sample
        with open(filepath, 'rb') as f:
            sample = f.read(CompressionSimulator.SAMPLE_SIZE)
        
        estimates = {}
        for algo in ['zlib', 'bz2', 'huffman']:
            ratio = CompressionSimulator.estimate_ratio(sample, algo)
            estimated_compressed = int(original_size * ratio)
            estimated_savings = original_size - estimated_compressed
            
            estimates[algo] = {
                'estimated_compressed_size': estimated_compressed,
                'estimated_ratio': round(ratio, 4),
                'estimated_savings': max(0, estimated_savings),
                'estimated_savings_percent': round(max(0, (1 - ratio)) * 100, 2),
            }
        
        # Find best algorithm
        best_algo = min(estimates, key=lambda a: estimates[a]['estimated_ratio'])
        
        return {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'original_size': original_size,
            'estimates': estimates,
            'best_algorithm': best_algo,
            'best_savings': estimates[best_algo]['estimated_savings'],
            'best_ratio': estimates[best_algo]['estimated_ratio'],
        }
    
    @staticmethod
    def simulate_folder(folder_path):
        """
        Simulate compression for an entire folder.
        
        Returns:
            dict with per-file estimates and totals
        """
        if not os.path.exists(folder_path):
            return {'error': f'Folder not found: {folder_path}'}
        
        start_time = time.time()
        
        file_results = []
        total_original = 0
        total_estimated_savings = 0
        algorithm_savings = {'zlib': 0, 'bz2': 0, 'huffman': 0}
        
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath) and not filename.endswith('.sc'):
                result = CompressionSimulator.simulate_file(filepath)
                if result:
                    file_results.append(result)
                    total_original += result['original_size']
                    total_estimated_savings += result['best_savings']
                    
                    for algo in ['zlib', 'bz2', 'huffman']:
                        if algo in result['estimates']:
                            algorithm_savings[algo] += result['estimates'][algo]['estimated_savings']
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Overall best algorithm
        best_overall = max(algorithm_savings, key=algorithm_savings.get) if algorithm_savings else 'zlib'
        
        return {
            'folder_path': folder_path,
            'total_files': len(file_results),
            'total_original_size': total_original,
            'total_estimated_savings': total_estimated_savings,
            'estimated_savings_percent': round(
                (total_estimated_savings / total_original * 100) if total_original > 0 else 0, 2
            ),
            'best_overall_algorithm': best_overall,
            'algorithm_savings': algorithm_savings,
            'files': file_results,
            'simulation_duration_ms': round(duration_ms, 2),
        }
