#include "function.h"

// 全局变量定义
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

float worst_accuracy[4] = {0.40f, 0.60f, 0.70f, 0.85f}; // 用于假设对于不同大小的任务的最差准确率要求已经给出

float trans_time_size[4] = {0.1, 0.2, 0.3, 0.4}; // 假设对应四个尺寸的传输时间（kx+b中的k）

float proc_time_size[4][4] = {
    {0.03, 0.05, 0.06, 0.07},
    {0.04, 0.06, 0.08, 0.10},
    {0.05, 0.07, 0.10, 0.12},
    {0.06, 0.09, 0.12, 0.15}
}; // 假设在不同大小的不同阶段的执行时间（kx+b中的b），第一维代表执行大小，第二维是阶段数


// 排序比较函数，根据任务的截止时间进行升序排序
int compareByDeadline(const void* a, const void* b) {
    Task* taskA = (Task*)a;
    Task* taskB = (Task*)b;

    // 根据 deadline 升序排列
    if (taskA->deadline < taskB->deadline) return -1;
    if (taskA->deadline > taskB->deadline) return 1;
    return 0;
}

// 排序任务队列（按截止期）
void sortTasksByDeadline(Task* tasks) {
    int num_tasks = get_num_tasks(tasks);
    qsort(tasks, num_tasks, sizeof(Task), compareByDeadline);
}
// 找到已有批次（返回这个尺寸任务应该被划分到第几个批次）
int findBatchIndexBySize(Batches *batches, int size) {
    for (int i = 0; i < 4; i++) {
        for(int j=0;j < batches->batches[i].Queue_count;j++)
        if (batches->batches[i].taskQueue[j].size == size) {
            return i;
        }
    }
    return -1;  // 返回 -1 表示没有找到匹配的批次
}

// 添加任务到批次
void appendTaskToQueue(TaskQueue *taskQueue, Task *task) {
    taskQueue->tasks = (Task*)realloc(taskQueue->tasks, (taskQueue->task_count+ 1) * sizeof(Task));
    taskQueue->tasks[taskQueue->task_count] = *task;
    taskQueue->task_count++;
}

//计算batches的总时间（对有任务的批次时间求和）
void calculate_current_time(Batches *batches)
{   batches->current_time = 0.0f; 
    int x;//任务数量
    for(int i=0;i<4;i++)
    {   
        if(batches->batches[i].Queue_count==0) continue;
        x=0;
        float k=trans_time_size[i];//传输时间
        for(int j=0;j<batches->batches[i].Queue_count;j++)
        {
            x+=batches->batches[i].taskQueue[j].task_count;
        }
        float b=proc_time_size[i][3];//阶段时间
        batches->current_time+=k*x+b;
    }
}
void init_batches(Batches *batches,Task *tasks)//初始化批次集合
{
    batches->batch_count = 4;
    batches->current_time = 0.0f;
    batches->deadline = tasks[0].deadline; // 假设第一个任务的截止时间是整体的截止时间
    batches->batches = (Batch *)malloc(batches->batch_count * sizeof(Batch));//分内存
    // 初始化四个批次
    for (int i = 0; i < 4; i++) 
    {
        Batch *batch = &batches->batches[i];
        batch->Queue_count=1;
        batch->taskQueue = (TaskQueue *)malloc(batch->Queue_count * sizeof(TaskQueue));
        batch->taskQueue[0].size = i + 1; // 初始化任务队列的大小
        batch->taskQueue[0].tasks = NULL; // 初始化任务数组为空
        batch->taskQueue[0].task_count = 0; // 初始化任务数量为0
        batch->end_time = 0.0f;
        batch->deadline = 0.0f;
        batch->start_time=0.0f;
        batch->stage = 3;
        batch->size = i + 1; // 批次处理的图像大小(1-4)
    }
}

// 压缩批次操作，压缩超时的批次
int compress_batch(Batches *batches) 
{   
    for(int i=3;i>=0;i--)//按尺寸从大到小遍历，因为是压缩到最小
    {   
        int original_count = batches->batches[i].Queue_count;
        for(int j=0;j<original_count;j++)
        {
            if(batches->batches[i].taskQueue[j].task_count==0) continue;
            //该批次内没有任务
            int batche_index= findMinTargetSizeTask(&batches->batches[i].taskQueue[j]);//找到当前批次内任务能最小缩到哪个尺寸
            if(batche_index==-1 || batche_index==i) continue;//不能再缩了或者缩到自己
            transfer_batch_tasks(&batches->batches[i].taskQueue[j], &batches->batches[batche_index]);
            batches->batches[i].taskQueue[j].tasks=NULL;
            batches->batches[i].taskQueue[j].task_count=0;
            calculate_current_time(batches);
            if(batches->current_time < batches->deadline) return 1;//成功融合使得时间小于截止期
        }
    }
    return -1;//未能成功融合
}

