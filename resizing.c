#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <ctype.h>

typedef struct {
    int size;            // 图像大小（索引：0=64, 1=128, 2=256, 3=512）
    int orig_size;       // 原始图像大小（索引）
    float deadline;      // 截止时间
    char id[50];         // 图片代号
    int crucial;         // 是否是关键任务，1是，0不是
    int assigned_size;   // 分配的处理尺寸
} Task;

// 定义批次结构体
typedef struct {
    Task *task;          // 批次内任务数组
    int task_count;      // 批次内任务数量
    float deadline;      // 批次的截止时间
    int size;            // 批次处理的图像大小(0-3)
} Batch;

// 定义批次集合结构体（队列）
typedef struct {
    Batch *batches;      // 批次数组
    int batch_count;     // 批次数量
    float deadline;      // 获取最紧急任务的截止期
    float current_time;  // 记录当前的时间
} Batches;

// 升级候选结构体
typedef struct {
    int task_idx;        // 任务索引
    int size_from;       // 升级前尺寸
    int size_to;         // 升级后尺寸
    float delta_utility; // 增量收益
    float delta_time;    // 增量时间
    float ratio;         // 性价比
} UpgradeCandidate;

float weight[2] = {0.5, 1}; // 定义权重(非关键和关键)
int size_values[4] = {64, 128, 256, 512}; // 实际尺寸值

// 全局变量定义
float accuracy[4][4] = {
   {0.54, 0.71, 0.77, 0.78},
   {0.67, 0.75, 0.82, 0.85},
   {0.65, 0.72, 0.84, 0.86},
   {0.69, 0.77, 0.86, 0.87}
}; // 第一维是原始大小，第二维是调整到哪个大小后的精度
float proc_time_size[4] = {2.25, 3.5, 3.5, 1.8}; // 固定推理开销 D[s]
float trans_time_size[4] = {0.75, 1, 1.7, 5.3};  // 增量时间 B[s]

// 函数声明
Task* read_tasks_from_file(const char *filename, int *task_count);

// 比较函数：用于升级候选排序（降序）
int compare_candidates(const void *a, const void *b) {
    UpgradeCandidate *ca = (UpgradeCandidate *)a;
    UpgradeCandidate *cb = (UpgradeCandidate *)b;
    if (cb->ratio > ca->ratio) return 1;
    if (cb->ratio < ca->ratio) return -1;
    return 0;
}

// 获取尺寸索引
int get_size_index(int size_value) {
    for (int i = 0; i < 4; i++) {
        if (size_values[i] == size_value) return i;
    }
    return 0;
}

// 贪心调度算法：对给定的 S_max 执行调度
float schedule_with_smax(Task *tasks, int task_count, int s_max_idx, float H, int *best_assignment) {
    // 计算有效预算 H' = H - sum(D[s]) for s <= s_max
    float H_prime = H;
    for (int s = 0; s <= s_max_idx; s++) {
        H_prime -= proc_time_size[s];
    }
    
    // 初始化：为每个任务分配最小允许尺寸
    int *assignment = (int *)malloc(task_count * sizeof(int));
    float C0 = 0; // 基础时间开销
    float U0 = 0; // 基础收益
    
    for (int i = 0; i < task_count; i++) {
        // 找到最小允许尺寸（<= orig_size 且 <= s_max）
        int min_size = 0;
        for (int s = 0; s <= s_max_idx && s <= tasks[i].orig_size; s++) {
            min_size = s;
            break;
        }
        assignment[i] = min_size;
        C0 += trans_time_size[min_size];
        float w = weight[tasks[i].crucial];
        U0 += w * accuracy[tasks[i].orig_size][min_size];
    }
    
    // 可行性检查
    if (C0 > H_prime) {
        free(assignment);
        return -1; // 不可行，如果不可行会怎么样？
    }
    
    // 构造升级候选
    UpgradeCandidate *candidates = (UpgradeCandidate *)malloc(task_count * 4 * sizeof(UpgradeCandidate));
    int candidate_count = 0;
    
    for (int i = 0; i < task_count; i++) {
        float w = weight[tasks[i].crucial];
        int orig = tasks[i].orig_size;
        
        // 对每个可能的升级路径
        for (int s_prev = 0; s_prev <= s_max_idx && s_prev <= orig; s_prev++) {
            for (int s_now = s_prev + 1; s_now <= s_max_idx && s_now <= orig; s_now++) {
                float delta_utility = w * (accuracy[orig][s_now] - accuracy[orig][s_prev]);
                float delta_time = trans_time_size[s_now] - trans_time_size[s_prev];
                
                if (delta_time > 0) {
                    candidates[candidate_count].task_idx = i;
                    candidates[candidate_count].size_from = s_prev;
                    candidates[candidate_count].size_to = s_now;
                    candidates[candidate_count].delta_utility = delta_utility;
                    candidates[candidate_count].delta_time = delta_time;
                    candidates[candidate_count].ratio = delta_utility / delta_time;
                    candidate_count++;
                }
            }
        }
    }
    
    // 按性价比排序（降序）
    qsort(candidates, candidate_count, sizeof(UpgradeCandidate), compare_candidates);
    
    // 贪心升级
    float budget = H_prime - C0;
    float utility = U0;

    for (int c = 0; c < candidate_count; c++) {
        int task_idx = candidates[c].task_idx;
        int size_from = candidates[c].size_from;
        int size_to = candidates[c].size_to;
        float delta_time = candidates[c].delta_time;
        float delta_utility = candidates[c].delta_utility;
        
        // 如果当前任务的尺寸正好是 size_from，且预算充足，则升级
        if (assignment[task_idx] == size_from && budget >= delta_time) {
            assignment[task_idx] = size_to;
            budget -= delta_time;
            utility += delta_utility;
        }
    }
    
    // 保存最佳分配
    memcpy(best_assignment, assignment, task_count * sizeof(int));
    
    free(assignment);
    free(candidates);
    
    return utility;
}

