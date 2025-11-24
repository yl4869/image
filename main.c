#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <float.h>
#include <ctype.h>

// 定义任务结构体
typedef struct {
    int size;            // 图像大小
    float deadline;       // 截止时间
    char id[50];  //图片代号
    int crucial;  //是否是关键任务，1是，0不是
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

float worst_accuracy[4] = {0.40f, 0.60f, 0.70f, 0.75f}; // 用于假设对于不同大小的任务的最差准确率要求已经给出

float trans_time_size[4] = {0.75, 1, 1.7, 5.3}; // 假设对应四个尺寸的传输时间（kx+b中的k）

float proc_time_size[4][4] = {
    {0.03, 0.05, 0.06, 2.25},
    {0.04, 0.06, 0.08, 3.5},
    {0.05, 0.07, 0.10, 3.5},
    {0.06, 0.09, 0.12, 1.8}
}; // 假设在不同大小的不同阶段的执行时间（kx+b中的b），第一维代表执行大小，第二维是阶段数


// 函数声明
int compareByDeadline(const void* a, const void* b);
int get_num_tasks(Task *tasks);
int compress_batch(Batches *batches, float accumulated_time, float global_deadline, int *used_batches);
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
Task* read_tasks_from_file(const char *filename, int *task_count);

// 函数实现

// 排序比较函数，根据任务的截止时间进行升序排序
int compareByDeadline(const void* a, const void* b) {
    Task* taskA = (Task*)a;
    Task* taskB = (Task*)b;

    // 关键任务优先
    if (taskA->crucial != taskB->crucial) {
        return taskB->crucial - taskA->crucial; // 关键(1)排前
    }
    // 同为关键或同为非关键时，按截止期升序
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
// 新增参数：include_fixed_overhead 控制是否包含固定开销
void calculate_current_time_impl(Batches *batches, int include_fixed_overhead)
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
        // 只在第一轮或指定时包含固定开销
        float b = include_fixed_overhead ? proc_time_size[i][3] : 0.0f;
        batches->current_time+=k*x+b;
    }
}

void calculate_current_time(Batches *batches)
{
    calculate_current_time_impl(batches, 1);
}

// 计算时间：根据已使用批次决定是否包含固定开销
void calculate_current_time_smart(Batches *batches, int *used_batches, float *fixed_overhead_added)
{
    batches->current_time = 0.0f;
    *fixed_overhead_added = 0.0f;
    int x; // 任务数量
    
    for(int i = 0; i < 4; i++) {
        if(batches->batches[i].Queue_count == 0) continue;
        
        x = 0;
        float k = trans_time_size[i]; // 传输时间系数
        for(int j = 0; j < batches->batches[i].Queue_count; j++) {
            x += batches->batches[i].taskQueue[j].task_count;
        }
        
        // 只在该批次第一次使用时包含固定开销
        float b = 0.0f;
        if (!used_batches[i] && x > 0) {
            b = proc_time_size[i][3]; // 第一次使用，加上固定开销
            *fixed_overhead_added += b;
        }
        
        batches->current_time += k * x + b;
    }
}

