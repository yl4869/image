# DDL10 结果统计（main、resizing、fifo、fifo_batch、cf_batch 算法对比）

仅统计 main_time.json、resizing_time.json、fifo_time.json、fifo_batch_time.json、cf_batch_time.json；若某任务的 resizing_time.json 为 -1，则视为全部错失。
准确率按关键任务总数统计：未处理的关键任务视为预测错误、计入分母。

## 1) 关键任务总数（来自 task_files_ddl）
- DDL10 关键任务总数: 1140

## 2) 关键任务错失率（已处理关键任务/总关键任务）
- main 错失率: 0.1561  （已处理关键任务数: 962 / 总关键任务数: 1140）
- resizing 错失率: 0.9395  （已处理关键任务数: 69 / 总关键任务数: 1140）
- fifo 错失率: 0.8921  （已处理关键任务数: 123 / 总关键任务数: 1140）
- fifo_batch 错失率: 0.7763  （已处理关键任务数: 255 / 总关键任务数: 1140）
- cf_batch 错失率: 0.5386  （已处理关键任务数: 526 / 总关键任务数: 1140）

## 3) 关键任务准确率（以关键任务总数为分母，未处理视为错误）
- main 准确率: 0.5939
- resizing 准确率: 0.0430
- fifo 准确率: 0.0693
- fifo_batch 准确率: 0.1754
- cf_batch 准确率: 0.3491

## 4) 非关键任务处理量（条目数去重）
- main 非关键处理量: 423
- resizing 非关键处理量: 155
- fifo 非关键处理量: 473
- fifo_batch 非关键处理量: 662
- cf_batch 非关键处理量: 333
