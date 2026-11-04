"""
Run full comprehensive benchmark suite.
Executes complete parameter sweeps across dataset sizes, generates CSVs, plots, and research report.
"""

import os
import sys

# Ensure src is in python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from approx_query.benchmarking import BenchmarkRunner
from approx_query.plotting import generate_all_plots
from approx_query.reporting import generate_academic_report


def main():
    print("=" * 70)
    print("RUNNING FULL M.TECH RESEARCH BENCHMARK SUITE")
    print("=" * 70)

    config_path = os.path.join(project_root, "configs", "full.yaml")
    results_dir = os.path.join(project_root, "results")
    plots_dir = os.path.join(results_dir, "plots")
    report_path = os.path.join(project_root, "reports", "research_report.md")

    runner = BenchmarkRunner(config_path=config_path, output_dir=results_dir)
    df_bf, df_cms, df_hll = runner.run_all()

    print("\nGenerating publication-quality plots...")
    plot_files = generate_all_plots(df_bf, df_cms, df_hll, output_dir=plots_dir)
    print(f"Generated {len(plot_files)} plots in {plots_dir}")

    print("\nSynthesizing academic research report...")
    generated_report = generate_academic_report(df_bf, df_cms, df_hll, output_path=report_path)
    print(f"Report generated at: {generated_report}")
    print("=" * 70)
    print("FULL BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
