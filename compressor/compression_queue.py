"""
Smart Adaptive File Compression System — Compression Queue
Priority queue implementation for scheduling file compression.
Demonstrates OS Concept: CPU Scheduling with Priority Queues.
"""
import heapq
import threading
from datetime import datetime


class CompressionTask:
    """A single compression task in the priority queue."""
    
    def __init__(self, file_id, filepath, filename, priority_score, temperature, algorithm='auto'):
        self.file_id = file_id
        self.filepath = filepath
        self.filename = filename
        self.priority_score = priority_score
        self.temperature = temperature
        self.algorithm = algorithm
        self.status = 'pending'        # pending, processing, completed, failed
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.result = None
    
    def __lt__(self, other):
        # Higher priority score = processed first (max-heap via negation)
        return self.priority_score > other.priority_score
    
    def to_dict(self):
        return {
            'file_id': self.file_id,
            'filepath': self.filepath,
            'filename': self.filename,
            'priority_score': self.priority_score,
            'temperature': self.temperature,
            'algorithm': self.algorithm,
            'status': self.status,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
        }


class CompressionQueue:
    """
    Thread-safe priority queue for compression tasks.
    
    OS Concept: Priority Queue Scheduling
    - Archive files get highest compression priority (weight=4)
    - Cold files get high priority (weight=3)
    - Warm files get moderate priority (weight=2)
    - Hot files are never queued (weight=0)
    
    Similar to: Multilevel Priority Queue Scheduling in OS
    """
    
    def __init__(self):
        self._queue = []
        self._lock = threading.Lock()
        self._history = []          # completed tasks
        self._processing = None     # currently processing task
    
    def add(self, file_id, filepath, filename, priority_score, temperature, algorithm='auto'):
        """Add a compression task to the queue."""
        with self._lock:
            # Don't add hot files
            if temperature == 'hot':
                return None
            
            # Don't add if already in queue
            for task in self._queue:
                if task.filepath == filepath:
                    return None
            
            task = CompressionTask(
                file_id=file_id,
                filepath=filepath,
                filename=filename,
                priority_score=priority_score,
                temperature=temperature,
                algorithm=algorithm,
            )
            heapq.heappush(self._queue, task)
            return task
    
    def next(self):
        """Get the next highest-priority task."""
        with self._lock:
            if self._queue:
                task = heapq.heappop(self._queue)
                task.status = 'processing'
                task.started_at = datetime.now().isoformat()
                self._processing = task
                return task
            return None
    
    def complete(self, task, result=None):
        """Mark a task as completed."""
        with self._lock:
            task.status = 'completed'
            task.completed_at = datetime.now().isoformat()
            task.result = result
            self._history.append(task)
            if self._processing and self._processing.filepath == task.filepath:
                self._processing = None
    
    def fail(self, task, error=None):
        """Mark a task as failed."""
        with self._lock:
            task.status = 'failed'
            task.completed_at = datetime.now().isoformat()
            task.result = {'error': str(error)}
            self._history.append(task)
            if self._processing and self._processing.filepath == task.filepath:
                self._processing = None
    
    def size(self):
        """Get the number of pending tasks."""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self):
        """Check if the queue is empty."""
        with self._lock:
            return len(self._queue) == 0
    
    def clear(self):
        """Clear all pending tasks."""
        with self._lock:
            self._queue.clear()
            self._processing = None
    
    def get_queue_state(self):
        """Get the current state of the queue for API response."""
        with self._lock:
            pending = [task.to_dict() for task in sorted(self._queue)]
            processing = self._processing.to_dict() if self._processing else None
            recent_history = [task.to_dict() for task in self._history[-10:]]
            
            return {
                'pending': pending,
                'pending_count': len(self._queue),
                'processing': processing,
                'recent_completed': recent_history,
                'total_completed': len(self._history),
            }
    
    def process_batch(self, n, compress_func):
        """
        Process up to n tasks from the queue.
        
        Args:
            n: Maximum number of tasks to process.
            compress_func: Function that takes (filepath, algorithm) and returns result dict.
            
        Returns:
            list of results
        """
        results = []
        for _ in range(n):
            task = self.next()
            if task is None:
                break
            
            try:
                result = compress_func(task.filepath, task.algorithm)
                self.complete(task, result)
                results.append({
                    'task': task.to_dict(),
                    'result': result,
                    'success': True,
                })
            except Exception as e:
                self.fail(task, e)
                results.append({
                    'task': task.to_dict(),
                    'error': str(e),
                    'success': False,
                })
        
        return results


# Global compression queue instance
compression_queue = CompressionQueue()
