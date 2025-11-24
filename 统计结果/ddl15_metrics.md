# DDL15 结果统计（main、resizing、fifo、fifo_batch、cf_batch 算法对比）

仅统计 main_time.json、resizing_time.json、fifo_time.json、fifo_batch_time.json、cf_batch_time.json；若某任务的 resizing_time.json 为 -1，则视为全部错失。
准确率按关键任务总数统计：未处理的关键任务视为预测错误、计入分母。

## 1) 关键任务总数（来自 task_files_ddl）
- DDL15 关键任务总数: 1140

## 2) 关键任务错失率（已处理关键任务/总关键任务）
- main 错失率: 0.0096  （已处理关键任务数: 1129 / 总关键任务数: 1140）
- resizing 错失率: 0.6228  （已处理关键任务数: 430 / 总关键任务数: 1140）
- fifo 错失率: 0.8228  （已处理关键任务数: 202 / 总关键任务数: 1140）
- fifo_batch 错失率: 0.5912  （已处理关键任务数: 466 / 总关键任务数: 1140）
- cf_batch 错失率: 0.3184  （已处理关键任务数: 777 / 总关键任务数: 1140）

## 3) 关键任务准确率（以关键任务总数为分母，未处理视为错误）
- main 准确率: 0.7009
- resizing 准确率: 0.2719
- fifo 准确率: 0.1167
- fifo_batch 准确率: 0.2974
- cf_batch 准确率: 0.5079

## 4) 非关键任务处理量（条目数去重）
- main 非关键处理量: 1205
- resizing 非关键处理量: 859
- fifo 非关键处理量: 785
- fifo_batch 非关键处理量: 1527
- cf_batch 非关键处理量: 599
