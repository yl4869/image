#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>


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
float worst_accuracy[4]={0.40f,0.60f,0.70f,0.75f};//用于假设对于不同大小的任务的最差准确率要求已经给出
float trans_time_size[4]={0.1,0.2,0.3,0.4};//假设对应四个尺寸的传输时间（kx+b中的k）
float proc_time_size[4][4]={
    {0.03,0.05,0.06,0.07},
    {0.04,0.06,0.08,0.10},
    {0.05,0.07,0.10,0.12},
    {0.06,0.09,0.12,0.15}
};//假设在不同大小的不同阶段的执行时间（kx+b中的b），第一维代表执行大小，第二维是阶段数


// 定义任务结构体
typedef struct {
    int size;            // 图像大小
    float deadline;       // 截止时间
    char id[50];  //图片代号
} Task;

// 定义批次结构体
typedef struct {
    Task *tasks;          // 批次内任务数组
    int task_count;       // 批次内任务数量
    int size[4];            // 批次目标大小,包含缩小后融入的尺寸，size[0]代表该批次的执行大小，size[1...3]用于记录有哪些尺寸融入进来了
    int stage;              // 批次阶段
    float start_time;     // 批次开始时间（暂未用到）
    float end_time;       // 批次结束时间（暂未用到）
    float deadline;       // 批次的截止时间
} Batch;

// 定义批次集合结构体（队列）
typedef struct {
    Batch *batches;       // 批次数组
    int batch_count;      // 批次数量（可以去掉，因为在实际实现时发现直接把4个序列全初始化更加方便）
    int max_size;         // 最大批次数（未用到）
    float deadline;       //获取最紧急任务的截止期
    float current_time;    //记录当前的时间
} Batches;

// 函数声明
int compress_batch( Batches *batches);
void calculate_current_time(Batches *batches); 
int findMinTargetSizeTask(Batch *batch);
void transfer_batch_tasks(Batch *source, Batch *destination);
void GPU_process(Batches *batches);
void batch_printf(Batch *batch);
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
void sortTasksByDeadline(Task* tasks, int num_tasks) {
    qsort(tasks, num_tasks, sizeof(Task), compareByDeadline);
}
// 找到已有批次（返回这个尺寸任务应该被划分到第几个批次）
int findBatchIndexBySize(Batches *batches, int size) {
    for (int i = 0; i < 4; i++) {
        for(int j=0;j<4;j++)
        if (batches->batches[i].size[j] == size) {
            return i;
        }
    }
    return -1;  // 返回 -1 表示没有找到匹配的批次
}
// 添加任务到批次
void appendTaskToBatch(Batch *batch, Task *task) {
    batch->tasks = (Task*)realloc(batch->tasks, (batch->task_count + 1) * sizeof(Task));
    batch->tasks[batch->task_count] = *task;
    batch->task_count++;
}
// 处理任务调度的主逻辑
void dynamicScheduling(Batches *batches, Task *tasks, int num_tasks) {
    // 初始化四个批次，分别对应四种任务大小
    batches->batch_count = 4;
    batches->deadline=tasks[0].deadline;//构想是在主函数中已经按ddl排序了，所以这里直接取第一个就可以了
    // 初始化四个批次
    for (int i = 0; i < 4; i++) {
        Batch *batch = &batches->batches[i];
        batch->size[0] = i + 1;  // 使用1, 2, 3, 4代替64, 128, 256, 512，直接先按大小顺序排列，最后传给GPU时再决定传递顺序
        batch->size[1] = 0;
        batch->size[2] = 0;
        batch->size[3] = 0;
        batch->tasks = NULL;
        batch->task_count = 0;
        batch->end_time = 0.0f;
        batch->deadline = 0.0f;
        batch->start_time=0.0f;
        batch->stage = 4;
    }

    // 遍历所有任务并分配到对应大小的批次
    for (int i = 0; i < num_tasks; i++) {
        Task *task = &tasks[i];
        appendTaskToBatch(&batches->batches[task->size-1], task);
        calculate_current_time(batches);//计算并更新一个当前批次集合的总时间
        if(batches->current_time>batches->deadline)//如果超ddl了，就进行融合
        {
            int result= compress_batch(batches);
            if(result==-1) break;//压缩满了
        }
    }
    //从上个循环出来，要么是任务安排完了，要么是批次压缩满了，下一步是传给GPU运行了（尚未想好）

    for (int i = 0; i < batches->batch_count; i++) 
    {
         GPU_process(batches); // 假设此函数执行GPU处理
    }
}


