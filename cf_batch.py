#!/usr/bin/env python3
"""
cf_batch.py
实现：CF-BATCH 调度器（优先关键任务、相同尺寸批处理、不进行压缩）
输出与 main.c 保持兼容：生成 output_cf_batch.json 和 missed_tasks_cf_batch.json
"""

import sys
import csv
import json
import time
from typing import List, Dict

# 时间模型（与 main.c 保持一致）
TRANS_TIME_SIZE = [0.75, 1.0, 1.7, 5.3]
PROC_TIME_SIZE_1D = [2.25, 3.5, 3.5, 1.8]


class Task:
    """任务类"""
    def __init__(self, size: int, deadline: float, task_id: str, crucial: int):
        self.size = size  # 1..4
        self.deadline = deadline
        self.id = task_id
        self.crucial = crucial  # 1 = crucial, 0 = non-crucial


def get_actual_size(internal_size: int) -> int:
    """根据内部尺寸索引获取实际尺寸"""
    size_map = {1: 64, 2: 128, 3: 256, 4: 512}
    return size_map.get(internal_size, internal_size)


def read_tasks_from_file(filename: str) -> List[Task]:
    """读取 CSV 文件中的任务"""
    tasks = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = None
            for row in reader:
                # 检查是否为表头
                if headers is None:
                    if len(row) >= 4 and 'size' in row[0].lower() and 'deadline' in row[1].lower():
                        headers = row
                        continue
                    else:
                        headers = []
                
                if len(row) < 4:
                    continue
                
                try:
                    size = int(row[0])
                    deadline = float(row[1])
                    task_id = row[2].strip()
                    crucial = int(row[3])
                    
                    # 如果有第5列（category），追加到 ID
                    if len(row) >= 5 and row[4].strip():
                        category = row[4].strip()
                        task_id = f"{task_id}_{category}"
                    
                    tasks.append(Task(size, deadline, task_id, crucial))
                except (ValueError, IndexError):
                    continue
    except FileNotFoundError:
        print(f"无法打开任务文件: {filename}", file=sys.stderr)
        return []
    
    return tasks