// 主调度函数，返回值：1表示调度成功，0表示任务丢失
int schedule_tasks(Task *tasks, int task_count, float H) {
    int *best_assignment = (int *)malloc(task_count * sizeof(int));
    int *temp_assignment = (int *)malloc(task_count * sizeof(int));
    float best_utility = -1;
    int best_s_max = -1;
    
    // 枚举每个 S_max
    for (int s_max = 0; s_max < 4; s_max++) {
        float utility = schedule_with_smax(tasks, task_count, s_max, H, temp_assignment);

        
        if (utility > best_utility) {
            best_utility = utility;
            best_s_max = s_max;
            memcpy(best_assignment, temp_assignment, task_count * sizeof(int));
        }
    }
    
    // 检查是否找到可行解
    if (best_utility < 0) {
        // 所有s_max都不可行，任务丢失
        free(best_assignment);
        free(temp_assignment);
        return 0;
    }
    
    // 将分配结果写入任务
    for (int i = 0; i < task_count; i++) {
        tasks[i].assigned_size = best_assignment[i];
    }
    
    free(best_assignment);
    free(temp_assignment);
    return 1;
}

// 输出 JSON 格式结果，task_dropped=1表示任务丢失
void output_json(Task *tasks, int task_count, float deadline, int task_dropped) {
    FILE *fp = fopen("output_resizing.json", "w");
    if (!fp) {
        printf("无法打开文件 output_resizing.json\n");
        return;
    }
    
    fprintf(fp, "[\n");
    
    // 如果任务丢失，只输出-1
    if (task_dropped) {
        fprintf(fp, "  -1\n");
        fprintf(fp, "]\n");
        fclose(fp);
        printf("错误: 任务调度失败，存在任务错过截止期\n");
        printf("结果已输出到 output_resizing.json\n");
        return;
    }
    
    // 按尺寸分组输出
    for (int size_idx = 0; size_idx < 4; size_idx++) {
        int has_tasks = 0;
        
        // 先检查是否有任务在这个尺寸
        for (int i = 0; i < task_count; i++) {
            if (tasks[i].assigned_size == size_idx) {
                has_tasks = 1;
                break;
            }
        }
        
        if (has_tasks) {
            fprintf(fp, "  {\n");
            fprintf(fp, "    \"size\": %d,\n", size_values[size_idx]);
            fprintf(fp, "    \"images\": [\n");
            
            int first = 1;
            for (int i = 0; i < task_count; i++) {
                if (tasks[i].assigned_size == size_idx) {
                    if (!first) fprintf(fp, ",\n");
                    fprintf(fp, "      {\"id\": \"%s\", \"crucial\": %d}", 
                            tasks[i].id, tasks[i].crucial);
                    first = 0;
                }
            }
            
            fprintf(fp, "\n    ]\n");
            fprintf(fp, "  },\n");
        }
    }
    
    fprintf(fp, "  {\"deadline\": %f}\n", deadline);
    fprintf(fp, "]\n");
    fclose(fp);
}

// 从文件读取任务（CSV格式：size,orig_size,deadline,id,crucial）
// 注意：resizing.c中size和orig_size都使用索引（0=64, 1=128, 2=256, 3=512）
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
    
    // 分配内存
    Task *tasks = (Task*)malloc(count * sizeof(Task));
    
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
        int size_val, crucial;
        float deadline;
        char id[50];    
        // 解析CSV行
        if (sscanf(line, "%d,%f,%49[^,],%d", &size_val, &deadline, id, &crucial) == 4) {
            // size_val是索引（1-4），转换为0-3
            int size_idx = size_val - 1;
            if (size_idx < 0 || size_idx > 3) {
                size_idx = 0; // 默认64
            }
            tasks[idx].size = size_idx;
            tasks[idx].orig_size = size_idx;  // 原始大小和当前大小相同
            tasks[idx].deadline = deadline;
            strncpy(tasks[idx].id, id, sizeof(tasks[idx].id) - 1);
            tasks[idx].id[sizeof(tasks[idx].id) - 1] = '\0';
            tasks[idx].crucial = crucial;
            tasks[idx].assigned_size = size_idx;  // 初始分配大小
            idx++;
        }
    }
    *task_count = idx;
    fclose(fp);
    return tasks;
}

int main(int argc, char *argv[]) {
    // 从命令行参数或默认文件读取任务
    const char *task_file = "tasks.csv"; 
    
    if (argc > 1) {
        task_file = argv[1]; // 使用命令行指定的文件
    }
    
    int task_count = 0;
    Task *tasks = read_tasks_from_file(task_file, &task_count);
    
    float H = tasks[0].deadline; 
    
    // 执行调度
    int schedule_success = schedule_tasks(tasks, task_count, H);
    
    // 输出结果
    if (!schedule_success) {
        // 调度失败，输出-1
        output_json(tasks, task_count, H, 1);
    } else {
        // 调度成功，正常输出
        output_json(tasks, task_count, H, 0);
        
    }
    
    // 释放内存
    free(tasks);
    
    return schedule_success ? 0 : 1;
}
