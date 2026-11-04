"""
Regenerate plots and research report from existing CSV results.
"""

import os
import sys
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from approx_query.plotting import generate_all_plots
from approx_query.reporting import generate_academic_report


def main():
    raw_dir = os.path.join(project_root, "results", "raw")
    plots_dir = os.path.join(project_root, "results", "plots")
    report_path = os.path.join(project_root, "reports", "research_report.md")

    bf_csv = os.path.join(raw_dir, "bloom_filter_raw.csv")
    cms_csv = os.path.join(raw_dir, "count_min_sketch_raw.csv")
    hll_csv = os.path.join(raw_dir, "hyperloglog_raw.csv")

    if not (os.path.exists(bf_csv) and os.path.exists(cms_csv) and os.path.exists(hll_csv)):
        print("Error: Benchmark CSV results not found in results/raw/.")
        print("Run 'python scripts/run_quick_benchmark.py' first.")
        sys.exit(1)

    df_bf = pd.read_csv(bf_csv)
    df_cms = pd.read_csv(cms_csv)
    df_hll = pd.read_csv(hll_csv)

    print("Generating plots...")
    generate_all_plots(df_bf, df_cms, df_hll, output_dir=plots_dir)

    print("Generating research report...")
    generate_academic_report(df_bf, df_cms, df_hll, output_path=report_path)

    print(f"Report regenerated successfully at {report_path}")


if __name__ == "__main__":
    main()
