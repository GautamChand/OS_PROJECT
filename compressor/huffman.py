"""
Smart Adaptive File Compression System — Huffman Encoding
Custom implementation of Huffman coding for file compression.
Demonstrates tree data structures and greedy algorithms (OS/CS concept).
"""
import heapq
import struct
import json
import os


class HuffmanNode:
    """A node in the Huffman tree."""
    
    def __init__(self, byte=None, freq=0, left=None, right=None):
        self.byte = byte
        self.freq = freq
        self.left = left
        self.right = right
    
    def __lt__(self, other):
        return self.freq < other.freq
    
    def is_leaf(self):
        return self.left is None and self.right is None


class HuffmanCoder:
    """
    Huffman Encoding/Decoding engine.
    
    Demonstrates:
    - Priority Queue (heapq) — OS scheduling concept
    - Tree data structure — hierarchical file system concept
    - Greedy algorithm — resource optimization
    """
    
    def __init__(self):
        self.codes = {}
        self.reverse_codes = {}
        self.tree = None
    
    def _build_frequency_table(self, data):
        """Build a frequency table from input bytes."""
        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1
        return freq
    
    def _build_tree(self, freq_table):
        """Build Huffman tree using a priority queue (min-heap)."""
        heap = []
        for byte, freq in freq_table.items():
            heapq.heappush(heap, HuffmanNode(byte=byte, freq=freq))
        
        # Handle edge case: single unique byte
        if len(heap) == 1:
            node = heapq.heappop(heap)
            root = HuffmanNode(freq=node.freq, left=node)
            return root
        
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right
            )
            heapq.heappush(heap, parent)
        
        return heap[0] if heap else None
    
    def _generate_codes(self, node, current_code=""):
        """Generate binary codes by traversing the Huffman tree."""
        if node is None:
            return
        
        if node.is_leaf():
            self.codes[node.byte] = current_code if current_code else "0"
            return
        
        self._generate_codes(node.left, current_code + "0")
        self._generate_codes(node.right, current_code + "1")
    
    def _serialize_tree(self, node):
        """Serialize the Huffman tree to a dictionary for storage."""
        if node is None:
            return None
        if node.is_leaf():
            return {'byte': node.byte, 'leaf': True}
        return {
            'leaf': False,
            'left': self._serialize_tree(node.left),
            'right': self._serialize_tree(node.right)
        }
    
    def _deserialize_tree(self, data):
        """Deserialize a Huffman tree from a dictionary."""
        if data is None:
            return None
        if data.get('leaf'):
            return HuffmanNode(byte=data['byte'])
        node = HuffmanNode()
        node.left = self._deserialize_tree(data.get('left'))
        node.right = self._deserialize_tree(data.get('right'))
        return node
    
    def encode(self, data):
        """
        Encode data using Huffman coding.
        
        Returns:
            bytes: Encoded data with header containing the tree structure.
        """
        if not data:
            return b''
        
        # Build frequency table and tree
        freq_table = self._build_frequency_table(data)
        self.tree = self._build_tree(freq_table)
        
        # Generate codes
        self.codes = {}
        self._generate_codes(self.tree)
        
        # Encode data to bit string
        bit_string = ''.join(self.codes[byte] for byte in data)
        
        # Pad bit string to make it a multiple of 8
        padding = 8 - (len(bit_string) % 8)
        if padding == 8:
            padding = 0
        bit_string += '0' * padding
        
        # Convert bit string to bytes
        encoded_bytes = bytearray()
        for i in range(0, len(bit_string), 8):
            encoded_bytes.append(int(bit_string[i:i+8], 2))
        
        # Serialize tree for header
        tree_data = self._serialize_tree(self.tree)
        tree_json = json.dumps(tree_data).encode('utf-8')
        
        # Pack: [tree_size(4 bytes)][padding(1 byte)][tree_json][encoded_data]
        header = struct.pack('>I', len(tree_json)) + struct.pack('B', padding)
        
        return header + tree_json + bytes(encoded_bytes)
    
    def decode(self, encoded_data):
        """
        Decode Huffman-encoded data.
        
        Args:
            encoded_data: bytes with header containing tree structure.
        
        Returns:
            bytes: Original decoded data.
        """
        if not encoded_data:
            return b''
        
        # Unpack header
        tree_size = struct.unpack('>I', encoded_data[:4])[0]
        padding = struct.unpack('B', encoded_data[4:5])[0]
        
        # Extract tree and encoded data
        tree_json = encoded_data[5:5+tree_size].decode('utf-8')
        tree_data = json.loads(tree_json)
        self.tree = self._deserialize_tree(tree_data)
        
        encoded_bytes = encoded_data[5+tree_size:]
        
        # Convert bytes to bit string
        bit_string = ''.join(format(byte, '08b') for byte in encoded_bytes)
        
        # Remove padding
        if padding > 0:
            bit_string = bit_string[:-padding]
        
        # Decode using tree traversal
        decoded = bytearray()
        node = self.tree
        
        for bit in bit_string:
            if bit == '0':
                node = node.left
            else:
                node = node.right
            
            if node.is_leaf():
                decoded.append(node.byte)
                node = self.tree
        
        return bytes(decoded)


def compress_huffman(data):
    """Compress data using Huffman encoding."""
    coder = HuffmanCoder()
    return coder.encode(data)


def decompress_huffman(data):
    """Decompress Huffman-encoded data."""
    coder = HuffmanCoder()
    return coder.decode(data)
