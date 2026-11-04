"""
LightRanger Wire-Format Compression Engine (Yu et al., IEEE/ACM IWQoS 2026).
Equal Element Grouping (EEG) + Base-Bit Reduction (BBR).
Reported strictly as serialized wire size, never mixed with in-memory RAM.
"""

from __future__ import annotations
import math
import struct
import numpy as np


def compress_matrix(matrix: np.ndarray, group_size: int = 8) -> bytes:
    """
    Compress a 2D counter matrix using EEG and BBR.
    Returns serialized byte string.
    """
    d, w = matrix.shape
    dtype_code = 0 if matrix.dtype == np.uint8 else (1 if matrix.dtype == np.uint16 else 2)

    # Header: d (uint16), w (uint32), group_size (uint8), dtype_code (uint8)
    header = struct.pack(">HIHB", d, w, group_size, dtype_code)
    body = bytearray()

    for row in range(d):
        for g_start in range(0, w, group_size):
            g_end = min(g_start + group_size, w)
            chunk = matrix[row, g_start:g_end].astype(np.uint64)
            actual_size = len(chunk)

            v_min = int(np.min(chunk))
            deltas = [int(x - v_min) for x in chunk]
            max_delta = max(deltas)

            if max_delta == 0:
                b = 0
            else:
                b = max_delta.bit_length()

            # Pack group header: v_min (compact), b (uint8), actual_size (uint8)
            if dtype_code == 0:
                body.extend(struct.pack(">BBB", v_min, b, actual_size))
            elif dtype_code == 1:
                body.extend(struct.pack(">HBB", v_min, b, actual_size))
            else:
                body.extend(struct.pack(">IBB", v_min, b, actual_size))

            if b > 0:
                # Bit-pack actual_size * b bits
                bit_buffer = 0
                bit_count = 0
                for delta in deltas:
                    bit_buffer = (bit_buffer << b) | (delta & ((1 << b) - 1))
                    bit_count += b
                    while bit_count >= 8:
                        shift = bit_count - 8
                        body.append((bit_buffer >> shift) & 0xFF)
                        bit_count -= 8
                        bit_buffer &= (1 << bit_count) - 1

                if bit_count > 0:
                    body.append((bit_buffer << (8 - bit_count)) & 0xFF)

    return header + bytes(body)


def decompress_matrix(data: bytes) -> np.ndarray:
    """
    Losslessly reconstruct the 2D counter matrix from compressed byte string.
    """
    d, w, group_size, dtype_code = struct.unpack(">HIHB", data[:9])
    dt = np.uint8 if dtype_code == 0 else (np.uint16 if dtype_code == 1 else np.uint32)
    min_size = 1 if dtype_code == 0 else (2 if dtype_code == 1 else 4)

    matrix = np.zeros((d, w), dtype=dt)
    offset = 9

    for row in range(d):
        col = 0
        while col < w:
            if dtype_code == 0:
                v_min, b, actual_size = struct.unpack(">BBB", data[offset:offset + 3])
                offset += 3
            elif dtype_code == 1:
                v_min, b, actual_size = struct.unpack(">HBB", data[offset:offset + 4])
                offset += 4
            else:
                v_min, b, actual_size = struct.unpack(">IBB", data[offset:offset + 6])
                offset += 6

            if b == 0:
                matrix[row, col:col + actual_size] = v_min
            else:
                # Unpack bits
                total_bits = actual_size * b
                total_bytes = (total_bits + 7) // 8
                chunk_bytes = data[offset:offset + total_bytes]
                offset += total_bytes

                bit_buffer = 0
                bit_count = 0
                byte_idx = 0
                mask = (1 << b) - 1

                for i in range(actual_size):
                    while bit_count < b and byte_idx < len(chunk_bytes):
                        bit_buffer = (bit_buffer << 8) | chunk_bytes[byte_idx]
                        bit_count += 8
                        byte_idx += 1

                    shift = bit_count - b
                    delta = (bit_buffer >> shift) & mask
                    bit_count -= b
                    bit_buffer &= (1 << bit_count) - 1
                    matrix[row, col + i] = v_min + delta

            col += actual_size

    return matrix
