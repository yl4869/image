import os
import random

# 配置参数
DEADLINE = 20.0  # 统一的截止时间
BASE_DIR = "images_cropped"  # 图片文件夹
OUTPUT_DIR = "task_files_ddl20"  # 输出CSV文件的文件夹

# 不同大小对应的关键任务概率
CRUCIAL_PROB = {
    64: 0.2,   # 64大小：20%概率为关键任务
    128: 0.4,  # 128大小：40%概率为关键任务
    256: 0.7,  # 256大小：60%概率为关键任务
    512: 1.0   # 512大小：100%概率为关键任务
}

# 大小映射：实际大小 -> 索引
SIZE_MAPPING = {
    64: 1,
    128: 2,
    256: 3,
    512: 4
}

def parse_filename(filename):

    if not filename.endswith('.jpg'):
        return None
    
    # 去掉扩展名
    name_without_ext = filename[:-4]
    parts = name_without_ext.split('_')
    
    # 至少需要3部分：size_id_category
    if len(parts) < 3:
        return None
    
    try:
        size = int(parts[0])
        # 检查size是否有效
        if size not in SIZE_MAPPING:
            return None
        
        # id是前两部分（size_id）
        img_id = f"{parts[0]}_{parts[1]}"
        
        # category是第三部分及之后的所有部分（用下划线连接）
        category = '_'.join(parts[2:])
        
        return (size, img_id, category)
    except ValueError:
        return None

def generate_csv_for_folder(folder_path, output_csv_path):
    # 获取所有jpg文件
    files = [f for f in os.listdir(folder_path) if f.endswith('.jpg')]
    tasks = []
    
    for filename in files:
        result = parse_filename(filename)
        if result is None:
            continue
        
        size_actual, img_id, category = result
        size_index = SIZE_MAPPING[size_actual]
        
        # 根据概率决定是否为关键任务
        crucial_prob = CRUCIAL_PROB[size_actual]
        is_crucial = 1 if random.random() < crucial_prob else 0
        
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
    random.seed(42)
    # 创建输出文件夹（如果不存在）
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"创建输出文件夹: {OUTPUT_DIR}")

    total_tasks = 0
    
    # 为每个 cropped_1 到 cropped_10 文件夹生成CSV
    for i in range(1, 201):
        folder_name = f"cropped_{i}"
        folder_path = os.path.join(BASE_DIR, folder_name)
        output_csv = os.path.join(OUTPUT_DIR, f"tasks_{i}.csv")
        
        task_count = generate_csv_for_folder(folder_path, output_csv)
        
        if task_count > 0:
            print(f"✓ {folder_name} -> {output_csv} ({task_count} 个任务)")
            total_tasks += task_count
        else:
            print(f"✗ {folder_name} -> 生成失败或无任务")


if __name__ == "__main__":
    main()

