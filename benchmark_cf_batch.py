#!/usr/bin/env python3
"""
批量生成任务并测试 cf_batch.py：
1) 对每个任务规模（默认 10..200，步长 10）生成多份 CSV
2) 逐个执行 cf_batch.py
3) 记录单次耗时与每个规模的平均耗时
"""

import argparse
import csv
import subprocess
from pathlib import Path


def parse_elapsed_ms(stdout: str) -> float:
    text = stdout.strip()
    if not text.endswith("ms"):
        raise ValueError(f"无法解析耗时输出: {text}")
    return float(text[:-2])


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="CF-BATCH 批量基准测试")
    parser.add_argument("--start", type=int, default=10, help="起始任务数（默认 10）")
    parser.add_argument("--end", type=int, default=200, help="结束任务数（默认 200）")
    parser.add_argument("--step", type=int, default=10, help="任务数步长（默认 10）")
    parser.add_argument("--repeat", type=int, default=10, help="每个任务规模重复次数（默认 10）")
    parser.add_argument(
        "--out-dir",
        default="generated_tasks/benchmark",
        help="测试数据与结果输出目录",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    csv_dir = out_dir / "csv_files"
    csv_dir.mkdir(parents=True, exist_ok=True)

    detailed_path = out_dir / "cf_batch_runs_detailed.csv"
    average_path = out_dir / "cf_batch_runs_average.csv"

    with detailed_path.open("w", newline="", encoding="utf-8") as df:
        writer = csv.writer(df)
        writer.writerow(["tasks_count", "run_index", "csv_file", "elapsed_ms"])

        averages: list[tuple[int, float]] = []

        for n in range(args.start, args.end + 1, args.step):
            elapsed_values: list[float] = []
            for i in range(1, args.repeat + 1):
                file_name = f"tasks_{n}_run_{i}.csv"
                file_path = csv_dir / file_name
                seed = n * 1000 + i

                run_cmd(
                    [
                        "python3",
                        "generate_random_tasks_csv.py",
                        str(n),
                        "--file-name",
                        file_name,
                        "--out-dir",
                        str(csv_dir),
                        "--seed",
                        str(seed),
                    ]
                )

                result = run_cmd(["python3", "cf_batch.py", str(file_path)])
                elapsed_ms = parse_elapsed_ms(result.stdout)
                elapsed_values.append(elapsed_ms)
                writer.writerow([n, i, str(file_path), f"{elapsed_ms:.3f}"])

            avg_ms = sum(elapsed_values) / len(elapsed_values)
            averages.append((n, avg_ms))
            print(f"tasks={n}, avg={avg_ms:.3f}ms")

    with average_path.open("w", newline="", encoding="utf-8") as af:
        writer = csv.writer(af)
        writer.writerow(["tasks_count", "repeat", "average_elapsed_ms"])
        for n, avg_ms in averages:
            writer.writerow([n, args.repeat, f"{avg_ms:.3f}"])

    print(f"详细结果: {detailed_path}")
    print(f"平均结果: {average_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