void init_batches(Batches *batches,Task *tasks)//初始化批次集合
{
    batches->batch_count = 4;
    batches->current_time = 0.0f;
    // 每轮初始化时不预设具体截止期，待插入首个任务后再确定，并在后续插入时取最小值
    batches->deadline = FLT_MAX;
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
// 持续压缩直到无法再压缩或时间满足deadline要求
int compress_batch(Batches *batches, float accumulated_time, float global_deadline, int *used_batches) 
{   
    int compressed_any = 0; // 标记是否进行了任何压缩
    float fixed_overhead_this_calc = 0.0f;
    
    // 持续压缩，直到无法再压缩
    while (1) {
        int compressed_this_round = 0; // 本轮是否压缩了
        
        // 从大到小遍历批次尺寸
        for(int i=3;i>=0;i--)
        {   
            int original_count = batches->batches[i].Queue_count;
            for(int j=0;j<original_count;j++)
            {
                if(batches->batches[i].taskQueue[j].task_count==0) continue;
                
                // 找到当前批次内任务能最小缩到哪个尺寸
                int batche_index = findMinTargetSizeTask(&batches->batches[i].taskQueue[j]);
                if(batche_index==-1 || batche_index==i) continue;//不能再缩了或者缩到自己
                
                // 执行压缩：将任务从批次i转移到批次batche_index
                transfer_batch_tasks(&batches->batches[i].taskQueue[j], &batches->batches[batche_index]);
                batches->batches[i].taskQueue[j].tasks=NULL;
                batches->batches[i].taskQueue[j].task_count=0;
                
                // 使用与主循环一致的时间计算方式
                calculate_current_time_smart(batches, used_batches, &fixed_overhead_this_calc);
                
                // 检查压缩后是否满足deadline
                if((accumulated_time + batches->current_time) <= global_deadline) {
                    return 1; // 成功压缩，时间满足要求
                }
                
                compressed_this_round = 1; // 本轮进行了压缩
                compressed_any = 1; // 标记进行了压缩
            }
        }
        
        // 如果本轮没有进行任何压缩，说明无法再压缩了
        if (!compressed_this_round) {
            break;
        }
    }
    
    // 如果进行了压缩但时间仍不满足，返回-1表示未能满足deadline
    // 如果没有进行任何压缩，也返回-1
    return compressed_any ? 0 : -1; // 0表示压缩了但未满足，-1表示无法压缩
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
            // 输出对象，包含是否为关键任务
            fprintf(out, "      {\"id\": \"%s\", \"crucial\": %d}", batch->taskQueue[i].tasks[j].id, batch->taskQueue[i].tasks[j].crucial);
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

// 从文件读取任务（CSV格式：size,deadline,id,crucial,category）
Task* read_tasks_from_file(const char *filename, int *task_count) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        printf("无法打开任务文件: %s\n", filename);
        *task_count = 0;
        return NULL;
    }
    
    // 先统计行数
    int count = 0;
    char line[256];
    
    // 跳过标题行（如果有）
    if (fgets(line, sizeof(line), fp)) {
        // 检查是否是标题行
        if (strstr(line, "size") && strstr(line, "deadline")) {
            // 是标题行，继续
        } else {
            // 不是标题行，计数
            count++;
        }
    }
    
    while (fgets(line, sizeof(line), fp)) {
        count++;
    }
    
    // 分配内存（多分配一个用作结束标记）
    Task *tasks = (Task*)malloc((count + 1) * sizeof(Task));
    
    // 重置文件指针
    rewind(fp);
    
    // 再次跳过标题行（如果有）
    if (fgets(line, sizeof(line), fp)) {
        if (!(strstr(line, "size") && strstr(line, "deadline"))) {
            // 不是标题行，重置回文件开头
            rewind(fp);
        }
    }
    
    // 读取任务数据
    int idx = 0;
    while (fgets(line, sizeof(line), fp) && idx < count) {
        int size, crucial;
        float deadline;
        char id[50];
        char category[100];
        
        // 解析CSV行：size,deadline,id,crucial,category
        int fields_read = sscanf(line, "%d,%f,%49[^,],%d,%99[^\n\r]", &size, &deadline, id, &crucial, category);
        if (fields_read >= 4) {
            tasks[idx].size = size;
            tasks[idx].deadline = deadline;
            
            // 如果有category字段（fields_read == 5），将id和category拼接
            if (fields_read == 5 && strlen(category) > 0) {
                // 移除category末尾的空白字符
                int cat_len = strlen(category);
                while (cat_len > 0 && (category[cat_len-1] == '\n' || category[cat_len-1] == '\r' || category[cat_len-1] == ' ')) {
                    category[cat_len-1] = '\0';
                    cat_len--;
                }
                // 拼接id和category: "id_category"
                snprintf(tasks[idx].id, sizeof(tasks[idx].id), "%s_%s", id, category);
            } else {
                // 没有category，直接使用id
                strncpy(tasks[idx].id, id, sizeof(tasks[idx].id) - 1);
                tasks[idx].id[sizeof(tasks[idx].id) - 1] = '\0';
            }
            
            tasks[idx].crucial = crucial;
            idx++;
        }
    }
    
    // 添加结束标记
    tasks[idx].size = 0;
    tasks[idx].deadline = 0.0f;
    strcpy(tasks[idx].id, "");
    tasks[idx].crucial = 0;
    
    *task_count = idx;
    fclose(fp);
    return tasks;
}

