/*
 cf-batch.c
 实现：CF-BATCH 调度器（优先关键任务、相同尺寸批处理、不进行压缩）
 输出与 main.c 保持兼容：生成 output_cf_batch.json 和 missed_tasks_cf_batch.json
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <ctype.h>

typedef struct {
    int size;          // 1..4 internal size index
    double deadline;
    char id[128];
    int crucial;       // 1 = crucial, 0 = non-crucial
} Task;

// 时间模型（与 main.c 保持一致）
static const double trans_time_size[4] = {0.75, 1.0, 1.7, 5.3};
static const double proc_time_size_1d[4] = {2.25, 3.5, 3.5, 1.8};

static int get_actual_size(int internal_size) {
    switch(internal_size) {
        case 1: return 64;
        case 2: return 128;
        case 3: return 256;
        case 4: return 512;
        default: return internal_size;
    }
}

// 简单的 JSON 字符串转义并写入文件
static void fputs_json_escaped(FILE *out, const char *s) {
    fputc('"', out);
    for (const unsigned char *p = (const unsigned char*)s; *p; ++p) {
        unsigned char c = *p;
        if (c == '"') fputs("\\\"", out);
        else if (c == '\\') fputs("\\\\", out);
        else if (c == '\b') fputs("\\b", out);
        else if (c == '\f') fputs("\\f", out);
        else if (c == '\n') fputs("\\n", out);
        else if (c == '\r') fputs("\\r", out);
        else if (c == '\t') fputs("\\t", out);
        else if (c < 0x20) {
            fprintf(out, "\\u%04x", c);
        } else {
            fputc(c, out);
        }
    }
    fputc('"', out);
}

// 读取 CSV 文件：size,deadline,id,crucial,category
Task* read_tasks_from_file(const char *filename, int *out_count) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        fprintf(stderr, "无法打开任务文件: %s\n", filename);
        *out_count = 0;
        return NULL;
    }

    char line[512];
    int count = 0;

    // 检查首行是否为表头
    if (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "size") && strstr(line, "deadline")) {
            // 有表头，继续计数剩余行
        } else {
            count++;
        }
    }
    while (fgets(line, sizeof(line), fp)) count++;
    rewind(fp);
    // 如果首行为数据，回退
    if (fgets(line, sizeof(line), fp)) {
        if (!(strstr(line, "size") && strstr(line, "deadline"))) {
            rewind(fp);
        }
    }

    Task *tasks = (Task*)malloc(sizeof(Task) * (count > 0 ? count : 0 + 1));
    int idx = 0;
    while (fgets(line, sizeof(line), fp)) {
        int size = 0, crucial = 0;
        double deadline = 0.0;
        char id[128] = {0};
        char category[256] = {0};

            int fields = sscanf(line, "%d,%lf,%127[^,],%d,%255[^\n]", &size, &deadline, id, &crucial, category);
        if (fields >= 4) {
            tasks[idx].size = size;
            tasks[idx].deadline = deadline;
            tasks[idx].crucial = crucial;
            if (fields == 5 && strlen(category) > 0) {
                int L = strlen(category);
                while (L > 0 && (category[L-1] == '\n' || category[L-1] == '\r' || category[L-1] == ' ')) { category[--L] = '\0'; }
                snprintf(tasks[idx].id, sizeof(tasks[idx].id), "%s_%s", id, category);
            } else {
                strncpy(tasks[idx].id, id, sizeof(tasks[idx].id)-1);
                tasks[idx].id[sizeof(tasks[idx].id)-1] = '\0';
            }
            idx++;
        }
    }

    fclose(fp);
    *out_count = idx;
    return tasks;
}

// 辅助结构：批次信息（用于调度决策）
typedef struct {
    int size_idx;       // 0..3
    int count;          // task count in this batch
    double earliest_deadline; // 用于按 deadline 排序
    Task **tasks;       // 指向任务指针数组
} BatchInfo;

// 用于最终输出的已调度批次（缓冲）
typedef struct {
    int size_idx;
    int count;
    Task **tasks;
    int is_crucial; // 1=来源于关键任务批次（可被合并低关键任务）
} ScheduledBatch;

// 对 BatchInfo 按 earliest_deadline 升序排序
static int cmp_batchinfo(const void *a, const void *b) {
    const BatchInfo *A = (const BatchInfo*)a;
    const BatchInfo *B = (const BatchInfo*)b;
    if (A->earliest_deadline < B->earliest_deadline) return -1;
    if (A->earliest_deadline > B->earliest_deadline) return 1;
    return 0;
}

// 按 Task* 的 deadline 排序（用于非关键任务列表）
static int cmp_taskptr_deadline(const void *a, const void *b) {
    Task *const *A = (Task *const *)a;
    Task *const *B = (Task *const *)b;
    if ((*A)->deadline < (*B)->deadline) return -1;
    if ((*A)->deadline > (*B)->deadline) return 1;
    return 0;
}

int main(int argc, char *argv[]) {
    const char *task_file = "tasks.csv";
    if (argc > 1) task_file = argv[1];

    int task_count = 0;
    Task *tasks = read_tasks_from_file(task_file, &task_count);
    if (!tasks || task_count == 0) {
        fprintf(stderr, "没有读取到任何任务，退出。\n");
        if (tasks) free(tasks);
        return 1;
    }

    // 计算全局最小 deadline
    double global_deadline = DBL_MAX;
    for (int i = 0; i < task_count; ++i) if (tasks[i].deadline < global_deadline) global_deadline = tasks[i].deadline;

    // 将任务分组：按 size（1..4）分别统计 crucial 与 non-crucial
    int crucial_counts[4] = {0,0,0,0};
    int noncrucial_counts[4] = {0,0,0,0};
    for (int i = 0; i < task_count; ++i) {
        int s = tasks[i].size;
        if (s < 1 || s > 4) continue;
        if (tasks[i].crucial) crucial_counts[s-1]++; else noncrucial_counts[s-1]++;
    }

    // 为每个组分配指针数组并填充
    Task **crucial_lists[4];
    Task **noncrucial_lists[4];
    for (int i = 0; i < 4; ++i) {
        crucial_lists[i] = NULL;
        noncrucial_lists[i] = NULL;
        if (crucial_counts[i] > 0) crucial_lists[i] = (Task**)malloc(sizeof(Task*) * crucial_counts[i]);
        if (noncrucial_counts[i] > 0) noncrucial_lists[i] = (Task**)malloc(sizeof(Task*) * noncrucial_counts[i]);
    }

    int ccurr[4] = {0,0,0,0};
    int ncurr[4] = {0,0,0,0};
    for (int i = 0; i < task_count; ++i) {
        int s = tasks[i].size;
        if (s < 1 || s > 4) continue;
        int idx = s-1;
        if (tasks[i].crucial) {
            crucial_lists[idx][ccurr[idx]++] = &tasks[i];
        } else {
            noncrucial_lists[idx][ncurr[idx]++] = &tasks[i];
        }
    }

    // 构造批次信息（先关键任务批次）
    BatchInfo crucial_batches[4];
    int crucial_batch_count = 0;
    for (int i = 0; i < 4; ++i) {
        if (crucial_counts[i] > 0) {
            BatchInfo b = {0};
            b.size_idx = i;
            b.count = crucial_counts[i];
            b.tasks = crucial_lists[i];
            double mind = DBL_MAX;
            for (int j = 0; j < b.count; ++j) if (b.tasks[j]->deadline < mind) mind = b.tasks[j]->deadline;
            b.earliest_deadline = mind;
            crucial_batches[crucial_batch_count++] = b;
        }
    }
    qsort(crucial_batches, crucial_batch_count, sizeof(BatchInfo), cmp_batchinfo);

    // 标记每个任务是否已被调度或错过
    int *processed = (int*)calloc(task_count, sizeof(int));

    // 先对非关键任务按 deadline 排序（每个尺寸内部）以便合并时优先选择靠前的
    for (int i = 0; i < 4; ++i) if (noncrucial_counts[i] > 1) qsort(noncrucial_lists[i], noncrucial_counts[i], sizeof(Task*), cmp_taskptr_deadline);

    // 这里我们先构造一个缓冲的已调度批次列表（还不写文件），以便后续合并低关键任务
    ScheduledBatch scheduled[8];
    int scheduled_count = 0;
    double accumulated_time = 0.0;

    // 处理关键任务批次 —— 只构造已调度批次缓冲
    int crucial_scheduled_flags[4] = {0,0,0,0};
    for (int bi = 0; bi < crucial_batch_count; ++bi) {
        BatchInfo *b = &crucial_batches[bi];
        double batch_time = trans_time_size[b->size_idx] * b->count + proc_time_size_1d[b->size_idx];
        if ((accumulated_time + batch_time) <= global_deadline) {
            // 可调度：将其加入 scheduled 缓冲
            scheduled[scheduled_count].size_idx = b->size_idx;
            scheduled[scheduled_count].count = b->count;
            scheduled[scheduled_count].is_crucial = 1;
            scheduled[scheduled_count].tasks = (Task**)malloc(sizeof(Task*) * b->count);
            for (int t = 0; t < b->count; ++t) {
                scheduled[scheduled_count].tasks[t] = b->tasks[t];
                // 标记为已调度
                for (int k = 0; k < task_count; ++k) if (!processed[k] && strcmp(tasks[k].id, b->tasks[t]->id) == 0 && tasks[k].crucial == b->tasks[t]->crucial) { processed[k] = 1; break; }
            }
            scheduled_count++;
            crucial_scheduled_flags[b->size_idx] = 1;
            accumulated_time += batch_time;
        } else {
            // 标记关键任务为错失
            for (int t = 0; t < b->count; ++t) {
                for (int k = 0; k < task_count; ++k) {
                    if (!processed[k] && strcmp(tasks[k].id, b->tasks[t]->id) == 0 && tasks[k].crucial == b->tasks[t]->crucial) {
                        processed[k] = -1;
                        break;
                    }
                }
            }
        }
    }

    // 合并非关键任务到已调度的关键任务批次（按尺寸），每添加一个任务都重新计算时间；一旦添加导致超时，丢弃所有剩余任务
    int stop_due_to_timeout = 0;
    // 为每个尺寸维护一个非关键任务的读取索引
    int noncrucial_read_idx[4] = {0,0,0,0};
    for (int si = 0; si < 4 && !stop_due_to_timeout; ++si) {
        if (!crucial_scheduled_flags[si]) continue; // 只有有关键任务批次存在时才做合并
        // 在 scheduled 中找到对应尺寸的关键批次（按添加顺序）
        for (int sb = 0; sb < scheduled_count && !stop_due_to_timeout; ++sb) {
            if (!scheduled[sb].is_crucial) continue;
            if (scheduled[sb].size_idx != si) continue;
            // 逐个尝试添加非关键任务
            while (noncrucial_read_idx[si] < noncrucial_counts[si]) {
                // 每添加一个任务，额外时间为 trans_time_size[si]
                double extra = trans_time_size[si];
                if ((accumulated_time + extra) <= global_deadline) {
                    // 可以添加：扩展 tasks 数组
                    int oldc = scheduled[sb].count;
                    scheduled[sb].tasks = (Task**)realloc(scheduled[sb].tasks, sizeof(Task*) * (oldc + 1));
                    Task *nt = noncrucial_lists[si][noncrucial_read_idx[si]];
                    scheduled[sb].tasks[oldc] = nt;
                    scheduled[sb].count = oldc + 1;
                    // 标记为已调度
                    for (int k = 0; k < task_count; ++k) if (!processed[k] && strcmp(tasks[k].id, nt->id) == 0 && tasks[k].crucial == nt->crucial) { processed[k] = 1; break; }
                    noncrucial_read_idx[si]++;
                    accumulated_time += extra;
                } else {
                    stop_due_to_timeout = 1;
                    break;
                }
            }
        }
    }

    // 对于没有关键批次的尺寸，尝试直接作为非关键批次整体调度（保持原来的合并行为）
    for (int si = 0; si < 4 && !stop_due_to_timeout; ++si) {
        if (crucial_scheduled_flags[si]) continue; // 已经有关键批次的尺寸已处理
        if (noncrucial_counts[si] == 0) continue;
        // 剩余的非关键任务数量
        int remaining = noncrucial_counts[si] - noncrucial_read_idx[si];
        if (remaining <= 0) continue;
        double batch_time = trans_time_size[si] * remaining + proc_time_size_1d[si];
        if ((accumulated_time + batch_time) <= global_deadline) {
            // 调度为一个非关键批次
            scheduled[scheduled_count].size_idx = si;
            scheduled[scheduled_count].count = remaining;
            scheduled[scheduled_count].is_crucial = 0;
            scheduled[scheduled_count].tasks = (Task**)malloc(sizeof(Task*) * remaining);
            for (int x = 0; x < remaining; ++x) {
                Task *nt = noncrucial_lists[si][noncrucial_read_idx[si] + x];
                scheduled[scheduled_count].tasks[x] = nt;
                for (int k = 0; k < task_count; ++k) if (!processed[k] && strcmp(tasks[k].id, nt->id) == 0 && tasks[k].crucial == nt->crucial) { processed[k] = 1; break; }
            }
            scheduled_count++;
            accumulated_time += batch_time;
            noncrucial_read_idx[si] += remaining;
        } else {
            stop_due_to_timeout = 1;
            break;
        }
    }

    // 如果遇到超时（stop_due_to_timeout），把所有未被标记的任务标为错失
    if (stop_due_to_timeout) {
        for (int i = 0; i < task_count; ++i) if (processed[i] == 0) processed[i] = -1;
    } else {
        // 否则，仍有可能存在某些未被分配的任务（例如被跳过的关键任务），把它们标为错失
        for (int i = 0; i < task_count; ++i) if (processed[i] == 0) processed[i] = -1;
    }

    // 现在将缓冲的 scheduled 批次一次性写入 output_cf_batch.json
    FILE *out = fopen("output_cf_batch.json", "w");
    if (!out) {
        fprintf(stderr, "无法创建输出文件 output_cf_batch.json\n");
        for (int i=0;i<4;i++){ if (crucial_lists[i]) free(crucial_lists[i]); if (noncrucial_lists[i]) free(noncrucial_lists[i]); }
        free(tasks);
        return 1;
    }
    fprintf(out, "[\n");
    int first_batch = 1;
    for (int sb = 0; sb < scheduled_count; ++sb) {
        ScheduledBatch *s = &scheduled[sb];
        if (!first_batch) fprintf(out, ",\n");
        fprintf(out, "  {\n    \"size\": %d,\n    \"images\": [\n", get_actual_size(s->size_idx+1));
        int first_img = 1;
        for (int t = 0; t < s->count; ++t) {
            if (!first_img) fprintf(out, ",\n");
            fprintf(out, "      {");
            fprintf(out, "\"id\": "); fputs_json_escaped(out, s->tasks[t]->id); fprintf(out, ", \"crucial\": %d}", s->tasks[t]->crucial);
            first_img = 0;
        }
        fprintf(out, "\n    ]\n  }");
        first_batch = 0;
    }
    // 写入 deadline 项
    if (!first_batch) fprintf(out, ",\n");
    fprintf(out, "  {\"deadline\": %.6f}\n]\n", global_deadline);
    fclose(out);

    // 生成 missed_tasks_cf_batch.json
    int missed_total = 0, missed_crucial = 0, missed_noncrucial = 0;
    for (int i = 0; i < task_count; ++i) if (processed[i] == -1) {
        missed_total++; if (tasks[i].crucial) missed_crucial++; else missed_noncrucial++; }

    if (missed_total > 0) {
        FILE *mf = fopen("missed_tasks_cf_batch.json", "w");
        if (mf) {
            fprintf(mf, "{\n  \"total_tasks\": %d,\n  \"completed_tasks\": %d,\n  \"missed_tasks\": %d,\n  \"missed_crucial\": %d,\n  \"missed_non_crucial\": %d,\n  \"deadline\": %.6f,\n  \"accumulated_time\": %.6f,\n  \"missed_task_details\": [\n",
                    task_count, task_count - missed_total, missed_total, missed_crucial, missed_noncrucial, global_deadline, accumulated_time);
            int first = 1;
            for (int i = 0; i < task_count; ++i) if (processed[i] == -1) {
                if (!first) fprintf(mf, ",\n");
                fprintf(mf, "    {\n      \"id\": "); fputs_json_escaped(mf, tasks[i].id); fprintf(mf, ",\n      \"size\": %d,\n      \"deadline\": %.6f,\n      \"crucial\": %d\n    }",
                        tasks[i].size, tasks[i].deadline, tasks[i].crucial);
                first = 0;
            }
            fprintf(mf, "\n  ]\n}\n");
            fclose(mf);
        } else {
            fprintf(stderr, "无法创建 missed_tasks_cf_batch.json\n");
        }
    }

    // 打印简短统计
    int completed = 0;
    for (int i = 0; i < task_count; ++i) if (processed[i] == 1) completed++;
    printf("调度完成：总任务=%d, 已完成=%d, 错失=%d, 累计时间=%.6f\n", task_count, completed, missed_total, accumulated_time);

    // 释放资源
    for (int sb = 0; sb < scheduled_count; ++sb) {
        if (scheduled[sb].tasks) free(scheduled[sb].tasks);
    }
    for (int i = 0; i < 4; ++i) { if (crucial_lists[i]) free(crucial_lists[i]); if (noncrucial_lists[i]) free(noncrucial_lists[i]); }
    free(processed);
    free(tasks);
    return 0;
}
