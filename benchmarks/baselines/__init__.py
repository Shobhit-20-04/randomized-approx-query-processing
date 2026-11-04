"""
Baselines suite for comparative analysis of probabilistic data structures.
"""

from baselines.hash_utils import hash128, kirsch_mitzenmacher, extract_hll_bits
from baselines.bloom_filter import BloomFilter
from baselines.counting_bloom_filter import CountingBloomFilter
from baselines.cuckoo_filter import CuckooFilter
from baselines.xor_filter import XorFilter
from baselines.count_min_sketch import CountMinSketch
from baselines.count_sketch import CountSketch
from baselines.hyperloglog import HyperLogLog
from baselines.augmented_sketch import AugmentedSketch
from baselines.elastic_sketch import ElasticSketch
from baselines.disjoint_stack import DisjointStack

__all__ = [
    "hash128",
    "kirsch_mitzenmacher",
    "extract_hll_bits",
    "BloomFilter",
    "CountingBloomFilter",
    "CuckooFilter",
    "XorFilter",
    "CountMinSketch",
    "CountSketch",
    "HyperLogLog",
    "AugmentedSketch",
    "ElasticSketch",
    "DisjointStack",
]
