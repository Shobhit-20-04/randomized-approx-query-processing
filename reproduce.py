"""Master Automated Reproduction Script for AdaLog-Sketch Case Study.

Authors: Shobhit Agrawal & Mayuri Rajendra Pawar (VIT Vellore)
Executes the full pipeline:
1. Environment pre-flight check and native C++ core compilation.
2. Invariant verification simulation (Theorem 1 proof & counterexample check).
3. All benchmark experiments (Exp 1 through Exp 8).
4. Automated figure generation into results/figures/.
5. Comprehensive results summary display.
"""

import os
import sys
import subprocess
import time

PYTHON_EXE = sys.executable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg: str):
    print(f"\n[REPRODUCE] {msg}")


def run_step(step_name: str, cmd_module: str):
    log(f"Executing {step_name} ({cmd_module})...")
    t0 = time.perf_counter()
    res = subprocess.run([PYTHON_EXE, "-m", cmd_module], cwd=BASE_DIR)
    t1 = time.perf_counter()
    if res.returncode != 0:
        print(f"[ERROR] Step {step_name} failed with exit code {res.returncode}")
        sys.exit(res.returncode)
    print(f"[DONE] {step_name} finished in {t1 - t0:.2f} seconds.")


def main():
    print("=" * 80)
    print("   ADALOG-SKETCH CASE STUDY: REPRODUCIBLE RESEARCH EXECUTION SUITE")
    print("   Authors: Shobhit Agrawal & Mayuri Rajendra Pawar (VIT Vellore)")
    print("=" * 80)

    # 1. Compile C++ Core if needed
    log("Verifying native compiled core...")
    core_dir = os.path.join(BASE_DIR, "core")
    dll_path = os.path.join(core_dir, "adalog_core.dll")
    if not os.path.exists(dll_path):
        log("Compiling adalog_core.dll with MSYS2 g++...")
        gxx = r"C:\msys64\ucrt64\bin\g++.exe"
        cmd = [gxx, "-O3", "-shared", "-static", "-static-libgcc", "-static-libstdc++", "-o", "adalog_core.dll", "adalog_core.cpp"]
        subprocess.run(cmd, cwd=core_dir, check=True)
    print(f"Native core verified at {dll_path}")

    # 2. Theory Invariant Simulation
    run_step("Theoretical Invariant Verification (N4)", "theory.simulate_proofs")

    # 3. Experiment 1: Memory Sweep Pareto Evaluation
    run_step("Experiment 1: Memory Sweep", "experiments.exp1_memory_sweep")

    # 4. Experiment 2: Skew Sensitivity Sweep
    run_step("Experiment 2: Skew Sensitivity", "experiments.exp2_skew_sweep")

    # 5. Experiment 3: Compiled C++ Latency & Throughput Benchmark
    run_step("Experiment 3: Compiled C++ Latency", "experiments.exp3_latency_benchmark")

    # 6. Experiment 4: Systematic Ablation Matrix
    run_step("Experiment 4: Ablation Matrix", "experiments.exp4_ablations")

    # 7. Experiment 5: Acceptance Test N1 (Planner)
    run_step("Experiment 5: Planner Acceptance (N1)", "experiments.exp5_planner_eval")

    # 8. Experiment 6: Acceptance Test N2 (Adaptive Controller)
    run_step("Experiment 6: Adaptive Controller Acceptance (N2)", "experiments.exp6_adaptive_eval")

    # 9. Experiment 7: Acceptance Test N3 (Certificates & Calibration)
    run_step("Experiment 7: Certificates & Calibration (N3)", "experiments.exp7_certificates_eval")

    # 10. Experiment 8: LightRanger Compression
    run_step("Experiment 8: Wire Compression", "experiments.exp8_compression")

    # 11. Plot all figures
    run_step("Automated Plot Generator", "experiments.plot_results")

    print("\n" + "=" * 80)
    print("REPRODUCTION COMPLETE! All experiments executed, validated, and plotted.")
    print("Raw data:    results/raw/")
    print("Figures:     results/figures/")
    print("=" * 80)


if __name__ == "__main__":
    main()
