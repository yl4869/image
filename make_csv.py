import os
import sys

# 配置参数
DEADLINE = 50.0  # 统一的截止时间
BASE_DIR = "sampled_crops"  # 图片文件夹
OUTPUT_DIR = "new_tasks/task_files_ddl50"  # 输出CSV文件的文件夹

# 大小映射：实际大小 -> 索引
SIZE_MAPPING = {
    64: 1,
    128: 2,
    256: 3,
    512: 4
}

def resolve_path(path_value):
    if os.path.isabs(path_value):
        return path_value
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, path_value)

def setup_console_encoding():
    # Ensure predictable console encoding on Windows terminals.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def parse_filename(filename):

    if not filename.endswith('.jpg'):
        return None
    
    # 去掉扩展名
    name_without_ext = filename[:-4]
    parts = name_without_ext.split('_')
    
    # 新格式至少需要4部分：size_id_category_ttc
    if len(parts) < 4:
        return None
    
    try:
        size = int(parts[0])
        # 检查size是否有效
        if size not in SIZE_MAPPING:
            return None
        
        # id是前两部分（size_id）
        img_id = f"{parts[0]}_{parts[1]}"
        
        # ttc 是最后一部分
        ttc = float(parts[-1])

        # category是第三部分到倒数第二部分（用下划线连接）
        category = '_'.join(parts[2:-1])
        if not category:
            return None
        
        return (size, img_id, category, ttc)
    except ValueError:
        return None

def is_crucial_by_ttc(ttc):
    # 关键任务规则：0 < ttc < 2
    return 1 if 0 < ttc < 2 else 0

def generate_csv_for_folder(folder_path, output_csv_path):
    if not os.path.isdir(folder_path):
        return None

    # 获取所有jpg文件
    files = [f for f in os.listdir(folder_path) if f.endswith('.jpg')]
    tasks = []
    
    for filename in files:
        result = parse_filename(filename)
        if result is None:
            continue
        
        size_actual, img_id, category, ttc = result
        size_index = SIZE_MAPPING[size_actual]
        
        # 根据 ttc 决定是否为关键任务
        is_crucial = is_crucial_by_ttc(ttc)
        
        tasks.append({
            'size': size_index,  # 使用索引（1-4）
            'deadline': DEADLINE,
            'id': img_id,
            'crucial': is_crucial,
            'category': category
        })
    
    # 按照 size 和 id 排序，保证输出一致性
    tasks.sort(key=lambda x: (x['size'], x['id']))
    
    # 写入CSV文件
    with open(output_csv_path, 'w', encoding='utf-8') as f:
        # 写入标题行
        f.write("size,deadline,id,crucial,category\n")
        
        # 写入数据行
        for task in tasks:
            f.write(f"{task['size']},{task['deadline']},{task['id']},{task['crucial']},{task['category']}\n")
    
    return len(tasks)

def main():
    setup_console_encoding()
    base_dir = resolve_path(BASE_DIR)
    output_dir = resolve_path(OUTPUT_DIR)

    # 创建输出文件夹（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    total_tasks = 0
    generated_files = 0
    skipped_folders = 0
    
    # 为每个 cropped_1 到 cropped_200 文件夹生成CSV
    for i in range(1, 201):
        folder_name = f"cropped_{i}"
        folder_path = os.path.join(base_dir, folder_name)
        output_csv = os.path.join(output_dir, f"tasks_{i}.csv")
        
        task_count = generate_csv_for_folder(folder_path, output_csv)

        if task_count is None:
            print(f"[SKIP] {folder_name}: folder not found")
            skipped_folders += 1
        elif task_count > 0:
            print(f"[OK]   {folder_name} -> {output_csv} ({task_count} tasks)")
            total_tasks += task_count
            generated_files += 1
        else:
            print(f"[EMPTY] {folder_name}: no valid jpg tasks")

    print(
        f"Done. Generated {generated_files} CSV files, "
        f"{total_tasks} tasks total, skipped {skipped_folders} missing folders."
    )


if __name__ == "__main__":
    main()

