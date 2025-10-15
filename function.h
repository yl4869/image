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
// 全局变量声明
extern float accuracy[4][4][4];
extern float worst_accuracy[4];
extern float trans_time_size[4];
extern float proc_time_size[4][4];





// 函数声明
int compareByDeadline(const void* a, const void* b) ;
int get_num_tasks(Task *tasks);
int compress_batch( Batches *batches);
void calculate_current_time(Batches *batches); 
int findMinTargetSizeTask(TaskQueue *taskQueue);
void transfer_batch_tasks(TaskQueue *source, Batch *destination);
void GPU_process(Batch *batch, FILE *out);
void init_batches(Batches *batches,Task *tasks);
void sortTasksByDeadline(Task* tasks);
int findBatchIndexBySize(Batches *batches, int size);
void dynamicScheduling(Batches *batches, Task *tasks, FILE *out);
void appendTaskToQueue(TaskQueue *taskQueue, Task *task);
int get_actual_size(int internal_size);






