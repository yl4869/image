#!/usr/bin/env python3
"""
根据 cf_batch_runs_average.csv 绘制执行时间趋势图。
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> int:
    base_dir = Path("generated_tasks/benchmark")
    input_csv = base_dir / "cf_batch_runs_average.csv"
    output_png = base_dir / "cf_batch_average_time_trend.png"

    if not input_csv.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_csv}")

    task_counts = []
    avg_ms = []

    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            task_counts.append(int(row["tasks_count"]))
            avg_ms.append(float(row["average_elapsed_ms"]))

    plt.figure(figsize=(9, 5))
    plt.plot(task_counts, avg_ms, marker="o", linewidth=2)
    plt.title("CF-BATCH Average Execution Time Trend")
    plt.xlabel("Task Count")
    plt.ylabel("Average Execution Time (ms)")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(output_png, dpi=160)
    print(output_png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
