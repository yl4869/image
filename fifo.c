#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// FIFO 调度器：按输入顺序逐个调度，不做批处理、不做压缩
// 输入：CSV 文件（size,deadline,id,crucial,category），size 为 1-4（对应 64/128/256/512）
// 输出：output_fifo.json（当前目录），若存在未完成任务则生成 missed_tasks.json

typedef struct {
    int size;       // 1-4
    float deadline; 
    char id[100];
    int crucial;    // 0/1
} Task;

// 时间模型（与其他实现保持一致）
float trans_time_size[4] = {0.75f, 1.0f, 1.7f, 5.3f};
float proc_time_size_1d[4] = {2.25f, 3.5f, 3.5f, 1.8f};
int size_values[4] = {64, 128, 256, 512};

// 读取 CSV（兼容有无表头）
Task* read_tasks_from_file(const char *filename, int *out_count) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        fprintf(stderr, "无法打开任务文件: %s\n", filename);
        *out_count = 0;
        return NULL;
    }

    char line[512];
    int count = 0;

    // 先判断是否有标题行并统计行数
    if (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "size") && strstr(line, "deadline")) {
            // 有标题，继续计数剩余行
        } else {
            // 没有标题，第一行也是数据
            count++;
        }
    }
    while (fgets(line, sizeof(line), fp)) count++;

    rewind(fp);
    // 再跳过表头（如果有）
    if (fgets(line, sizeof(line), fp)) {
        if (!(strstr(line, "size") && strstr(line, "deadline"))) {
            // 不是表头，回到文件开始
            rewind(fp);
        }
    }

    Task *tasks = (Task*)malloc(sizeof(Task) * (count > 0 ? count : 0));
    if (!tasks && count > 0) {
        fprintf(stderr, "内存分配失败\n");
        fclose(fp);
        *out_count = 0;
        return NULL;
    }

    int idx = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (idx >= count) break;
        int size_i = 0;
        float deadline = 0.0f;
        char id[100] = {0};
        char category[200] = {0};
        int crucial = 0;

        int fields = sscanf(line, "%d,%f,%99[^,],%d,%199[^\n\r]", &size_i, &deadline, id, &crucial, category);
        if (fields >= 4) {
            if (size_i < 1 || size_i > 4) size_i = 1;
            tasks[idx].size = size_i;
            tasks[idx].deadline = deadline;
            tasks[idx].crucial = crucial;
            if (fields == 5 && strlen(category) > 0) {
                // trim trailing whitespace/newline
                int len = strlen(category);
                while (len > 0 && (category[len-1] == '\n' || category[len-1] == '\r' || category[len-1] == ' ')) {
                    category[len-1] = '\0'; len--;
                }
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

int main(int argc, char *argv[]) {
    const char *task_file = "tasks.csv";
    if (argc > 1) task_file = argv[1];

    int task_count = 0;
    Task *tasks = read_tasks_from_file(task_file, &task_count);
    if (!tasks || task_count == 0) {
        fprintf(stderr, "未读取到任务或文件为空: %s\n", task_file);
        if (tasks) free(tasks);
        return 1;
    }

    // global deadline 使用所有任务的最小 deadline
    float global_deadline = tasks[0].deadline;
    for (int i = 1; i < task_count; i++) {
        if (tasks[i].deadline < global_deadline) global_deadline = tasks[i].deadline;
    }

    FILE *out = fopen("output_fifo.json", "w");
    if (!out) {
        fprintf(stderr, "无法创建输出文件 output_fifo.json\n");
        free(tasks);
        return 1;
    }

    fprintf(out, "[\n");

    float accumulated_time = 0.0f;
    int completed_count = 0;
    int missed_count = 0;
    int missed_crucial = 0;
    int missed_non_crucial = 0;

    int first = 1;
    for (int i = 0; i < task_count; i++) {
        int sz_idx = tasks[i].size - 1; // 0-based
        if (sz_idx < 0) sz_idx = 0; if (sz_idx > 3) sz_idx = 3;
        float task_time = trans_time_size[sz_idx] + proc_time_size_1d[sz_idx];

        if (accumulated_time + task_time <= global_deadline) {
            // 完成该任务
            if (!first) fprintf(out, ",\n");
            fprintf(out, "  {\"id\": \"%s\", \"size\": %d, \"crucial\": %d}",
                    tasks[i].id, size_values[sz_idx], tasks[i].crucial);
            first = 0;
            accumulated_time += task_time;
            completed_count++;
        } else {
            // 任务错过截止期（FIFO：后续任务通常也会错过，但我们仍然记录所有错失任务）
            missed_count++;
            if (tasks[i].crucial) missed_crucial++; else missed_non_crucial++;
        }
    }

    // 写入 deadline 为最后一项（与其他算法输出一致）
    if (!first) fprintf(out, ",\n");
    fprintf(out, "  {\"deadline\": %.6f}\n", global_deadline);
    fprintf(out, "]\n");
    fclose(out);

    if (missed_count > 0) {
        // 生成 missed_tasks.json
        FILE *mf = fopen("missed_tasks.json", "w");
        if (mf) {
            fprintf(mf, "{\n");
            fprintf(mf, "  \"total_tasks\": %d,\n", task_count);
            fprintf(mf, "  \"completed_tasks\": %d,\n", completed_count);
            fprintf(mf, "  \"missed_tasks\": %d,\n", missed_count);
            fprintf(mf, "  \"missed_crucial\": %d,\n", missed_crucial);
            fprintf(mf, "  \"missed_non_crucial\": %d,\n", missed_non_crucial);
            fprintf(mf, "  \"deadline\": %.6f,\n", global_deadline);
            fprintf(mf, "  \"accumulated_time\": %.6f,\n", accumulated_time);
            fprintf(mf, "  \"missed_task_details\": [\n");

            int first_t = 1;
            for (int i = 0; i < task_count; i++) {
                int sz_idx = tasks[i].size - 1; if (sz_idx < 0) sz_idx = 0; if (sz_idx > 3) sz_idx = 3;
                float task_time = trans_time_size[sz_idx] + proc_time_size_1d[sz_idx];
                if (accumulated_time + task_time <= global_deadline) {
                    // completed, skip
                    accumulated_time += task_time; // keep consistent with earlier accumulation
                    continue;
                }
                if (!first_t) fprintf(mf, ",\n");
                fprintf(mf, "    {\n");
                fprintf(mf, "      \"id\": \"%s\",\n", tasks[i].id);
                fprintf(mf, "      \"size\": %d,\n", tasks[i].size);
                fprintf(mf, "      \"deadline\": %.6f,\n", tasks[i].deadline);
                fprintf(mf, "      \"crucial\": %d\n", tasks[i].crucial);
                fprintf(mf, "    }");
                first_t = 0;
            }

            fprintf(mf, "\n  ]\n}");
            fclose(mf);
            printf("[WARN] 有 %d 个任务错过截止期，详情已保存到 missed_tasks.json\n", missed_count);
        } else {
            fprintf(stderr, "无法创建 missed_tasks.json\n");
        }
    }

    free(tasks);
    printf("[OK] FIFO 调度完成. 完成任务: %d, 错失: %d\n", completed_count, missed_count);
    return 0;
}
