#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
// 定义任务结构体
typedef struct {
    int size;            // 图像大小
    float deadline;       // 截止时间
    char id[50];  //图片代号
} Task;

typedef struct{
    Task *tasks;          // 任务数组
    int task_count;       // 任务数量
    int size;            // 图像大小
}TaskQueue;

// 定义批次结构体
typedef struct {
    TaskQueue *taskQueue;          // 批次内任务数组
    int Queue_count;       // 批次内任务数量
    int stage;              // 批次阶段
    float start_time;     // 批次开始时间（暂未用到）
    float end_time;       // 批次结束时间（暂未用到）
    float deadline;       // 批次的截止时间
    int size;              // 批次处理的图像大小(1-4)
} Batch;



// 定义批次集合结构体（队列）
typedef struct {
    Batch *batches;       // 批次数组
    int batch_count;      // 批次数量（可以去掉，因为在实际实现时发现直接把4个序列全初始化更加方便）
    float deadline;       //获取最紧急任务的截止期
    float current_time;    //记录当前的时间
} Batches;
//对大小提前做一个映射（64->1,128->2,256->3,512->4）
//第一维是原始大小（0是64，1是128，2是256，3是512）
//第二维是压缩后大小（0是64，1是128，2是256，3是512）
//第三维是执行阶段（0是阶段1，1是阶段2，2是阶段3，3是阶段4）
float accuracy[4][4][4] = {
    {
        {0.33f, 0.50f, 0.54f, 0.54f}, 
        {0.42f, 0.53f, 0.64f, 0.71f},  
        {0.44f, 0.69f, 0.75f, 0.77f},  
        {0.23f, 0.68f, 0.77f, 0.78f}   
    },
    {
        {0.45f, 0.63f, 0.66f, 0.67f},
        {0.54f, 0.63f, 0.69f, 0.75f},
        {0.59f, 0.79f, 0.82f, 0.82f},
        {0.33f, 0.75f, 0.82f, 0.85f}
    },
    {
        {0.48f, 0.59f, 0.64f, 0.65f},
        {0.54f, 0.62f, 0.67f, 0.72f},
        {0.63f, 0.77f, 0.83f, 0.84f},
        {0.30f, 0.76f, 0.84f, 0.86f}
    },
    {
        {0.53f, 0.64f, 0.67f, 0.69f},
        {0.53f, 0.67f, 0.73f, 0.77f},
        {0.54f, 0.73f, 0.84f, 0.86f},
        {0.34f, 0.76f, 0.84f, 0.87f}
    }
};
float worst_accuracy[4]={0.40f,0.60f,0.70f,0.70f};//用于假设对于不同大小的任务的最差准确率要求已经给出
float trans_time_size[4]={0.1,0.2,0.3,0.4};//假设对应四个尺寸的传输时间（kx+b中的k）
float proc_time_size[4][4]={
    {0.03,0.05,0.06,0.07},
    {0.04,0.06,0.08,0.10},
    {0.05,0.07,0.10,0.12},
    {0.06,0.09,0.12,0.15}
};//假设在不同大小的不同阶段的执行时间（kx+b中的b），第一维代表执行大小，第二维是阶段数





// 函数声明
int compareByDeadline(const void* a, const void* b) ;
int get_num_tasks(Task *tasks);
int compress_batch( Batches *batches);
void calculate_current_time(Batches *batches); 
int findMinTargetSizeTask(TaskQueue *taskQueue);
void transfer_batch_tasks(Batch *source, Batch *destination);
void GPU_process(Batch *batch, FILE *out);
void init_batches(Batches *batches,Task *tasks);
void sortTasksByDeadline(Task* tasks);
int findBatchIndexBySize(Batches *batches, int size);
void dynamicScheduling(Batches *batches, Task *tasks, FILE *out);
void appendTaskToQueue(TaskQueue *taskQueue, Task *task);
int get_actual_size(int internal_size);