// 处理任务调度的主逻辑
// 辅助函数：根据已入队任务标记已处理
static void mark_processed_tasks(Batches *batches, Task *tasks, int num_tasks, int *processed) {
    for (int b = 0; b < 4; b++) {
        for (int q = 0; q < batches->batches[b].Queue_count; q++) {
            TaskQueue *queue = &batches->batches[b].taskQueue[q];
            for (int t = 0; t < queue->task_count; t++) {
                Task *queued = &queue->tasks[t];
                // 通过 id 匹配（假设唯一）
                for (int i = 0; i < num_tasks; i++) {
                    if (!processed[i] && strcmp(tasks[i].id, queued->id) == 0) {
                        processed[i] = 1;
                        break;
                    }
                }
            }
        }
    }
}

void dynamicScheduling(Batches *batches, Task *tasks, FILE *out)
 {
    int num_tasks = get_num_tasks(tasks);
    int *processed = (int*)calloc(num_tasks, sizeof(int));
    float accumulated_time = 0.0f; // 跨轮累计时间（连续时间）
    int used_batches[4] = {0, 0, 0, 0}; // 记录哪些批次尺寸已经使用过（已计入固定开销）
    int is_first_round = 1; // 标记是否是第一轮

    // 找到所有任务的最小deadline（全局deadline）
    float global_deadline = FLT_MAX;
    for (int i = 0; i < num_tasks; i++) {
        if (tasks[i].deadline < global_deadline) {
            global_deadline = tasks[i].deadline;
        }
    }

    // 开始JSON数组（整个运行期仅一次）
    fprintf(out, "[\n");
    int first_batch = 1; // 控制跨轮次的逗号

    while (1) {
        // 初始化四个批次
        init_batches(batches, tasks);

        // 分配未处理任务到本轮批次
        int tasks_added_this_round = 0; // 记录本轮添加的任务数
        int can_add_more = 1; // 标记是否还能继续添加任务
        
        for (int i = 0; i < num_tasks; i++) {
            if (processed[i]) continue; // 跳过已处理
            Task *task = &tasks[i];
            if (task->size < 1 || task->size > 4) {
                continue; // 防越界
            }
            
            int target_batch_index;
            if (task->crucial == 0) {
                target_batch_index = 0; // 非关键任务直接分配到64大小（索引0）
            } else {
                target_batch_index = task->size - 1; // 关键任务按原大小分配
            }
            
            // 先添加任务
            appendTaskToQueue(&batches->batches[target_batch_index].taskQueue[0], task);
            tasks_added_this_round++;
            
            // 使用智能时间计算：只在第一次使用批次时计入固定开销
            float fixed_overhead_this_calc = 0.0f;
            calculate_current_time_smart(batches, used_batches, &fixed_overhead_this_calc);
            
            // 使用连续时间进行判断：accumulated_time + 本轮时间，使用全局deadline
            if ((accumulated_time + batches->current_time) > global_deadline) {
                // 尝试压缩批次以节省时间
                int result = compress_batch(batches, accumulated_time, global_deadline, used_batches);
                
                if (result == 1) {
                    // 压缩成功，时间满足deadline，可以继续添加任务
                    // compress_batch内部已经重新计算了时间，batches->current_time已经更新
                    continue; // 继续添加下一个任务
                } else if (result == 0) {
                    // 压缩了但时间仍不满足deadline，移除刚加入的任务
                    batches->batches[target_batch_index].taskQueue[0].task_count--;
                    tasks_added_this_round--;
                    calculate_current_time_smart(batches, used_batches, &fixed_overhead_this_calc); // 重新计算时间
                    can_add_more = 0;
                    break; // 停止添加更多任务，但会输出已添加的任务
                } else {
                    // result == -1: 无法再压缩，移除刚加入的任务
                    batches->batches[target_batch_index].taskQueue[0].task_count--;
                    tasks_added_this_round--;
                    calculate_current_time_smart(batches, used_batches, &fixed_overhead_this_calc); // 重新计算时间
                    can_add_more = 0;
                    break; // 停止添加更多任务，但会输出已添加的任务
                }
            }
        }
        
        // 如果本轮一个任务都没加进去，说明剩余任务都无法完成
        if (tasks_added_this_round == 0) {
            printf("警告: 剩余任务无法在deadline内完成，停止调度\n");
            break; // 退出 while(1) 循环
        }
        
        // 统计每个批次的关键任务数量，并创建批次索引数组
        typedef struct {
            int index;           // 批次索引
            int crucial_count;   // 关键任务数量
        } BatchPriority;
        BatchPriority batch_priorities[4];
        for (int i = 0; i < batches->batch_count; i++) {
            batch_priorities[i].index = i;
            batch_priorities[i].crucial_count = 0;
            
            // 统计该批次的关键任务数量
            for (int j = 0; j < batches->batches[i].Queue_count; j++) {
                for (int k = 0; k < batches->batches[i].taskQueue[j].task_count; k++) {
                    if (batches->batches[i].taskQueue[j].tasks[k].crucial == 1) {
                        batch_priorities[i].crucial_count++;
                    }
                }
            }
        }
        // 按关键任务数量降序排序（冒泡排序）
        for (int i = 0; i < batches->batch_count - 1; i++) {
            for (int j = 0; j < batches->batch_count - 1 - i; j++) {
                if (batch_priorities[j].crucial_count < batch_priorities[j + 1].crucial_count) {
                    BatchPriority temp = batch_priorities[j];
                    batch_priorities[j] = batch_priorities[j + 1];
                    batch_priorities[j + 1] = temp;
                }
            }
        }
        // 按排序后的顺序输出批次
        for (int i = 0; i < batches->batch_count; i++) 
        {
            int batch_index = batch_priorities[i].index;
            
            // 先检查这个批次是否有任务
            int has_tasks = 0;
            for (int j = 0; j < batches->batches[batch_index].Queue_count; j++) {
                if (batches->batches[batch_index].taskQueue[j].task_count > 0) {
                    has_tasks = 1;
                    break;
                }
            }
            
            if (has_tasks) {
                if (!first_batch) {
                    fprintf(out, ",\n");
                }
                GPU_process(&batches->batches[batch_index], out); // 写入文件
                first_batch = 0;
            }
        }
        // 标记本轮输出的任务为已处理
        mark_processed_tasks(batches, tasks, num_tasks, processed);

        // 标记本轮使用的批次（这些批次的固定开销已经计入）
        for (int i = 0; i < 4; i++) {
            int has_tasks_in_batch = 0;
            for (int j = 0; j < batches->batches[i].Queue_count; j++) {
                if (batches->batches[i].taskQueue[j].task_count > 0) {
                    has_tasks_in_batch = 1;
                    break;
                }
            }
            if (has_tasks_in_batch) {
                used_batches[i] = 1; // 标记该批次已使用过
            }
        }

        // 本轮时间计入累计时间，下一轮判断基于连续时间
        // 这里 batches->current_time 为本轮估计的用时
        accumulated_time += batches->current_time;
        
        is_first_round = 0; // 第一轮结束

        // 判断是否全部处理完成
        int done = 1;
        for (int i = 0; i < num_tasks; i++) {
            if (!processed[i]) { 
                done = 0; 
                break;
            }
        }
        
        if (done) break;

        // 未完成则进入下一轮，重新初始化 batches 并继续
    }
    // 追加deadline信息为数组最后一项
    if (!first_batch) {
        fprintf(out, ",\n");
    }
    fprintf(out, "  {\"deadline\": %.6f}", global_deadline);
    // 结束JSON数组
    fprintf(out, "\n]\n");
    // 统计和输出未处理的任务信息
    int unprocessed_count = 0;
    int crucial_missed = 0;
    int non_crucial_missed = 0;
    
    for (int i = 0; i < num_tasks; i++) {
        if (!processed[i]) {
            unprocessed_count++;
            if (tasks[i].crucial == 1) {
                crucial_missed++;
            } else {
                non_crucial_missed++;
            }
        }
    }
    if (unprocessed_count > 0) {
        printf("部分任务错过截止期\n");
        printf("错失任务数: %d\n", unprocessed_count);
        printf("  - 关键任务: %d\n", crucial_missed);
        printf("  - 非关键任务: %d\n", non_crucial_missed);
        printf("错失任务详细信息:\n");
        for (int i = 0; i < num_tasks; i++) {
            if (!processed[i]) {
                printf("%-15s %-10d %-12.2f %-10s\n", 
                       tasks[i].id, 
                       tasks[i].size, 
                       tasks[i].deadline,
                       tasks[i].crucial ? "关键" : "非关键");
            }
        }
        
        // 将错失任务输出到 JSON 文件
        FILE *missed_file = NULL;
        if (fopen_s(&missed_file, "missed_tasks.json", "w") == 0 && missed_file) {
            fprintf(missed_file, "{\n");
            fprintf(missed_file, "  \"total_tasks\": %d,\n", num_tasks);
            fprintf(missed_file, "  \"completed_tasks\": %d,\n", num_tasks - unprocessed_count);
            fprintf(missed_file, "  \"missed_tasks\": %d,\n", unprocessed_count);
            fprintf(missed_file, "  \"missed_crucial\": %d,\n", crucial_missed);
            fprintf(missed_file, "  \"missed_non_crucial\": %d,\n", non_crucial_missed);
            fprintf(missed_file, "  \"deadline\": %.6f,\n", global_deadline);
            fprintf(missed_file, "  \"accumulated_time\": %.6f,\n", accumulated_time);
            fprintf(missed_file, "  \"missed_task_details\": [\n");
            
            int first_task = 1;
            for (int i = 0; i < num_tasks; i++) {
                if (!processed[i]) {
                    if (!first_task) {
                        fprintf(missed_file, ",\n");
                    }
                    fprintf(missed_file, "    {\n");
                    fprintf(missed_file, "      \"id\": \"%s\",\n", tasks[i].id);
                    fprintf(missed_file, "      \"size\": %d,\n", tasks[i].size);
                    fprintf(missed_file, "      \"deadline\": %.6f,\n", tasks[i].deadline);
                    fprintf(missed_file, "      \"crucial\": %d\n", tasks[i].crucial);
                    fprintf(missed_file, "    }");
                    first_task = 0;
                }
            }
            
            fprintf(missed_file, "\n  ]\n");
            fprintf(missed_file, "}\n");
            fclose(missed_file);
            printf("\n错失任务详情已保存到: missed_tasks.json\n");
        } else {
            printf("\n警告: 无法创建 missed_tasks.json 文件\n");
        }
    } 
    free(processed);
}
// main函数
int main(int argc, char *argv[]) {
    // 从命令行参数或默认文件读取任务
    const char *task_file = "tasks.csv"; 
    if (argc > 1) {
        task_file = argv[1]; // 使用命令行指定的文件
    }
    int task_count = 0;
    Task *tasks = read_tasks_from_file(task_file, &task_count);
    sortTasksByDeadline(tasks);
    FILE *out = fopen("output.json", "w");
    if (!out) {
        perror("无法创建 output.json");
        free(tasks);
        return 1;
    }
    Batches batches;
    dynamicScheduling(&batches, tasks, out);
    fclose(out);
    free(tasks);
    return 0;
}
