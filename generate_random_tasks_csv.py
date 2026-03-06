#!/usr/bin/env python3
"""
生成与 tasks CSV 类似格式的随机任务文件。

输出字段:
size,deadline,id,crucial,category
"""

import argparse
import csv
import os
import random
from datetime import datetime


SIZE_TO_ACTUAL = {
    1: 64,
    2: 128,
    3: 256,
    4: 512,
}

DEFAULT_CATEGORIES = ["car", "person", "bicycle", "bus", "truck"]
FIXED_DEADLINE_MS = 100.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="随机生成任务 CSV 文件。"
    )
    parser.add_argument(
        "count",
        type=int,
        help="要生成的数据条目数，例如 100。",
    )
    parser.add_argument(
        "--out-dir",
        default="generated_tasks",
        help="输出目录（默认: generated_tasks）。",
    )
    parser.add_argument(
        "--file-name",
        default=None,
        help="输出文件名（默认自动生成）。",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（可选，便于复现）。",
    )
    parser.add_argument(
        "--crucial-prob",
        type=float,
        default=0.25,
        help="crucial=1 的概率，范围 [0,1]（默认: 0.25）。",
    )
    return parser


def validate_args(count: int, crucial_prob: float) -> None:
    if count <= 0:
        raise ValueError("count 必须大于 0。")
    if not (0.0 <= crucial_prob <= 1.0):
        raise ValueError("crucial-prob 必须在 [0, 1] 范围内。")


def generate_rows(count: int, crucial_prob: float) -> list[list[object]]:
    counters = {size: 0 for size in SIZE_TO_ACTUAL}
    rows: list[list[object]] = []

    for _ in range(count):
        size = random.randint(1, 4)
        deadline = FIXED_DEADLINE_MS
        category = random.choice(DEFAULT_CATEGORIES)
        crucial = 1 if random.random() < crucial_prob else 0

        idx = counters[size]
        counters[size] += 1
        task_id = f"{SIZE_TO_ACTUAL[size]}_{idx}"

        rows.append([size, deadline, task_id, crucial, category])

    return rows


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args.count, args.crucial_prob)
    except ValueError as err:
        parser.error(str(err))

    if args.seed is not None:
        random.seed(args.seed)

    os.makedirs(args.out_dir, exist_ok=True)

    if args.file_name:
        file_name = args.file_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"tasks_{args.count}_{timestamp}.csv"

    output_path = os.path.join(args.out_dir, file_name)
    rows = generate_rows(args.count, args.crucial_prob)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["size", "deadline", "id", "crucial", "category"])
        writer.writerows(rows)

    print(f"已生成 {args.count} 条数据: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
