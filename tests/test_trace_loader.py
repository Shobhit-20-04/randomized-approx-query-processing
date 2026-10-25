"""
Unit tests for network trace loader.
"""

from approx_query.trace_loader import generate_caida_like_trace


def test_generate_caida_like_trace():
    trace = generate_caida_like_trace(total_packets=5000, distinct_source_ips=200, seed=42)
    assert trace.total_packets == 5500  # 5000 + 500 attacker packets
    assert trace.distinct_flows > 500
    assert len(trace.heavy_hitters) > 0
    assert len(trace.super_spreaders) > 0
    # Super-spreader attacker should be detected
    top_spreader_ip, top_spreader_count = trace.super_spreaders[0]
    assert top_spreader_ip == "192.168.99.99"
    assert top_spreader_count >= 50
