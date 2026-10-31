# Master Makefile for AdaLog-Sketch Paper Reproduction
# Strictly adheres to DSA principles and verified numerical reproduction.

PYTHON = python
GXX = g++

.PHONY: all reproduce test benchmark clean

all: reproduce

reproduce:
	$(PYTHON) scripts/run_all.py

test:
	$(PYTHON) -m pytest tests/

benchmark:
	$(GXX) -O3 -std=c++17 -static -static-libgcc -static-libstdc++ -o core/bench_core.exe core/bench_core.cpp
	./core/bench_core.exe results/raw/exp3_latency_benchmark.json

clean:
	rm -f core/*.exe core/*.o results/raw/*.tmp
