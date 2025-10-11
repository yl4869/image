#include "function.h"
#include <stdio.h>


 int main() {
     // 示例任务（任务大小，截止时间,图像id）
     Task tasks[] = {
        {1, 1, "64_1"},   
        {1, 10.1,"64_2"},  
        {2,10.1,"128_1"},   
        {3,10.1,"256_1"},  
        {4,10.1,"512_1"},
        {0,0,""}   
    };
    sortTasksByDeadline(tasks);
    // 打开输出文件（当前目录）
    FILE *out = NULL;
    if (fopen_s(&out, "output.txt", "w") != 0 || !out) return 1;
    // 写入 UTF-8 BOM，帮助编辑器正确识别编码
    {
        unsigned char bom[3] = {0xEF, 0xBB, 0xBF};
        fwrite(bom, 1, 3, out);
    }
    // 初始化批次集合
    Batches batches;
    //动态调度任务（将输出写入文件）
    dynamicScheduling(&batches, tasks, out);
    // 释放内存
    for (int i = 0; i < batches.batch_count; i++)
    {
        free(batches.batches[i].tasks);
    }
    free(batches.batches);
    fclose(out);
    
     return 0;
 }