int findMinTargetSizeTask(TaskQueue *taskQueue)//查找当前大小图片能最小缩到哪个大小
{
    int size=taskQueue->size;//我们需要找到这个批次内最大的图片是多大
    int size_index=1;
    for(int i=0;i<size-1;i++)
    {
        if(accuracy[size-1][i][3]>=worst_accuracy[size-1])
        {return i;}//返回最小能缩到batches.batch[i]
    }
    return -1;//缩不了了
}


// 批次内任务转移函数
void transfer_batch_tasks(TaskQueue *source, Batch *destination) {
    // 为目标批次分配足够的空间来存储所有源批次的任务
    destination->taskQueue = (TaskQueue*)realloc(destination->taskQueue, sizeof(TaskQueue) * (destination->Queue_count + 1));
    
    // 创建新的TaskQueue并复制任务
    TaskQueue *newQueue = &destination->taskQueue[destination->Queue_count];
    newQueue->size = source->size;
    newQueue->task_count = source->task_count;
    newQueue->tasks = (Task*)malloc(source->task_count * sizeof(Task));
    
    // 复制所有任务
    for(int i = 0; i < source->task_count; i++) {
        newQueue->tasks[i] = source->tasks[i];
    }
    
    destination->Queue_count++;
}

// 将内部大小映射到实际大小
int get_actual_size(int internal_size) {
    switch(internal_size) {
        case 1: return 64;
        case 2: return 128;
        case 3: return 256;
        case 4: return 512;
        default: return internal_size;
    }
}

void GPU_process(Batch *batch, FILE *out)
{
    // 先检查是否有任何非空的任务队列
    int has_tasks = 0;
    for(int i = 0; i < batch->Queue_count; i++) {
        if(batch->taskQueue[i].task_count > 0) {
            has_tasks = 1;
            break;
        }
    }
    
    if(!has_tasks) {
        return;
    }
    
    int actual_size = get_actual_size(batch->size);
    fprintf(out, "  {\n");
    fprintf(out, "    \"size\": %d,\n", actual_size);
    fprintf(out, "    \"images\": [\n");
    
    int first_image = 1;
    for(int i = 0; i < batch->Queue_count; i++) {
        for(int j = 0; j < batch->taskQueue[i].task_count; j++) {
            if(!first_image) {
                fprintf(out, ",\n");
            }
            fprintf(out, "      \"%s\"", batch->taskQueue[i].tasks[j].id);
            first_image = 0;
        }
    }
    
    fprintf(out, "\n    ]\n");
    fprintf(out, "  }");
}


int get_num_tasks(Task *tasks)
{
    int count = 0;
    while (tasks[count].size != 0) {
        count++;
    }
    return count;
}
// 处理任务调度的主逻辑
void dynamicScheduling(Batches *batches, Task *tasks, FILE *out)
 {
    // 初始化四个批次
    init_batches(batches,tasks);
    int num_tasks = get_num_tasks(tasks);
    // 遍历所有任务并分配到对应大小的批次
    for (int i = 0; i < num_tasks; i++) {
        Task *task = &tasks[i];
        if (task->size < 1 || task->size > 4) {
            continue; // 防越界
        }
        appendTaskToQueue(&batches->batches[task->size-1].taskQueue[0], task);
        calculate_current_time(batches);//计算并更新一个当前批次集合的总时间
        if(batches->current_time > batches->deadline)//如果超ddl了，就进行融合
        {
            int result= compress_batch(batches);
            if(result==-1) break;//压缩满了
        }
    }
    //从上个循环出来，要么是任务安排完了，要么是批次压缩满了，下一步是传给GPU运行了（尚未想好）
    
    // 开始JSON数组
    fprintf(out, "[\n");
    
    int first_batch = 1;
    for (int i = 0; i < batches->batch_count; i++) 
    {
        // 先检查这个批次是否有任务
        int has_tasks = 0;
        for(int j = 0; j < batches->batches[i].Queue_count; j++) {
            if(batches->batches[i].taskQueue[j].task_count > 0) {
                has_tasks = 1;
                break;
            }
        }
        
        if(has_tasks) {
            if(!first_batch) {
                fprintf(out, ",\n");
            }
            GPU_process(&batches->batches[i], out); // 写入文件
            first_batch = 0;
        }
    }
    
    // 结束JSON数组
    fprintf(out, "\n]\n");
}