//计算batches的总时间（对有任务的批次时间求和）
void calculate_current_time(Batches *batches)
{   batches->current_time = 0.0f; 
    for(int i=0;i<4;i++)
    {
        if(batches->batches[i].task_count==0) continue;
        float k=trans_time_size[batches->batches[i].size[0]-1];//传输时间
        int x=batches->batches[i].task_count;//任务数量
        float b=proc_time_size[batches->batches[i].size[0]-1][batches->batches[i].stage];//阶段时间
        batches->current_time+=k*x+b;
    }
}


// 压缩批次操作，压缩超时的批次
int compress_batch( Batches *batches) 
{   
    for(int i=3;i>=0;i--)//按尺寸从小到大遍历，因为是压缩到最小
    {
        int batche_index= findMinTargetSizeTask(&batches->batches[i]);
        transfer_batch_tasks(&batches->batches[i],&batches->batches[batche_index] );
        calculate_current_time(batches);
        if(batches->current_time< batches->deadline) return 1;//成功融合使得时间小于截止期
    }
    return -1;//未能成功融合
}

// 批次内任务转移函数
void transfer_batch_tasks(Batch *source, Batch *destination) {
    // 为目标批次分配足够的空间来存储所有源批次的任务
    destination->tasks = (Task*)realloc(destination->tasks, sizeof(Task) * (destination->task_count + source->task_count));
    // 将源批次的任务复制到目标批次
    for (int i = 0; i < source->task_count; i++) {
        destination->tasks[destination->task_count + i] = source->tasks[i];
    }
    destination->task_count += source->task_count;

    free(source->tasks);  // 释放源批次的任务数组
    source->tasks = NULL; // 将任务指针置为NULL
    source->task_count = 0; // 清空任务数量
    for(int i=0;i<4;i++)//用于记录融合后的批次包含的任务原尺寸都是多少
    {
        if(destination->size[i]!=0) continue;//找到第一个非零的索引
        for(int j=0;j<4;j++)
        {
            if(source->size[j]==0) break;//遇到第一个为零的索引停止
            destination->size[i++]=source->size[j];
        }
        source->size[0]=0;//标记该批次已经被移除，构想是已经压缩的批次后续不可能再次出现
        break;
    }
    
}

int findMinTargetSizeTask(Batch *batch)//查找当前批次能最小缩到哪个大小
{
    int biggest_size=batch->size[0];//我们需要找到这个批次内最大的图片是多大
    int size_index=1;
    while(batch->size[size_index]!=0)//获取当前批次里原尺寸最大的图片
    {
        if (biggest_size < batch->size[size_index]){biggest_size=batch->size[size_index];}
        size_index++;
    }
    for(int i=0;i<batch->size[0]-1;i++)
    {
        if(accuracy[biggest_size-1][i][3]>=worst_accuracy[biggest_size-1])
        {return i;}//返回最小能缩到batches.batch[i]
    }
    return -1;//缩不了了
}

void GPU_process(Batches *batches)
{
    for(int i=1;i<=batches->batch_count;i++)
    {
        if(batches->batches[i-1].task_count==0) continue;
        batch_printf(&batches->batches[i-1]);
    }
}
void batch_printf(Batch *batch)
{
    printf("批次大小：%d\n",batch->size[0]);
    for(int i=1;i<batch->task_count;i++)
    {
        printf("%c\n",batch->tasks[i].id);
    }
}
// int main() {
//     // 示例任务（任务大小，压缩精度，传输时间，处理时间，截止时间）
//     Task tasks[] = {
//         {1, 0.9f, 1.0f, 2.0f, 10.0f},   // 原来64改为1
//         {2, 0.85f, 1.2f, 2.3f, 15.0f},  // 原来128改为2
//         {3, 0.8f, 1.5f, 2.8f, 20.0f},   // 原来256改为3
//         {4, 0.75f, 1.8f, 3.1f, 25.0f}   // 原来512改为4
//     };
//     int num_tasks = 4;
//     sortTasksByDeadline(tasks, num_tasks);
//     // 初始化批次集合
//     Batches batches;
//     batches.max_size = 4;
//     batches.batches = (Batch *)malloc(batches.max_size * sizeof(Batch));
    
//     // 动态调度任务
//     dynamicScheduling(&batches, tasks, num_tasks);

//     // 释放内存
//     for (int i = 0; i < batches.batch_count; i++) {
//         free(batches.batches[i].tasks);
//     }
//     free(batches.batches);
    
//     return 0;
// }
