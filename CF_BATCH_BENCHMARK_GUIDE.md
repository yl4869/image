# CF-BATCH 批量测试与可视化使用方案

本文档用于在其他电脑上复现整套流程：
1. 随机生成任务 CSV  
2. 按任务规模批量运行 `cf_batch.py`  
3. 统计每个规模的平均执行时间  
4. 绘制趋势图观察变化

## 1. 文件说明

请确保以下文件在项目根目录（`/home/yunlang/image`）：

- `cf_batch.py`：CF-BATCH 调度算法，运行后会输出单次耗时（stdout）并写入 `cf_batch_timing.csv`
- `generate_random_tasks_csv.py`：随机任务生成器（当前 `deadline` 固定为 `100.0` ms）
- `benchmark_cf_batch.py`：批量生成 + 批量运行 + 平均值汇总
- `plot_cf_batch_trend.py`：根据平均结果画趋势图

## 2. 环境准备

建议使用 Python 3.9+。

```bash
python3 --version
```

安装绘图依赖（仅画图脚本需要）：

```bash
python3 -m pip install matplotlib
```

## 3. 单次生成与运行（可选）

先做一次最小验证：

```bash
python3 generate_random_tasks_csv.py 100 --file-name tasks_100_demo.csv --out-dir generated_tasks/demo --seed 42
python3 cf_batch.py generated_tasks/demo/tasks_100_demo.csv
```

说明：
- 第二条命令会在终端输出类似 `0.123ms`
- 同时会在项目根目录追加写入 `cf_batch_timing.csv`

## 4. 正式批量测试（你的目标流程）

执行下面一条命令即可：

```bash
python3 benchmark_cf_batch.py --start 10 --end 200 --step 10 --repeat 10
```

这条命令会自动完成：
- 任务规模：`10,20,30,...,200`
- 每个规模随机生成 `10` 份 CSV
- 每份都运行一次 `cf_batch.py`
- 计算每个规模的平均执行时间

## 5. 结果文件位置

批量测试完成后，结果在：

- 明细（每次运行一行）  
  `generated_tasks/benchmark/cf_batch_runs_detailed.csv`
- 平均值（每个任务规模一行）  
  `generated_tasks/benchmark/cf_batch_runs_average.csv`
- 生成的测试数据  
  `generated_tasks/benchmark/csv_files/`

## 6. 绘制趋势图

执行：

```bash
python3 plot_cf_batch_trend.py
```

输出图片：

- `generated_tasks/benchmark/cf_batch_average_time_trend.png`

图含义：
- X 轴：任务数量（10 到 200）
- Y 轴：平均执行时间（毫秒）
- 每个点：该规模 10 次运行的平均值

## 7. 一键复现实验命令清单

在项目根目录依次运行：

```bash
python3 -m pip install matplotlib
python3 benchmark_cf_batch.py --start 10 --end 200 --step 10 --repeat 10
python3 plot_cf_batch_trend.py
```

## 8. 常见问题排查

1. `ModuleNotFoundError: matplotlib`  
执行：
```bash
python3 -m pip install matplotlib
```

2. `cf_batch.py` 报“没有读取到任何任务”  
通常是传入的 CSV 路径错误，检查文件是否存在。

3. 看不到计时文件内容  
`cf_batch.py` 写入的是项目根目录下的 `cf_batch_timing.csv`。  
请确认你查看的是同一个目录中的文件。

4. 想改实验规模  
例如改为 50 到 500，步长 50，每个规模跑 20 次：
```bash
python3 benchmark_cf_batch.py --start 50 --end 500 --step 50 --repeat 20
```

## 9. 结果解读建议

- 优先看 `cf_batch_runs_average.csv`：用于比较不同任务规模的总体趋势
- 再看 `cf_batch_runs_detailed.csv`：用于定位离群值或抖动
- 通过趋势图快速判断算法耗时是否随规模增长而近似线性

