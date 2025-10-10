#include "function.h"


 int main() {
     // 示例任务（任务大小，截止时间,图像id）
     Task tasks[] = {
        {1, 1, "64_1"},   
        {1, 1.1,"64_2"},  
        {2,1.1,"128_1"},   
        {3,1.1,"256_1"},  
        {4,1.1,"512_1"}   
    };
    int num_tasks = get_num_tasks(tasks);
    sortTasksByDeadline(tasks, num_tasks);
    // 初始化批次集合
    Batches batches;
    batches.max_size = 4;
    batches.batches = (Batch *)malloc(batches.max_size * sizeof(Batch));
    //动态调度任务
    dynamicScheduling(&batches, tasks, num_tasks);

    // 释放内存
    for (int i = 0; i < batches.batch_count; i++)
    {
        free(batches.batches[i].tasks);
    }
    free(batches.batches);
    
     return 0;
 }
