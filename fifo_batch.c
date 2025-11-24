#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// FIFO 批处理调度器：按输入顺序构建批次，当连续任务尺寸相同则并入同一批次
// 输入：CSV 文件（size,deadline,id,crucial,category），size 为 1-4（对应 64/128/256/512）
// 输出：output_fifo_batch.json（当前目录），若存在未完成任务则生成 missed_tasks_batch.json

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

Task* read_tasks_from_file(const char *filename, int *out_count) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        fprintf(stderr, "无法打开任务文件: %s\n", filename);
        *out_count = 0;
        return NULL;
    }

    char line[512];
    int count = 0;

    if (fgets(line, sizeof(line), fp)) {
        if (strstr(line, "size") && strstr(line, "deadline")) {
            // 有表头
        } else {
            count++;
        }
    }
    while (fgets(line, sizeof(line), fp)) count++;

    rewind(fp);
    if (fgets(line, sizeof(line), fp)) {
        if (!(strstr(line, "size") && strstr(line, "deadline"))) {
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

    // 全局截止期取所有任务最小值
    float global_deadline = tasks[0].deadline;
    for (int i = 1; i < task_count; i++) {
        if (tasks[i].deadline < global_deadline) global_deadline = tasks[i].deadline;
    }

    FILE *out = fopen("output_fifo_batch.json", "w");
    if (!out) {
        fprintf(stderr, "无法创建输出文件 output_fifo_batch.json\n");
        free(tasks);
        return 1;
    }

    fprintf(out, "[\n");

    float accumulated_time = 0.0f;
    int completed_count = 0;
    int missed_count = 0;
    int missed_crucial = 0;
    int missed_non_crucial = 0;

    int first_obj = 1;

    int idx = 0;
    while (idx < task_count) {
        // 开始一个新批次，从当前 idx 开始收集连续相同尺寸的任务
        int current_size = tasks[idx].size;
        int sz_idx = current_size - 1; if (sz_idx < 0) sz_idx = 0; if (sz_idx > 3) sz_idx = 3;

        // 计算本批次的任务列表（连续相同尺寸）
        int batch_start = idx;
        int batch_end = idx;
        while (batch_end + 1 < task_count && tasks[batch_end + 1].size == current_size) {
            batch_end++;
        }

        // 计算批次时间：trans_time_size * n + proc_time_size_1d（n是批次内任务数量）
        int batch_size = batch_end - batch_start + 1;
        float batch_time = trans_time_size[sz_idx] * batch_size + proc_time_size_1d[sz_idx];

        // 判断整个批次是否能完成
        if (accumulated_time + batch_time <= global_deadline) {
            // 整个批次都能完成
            if (!first_obj) fprintf(out, ",\n");
            fprintf(out, "  {\n    \"size\": %d,\n    \"images\": [\n", size_values[sz_idx]);
            
            for (int j = batch_start; j <= batch_end; j++) {
                if (j > batch_start) fprintf(out, ",\n");
                fprintf(out, "      {\"id\": \"%s\", \"crucial\": %d}", tasks[j].id, tasks[j].crucial);
                completed_count++;
            }
            
            fprintf(out, "\n    ]\n  }");
            first_obj = 0;
            accumulated_time += batch_time;
        } else {
            // 整个批次都错过截止
            for (int j = batch_start; j <= batch_end; j++) {
                missed_count++;
                if (tasks[j].crucial) missed_crucial++; else missed_non_crucial++;
            }
        }

        idx = batch_end + 1; // 移动到下一个批次起点
    }

    // 写入 deadline
    if (!first_obj) fprintf(out, ",\n");
    fprintf(out, "  {\"deadline\": %.6f}\n", global_deadline);
    fprintf(out, "]\n");
    fclose(out);

    // 生成 missed_tasks_batch.json（如果有错失）
    if (missed_count > 0) {
        FILE *mf = fopen("missed_tasks_batch.json", "w");
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
            // 重新遍历以输出错失详情（按照输入顺序，使用批次时间计算）
            float tmp_acc = 0.0f;
            int tmp_idx = 0;
            while (tmp_idx < task_count) {
                int tmp_size = tasks[tmp_idx].size;
                int tmp_sz_idx = tmp_size - 1; if (tmp_sz_idx < 0) tmp_sz_idx = 0; if (tmp_sz_idx > 3) tmp_sz_idx = 3;
                
                // 计算批次范围
                int tmp_batch_start = tmp_idx;
                int tmp_batch_end = tmp_idx;
                while (tmp_batch_end + 1 < task_count && tasks[tmp_batch_end + 1].size == tmp_size) {
                    tmp_batch_end++;
                }
                
                // 计算批次时间
                int tmp_batch_size = tmp_batch_end - tmp_batch_start + 1;
                float tmp_batch_time = trans_time_size[tmp_sz_idx] * tmp_batch_size + proc_time_size_1d[tmp_sz_idx];
                
                if (tmp_acc + tmp_batch_time <= global_deadline) {
                    tmp_acc += tmp_batch_time;
                    tmp_idx = tmp_batch_end + 1;
                    continue; // 整个批次已完成
                }
                
                // 整个批次都错过，输出所有任务
                for (int k = tmp_batch_start; k <= tmp_batch_end; k++) {
                    if (!first_t) fprintf(mf, ",\n");
                    fprintf(mf, "    {\n");
                    fprintf(mf, "      \"id\": \"%s\",\n", tasks[k].id);
                    fprintf(mf, "      \"size\": %d,\n", tasks[k].size);
                    fprintf(mf, "      \"deadline\": %.6f,\n", tasks[k].deadline);
                    fprintf(mf, "      \"crucial\": %d\n", tasks[k].crucial);
                    fprintf(mf, "    }");
                    first_t = 0;
                }
                
                tmp_idx = tmp_batch_end + 1;
            }

            fprintf(mf, "\n  ]\n}");
            fclose(mf);
            printf("[WARN] 有 %d 个任务错过截止期，详情已保存到 missed_tasks_batch.json\n", missed_count);
        } else {
            fprintf(stderr, "无法创建 missed_tasks_batch.json\n");
        }
    }

    free(tasks);
    printf("[OK] FIFO 批处理调度完成. 完成任务: %d, 错失: %d\n", completed_count, missed_count);
    return 0;
}