def main():
    task_file = sys.argv[1] if len(sys.argv) > 1 else "tasks.csv"
    
    # 记录算法开始时间
    start_time = time.time()
    # 读取任务
    tasks = read_tasks_from_file(task_file)
    if not tasks:
        print("没有读取到任何任务，退出。", file=sys.stderr)
        return 1
    
    task_count = len(tasks)
    
    
    # 计算全局最小 deadline
    global_deadline = min(task.deadline for task in tasks)
    
    # 将任务分组：按 size（1..4）分别统计 crucial 与 non-crucial
    crucial_lists = {i: [] for i in range(1, 5)}
    noncrucial_lists = {i: [] for i in range(1, 5)}
    
    for task in tasks:
        if task.size < 1 or task.size > 4:
            continue
        if task.crucial:
            crucial_lists[task.size].append(task)
        else:
            noncrucial_lists[task.size].append(task)
    
    # 构造批次信息（关键任务批次）
    crucial_batches = []
    for size in range(1, 5):
        if crucial_lists[size]:
            earliest_deadline = min(t.deadline for t in crucial_lists[size])
            crucial_batches.append({
                'size_idx': size - 1,  # 0..3
                'count': len(crucial_lists[size]),
                'tasks': crucial_lists[size],
                'earliest_deadline': earliest_deadline
            })
    
    # 按 earliest_deadline 排序
    crucial_batches.sort(key=lambda x: x['earliest_deadline'])
    
    # 标记每个任务是否已被调度或错过（0=未处理，1=已调度，-1=错失）
    processed = {i: 0 for i in range(task_count)}
    task_to_idx = {id(t): i for i, t in enumerate(tasks)}
    
    # 对非关键任务按 deadline 排序（每个尺寸内部）
    for size in range(1, 5):
        if len(noncrucial_lists[size]) > 1:
            noncrucial_lists[size].sort(key=lambda t: t.deadline)
    
    # 缓冲的已调度批次
    scheduled = []
    accumulated_time = 0.0
    crucial_scheduled_flags = {i: False for i in range(1, 5)}
    
    # 处理关键任务批次
    for batch in crucial_batches:
        size_idx = batch['size_idx']
        batch_time = TRANS_TIME_SIZE[size_idx] * batch['count'] + PROC_TIME_SIZE_1D[size_idx]
        
        if (accumulated_time + batch_time) <= global_deadline:
            # 可调度
            scheduled.append({
                'size_idx': size_idx,
                'count': batch['count'],
                'tasks': batch['tasks'][:],
                'is_crucial': 1
            })
            crucial_scheduled_flags[batch['size_idx'] + 1] = True
            
            # 标记为已调度
            for task in batch['tasks']:
                processed[task_to_idx[id(task)]] = 1
            
            accumulated_time += batch_time
        else:
            # 标记关键任务为错失
            for task in batch['tasks']:
                processed[task_to_idx[id(task)]] = -1
    
    # 合并非关键任务到已调度的关键任务批次
    stop_due_to_timeout = False
    noncrucial_read_idx = {i: 0 for i in range(1, 5)}
    
    for size in range(1, 5):
        if stop_due_to_timeout:
            break
        if not crucial_scheduled_flags[size]:
            continue
        
        # 找到对应尺寸的关键批次
        for batch_idx, batch in enumerate(scheduled):
            if stop_due_to_timeout:
                break
            if batch['is_crucial'] != 1 or (batch['size_idx'] + 1) != size:
                continue
            
            # 逐个尝试添加非关键任务
            while noncrucial_read_idx[size] < len(noncrucial_lists[size]):
                extra = TRANS_TIME_SIZE[size - 1]
                
                if (accumulated_time + extra) <= global_deadline:
                    # 可以添加
                    task = noncrucial_lists[size][noncrucial_read_idx[size]]
                    batch['tasks'].append(task)
                    batch['count'] += 1
                    processed[task_to_idx[id(task)]] = 1
                    noncrucial_read_idx[size] += 1
                    accumulated_time += extra
                else:
                    stop_due_to_timeout = True
                    break
    
    # 对于没有关键批次的尺寸，尝试直接作为非关键批次整体调度
    for size in range(1, 5):
        if stop_due_to_timeout:
            break
        if crucial_scheduled_flags[size]:
            continue
        
        remaining = len(noncrucial_lists[size]) - noncrucial_read_idx[size]
        if remaining <= 0:
            continue
        
        size_idx = size - 1
        batch_time = TRANS_TIME_SIZE[size_idx] * remaining + PROC_TIME_SIZE_1D[size_idx]
        
        if (accumulated_time + batch_time) <= global_deadline:
            scheduled.append({
                'size_idx': size_idx,
                'count': remaining,
                'tasks': noncrucial_lists[size][noncrucial_read_idx[size]:],
                'is_crucial': 0
            })
            
            for task in noncrucial_lists[size][noncrucial_read_idx[size]:]:
                processed[task_to_idx[id(task)]] = 1
            
            accumulated_time += batch_time
            noncrucial_read_idx[size] = len(noncrucial_lists[size])
        else:
            stop_due_to_timeout = True
            break
    
    # 标记未调度的任务为错失
    if stop_due_to_timeout:
        for i in range(task_count):
            if processed[i] == 0:
                processed[i] = -1
    else:
        for i in range(task_count):
            if processed[i] == 0:
                processed[i] = -1
    
    # 记录算法结束时间
    end_time = time.time()
    elapsed = (end_time - start_time) * 1000.0  # 转换为毫秒
    
    # 将计时结果追加写入 CSV
    with open("cf_batch_timing.csv", "a") as tf:
        tf.write(f"{elapsed:.3f}\n")
    
    # 生成 output_cf_batch.json
    output_data = []
    for batch in scheduled:
        batch_item = {
            "size": get_actual_size(batch['size_idx'] + 1),
            "images": [
                {"id": task.id, "crucial": task.crucial}
                for task in batch['tasks']
            ]
        }
        output_data.append(batch_item)
    
    # 添加 deadline
    output_data.append({"deadline": global_deadline})
    
    with open("output_cf_batch.json", "w", encoding='utf-8') as out:
        json.dump(output_data, out, indent=2, ensure_ascii=False)
    
    # 计算错失统计
    missed_total = sum(1 for p in processed.values() if p == -1)
    missed_crucial = sum(1 for i, p in processed.items() if p == -1 and tasks[i].crucial)
    missed_noncrucial = missed_total - missed_crucial
    
    # 生成 missed_tasks_cf_batch.json
    if missed_total > 0:
        missed_details = []
        for i, task in enumerate(tasks):
            if processed[i] == -1:
                missed_details.append({
                    "id": task.id,
                    "size": task.size,
                    "deadline": task.deadline,
                    "crucial": task.crucial
                })
        
        missed_data = {
            "total_tasks": task_count,
            "completed_tasks": task_count - missed_total,
            "missed_tasks": missed_total,
            "missed_crucial": missed_crucial,
            "missed_non_crucial": missed_noncrucial,
            "deadline": global_deadline,
            "accumulated_time": accumulated_time,
            "missed_task_details": missed_details
        }
        
        with open("missed_tasks_cf_batch.json", "w", encoding='utf-8') as mf:
            json.dump(missed_data, mf, indent=2, ensure_ascii=False)
    
    # 打印统计
    completed = task_count - missed_total
    print(f"调度完成：总任务={task_count}, 已完成={completed}, 错失={missed_total}, 累计时间={accumulated_time:.6f}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
