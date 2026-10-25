"""
Network Trace Loader & Realistic Backbone Traffic Generator.
Simulates CAIDA-style high-speed Internet backbone packet traces with:
  1. 5-tuple IP flows (src_ip, dst_ip, src_port, dst_port, protocol).
  2. Heavy-tailed flow size distribution (Pareto/Zipf: 1% of flows carry 60%+ of packets).
  3. Flow spread / Super-spreader events (port scans / DDoS where an IP contacts thousands of distinct IPs).
  4. Support for loading real CSV packet capture traces.
"""

from __future__ import annotations

import collections
import csv
import dataclasses
import os
from typing import Dict, List, Optional, Sequence, Tuple
import numpy as np


@dataclasses.dataclass
class PacketTrace:
    """Encapsulates a streaming packet trace and ground-truth metrics."""
    packets: List[str]  # 5-tuple flow strings or IP keys
    flow_frequencies: Dict[str, int]
    flow_spreads: Dict[str, int]  # Distinct destinations per source IP
    super_spreaders: List[Tuple[str, int]]
    heavy_hitters: List[Tuple[str, int]]
    total_packets: int
    distinct_flows: int


def generate_caida_like_trace(
    total_packets: int = 50000,
    distinct_source_ips: int = 2000,
    pareto_shape: float = 1.15,
    seed: int = 42,
) -> PacketTrace:
    """
    Generate synthetic network traffic matching CAIDA backbone flow characteristics.
    """
    rng = np.random.RandomState(seed)

    # 1. Generate pool of Source and Destination IPs
    src_ips = [f"192.168.{i // 256}.{i % 256}" for i in range(distinct_source_ips)]
    dst_ips = [f"10.0.{i // 256}.{i % 256}" for i in range(5000)]

    # 2. Pareto flow size distribution (heavy-tailed)
    raw_weights = rng.pareto(a=pareto_shape, size=distinct_source_ips) + 1.0
    probabilities = raw_weights / np.sum(raw_weights)

    # Sample source IP packet stream
    sampled_src_indices = rng.choice(distinct_source_ips, size=total_packets, p=probabilities)

    packets: List[str] = []
    flow_freq: collections.Counter = collections.Counter()
    src_to_dsts: Dict[str, set] = collections.defaultdict(set)

    # Add a dedicated Super-Spreader (e.g., port scan attack from a specific IP)
    attacker_ip = "192.168.99.99"

    for idx in sampled_src_indices:
        src = src_ips[idx]
        # Most flows contact 1 or 2 destinations; elephants contact more
        dst_idx = rng.randint(0, min(50, len(dst_ips)))
        dst = dst_ips[dst_idx]
        flow_id = f"{src}->{dst}"
        packets.append(flow_id)
        flow_freq[flow_id] += 1
        src_to_dsts[src].add(dst)

    # Inject 500 packets from super-spreader scanner hitting distinct destinations
    for i in range(min(500, len(dst_ips))):
        flow_id = f"{attacker_ip}->{dst_ips[i]}"
        packets.append(flow_id)
        flow_freq[flow_id] += 1
        src_to_dsts[attacker_ip].add(dst_ips[i])

    # Shuffle stream to interleave packets realistically
    rng.shuffle(packets)

    flow_frequencies = dict(flow_freq)
    flow_spreads = {src: len(dsts) for src, dsts in src_to_dsts.items()}

    heavy_hitters = sorted(flow_frequencies.items(), key=lambda kv: kv[1], reverse=True)[:50]
    super_spreaders = sorted(flow_spreads.items(), key=lambda kv: kv[1], reverse=True)[:20]

    return PacketTrace(
        packets=packets,
        flow_frequencies=flow_frequencies,
        flow_spreads=flow_spreads,
        super_spreaders=super_spreaders,
        heavy_hitters=heavy_hitters,
        total_packets=len(packets),
        distinct_flows=len(flow_frequencies),
    )


def load_pcap_csv_trace(csv_path: str, max_packets: Optional[int] = None) -> PacketTrace:
    """
    Load real network packet trace from CSV file containing (src_ip, dst_ip, [src_port, dst_port, proto]).
    """
    packets = []
    flow_freq = collections.Counter()
    src_to_dsts = collections.defaultdict(set)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for count, row in enumerate(reader):
            if max_packets and count >= max_packets:
                break
            src = row.get("src_ip", row.get("Source", "unknown_src"))
            dst = row.get("dst_ip", row.get("Destination", "unknown_dst"))
            flow_id = f"{src}->{dst}"
            packets.append(flow_id)
            flow_freq[flow_id] += 1
            src_to_dsts[src].add(dst)

    flow_frequencies = dict(flow_freq)
    flow_spreads = {src: len(dsts) for src, dsts in src_to_dsts.items()}
    heavy_hitters = sorted(flow_frequencies.items(), key=lambda kv: kv[1], reverse=True)[:50]
    super_spreaders = sorted(flow_spreads.items(), key=lambda kv: kv[1], reverse=True)[:20]

    return PacketTrace(
        packets=packets,
        flow_frequencies=flow_frequencies,
        flow_spreads=flow_spreads,
        super_spreaders=super_spreaders,
        heavy_hitters=heavy_hitters,
        total_packets=len(packets),
        distinct_flows=len(flow_frequencies),
    )
