import os
from pathlib import Path
from simple_inference import SimpleInference, process_single_result


def find_all_main_result_files(base_folder):

    base_path = Path(base_folder)
    if not base_path.exists():
        print(f"[X] 文件夹不存在: {base_folder}")
        return []
    
    file_pairs = []
    # 遍历所有子目录
    for result_dir in sorted(base_path.iterdir()):
        if result_dir.is_dir():
            main_result_path = result_dir / "main_result.json"
            if main_result_path.exists():
                main_time_path = result_dir / "main_time.json"
                file_pairs.append((str(main_result_path), str(main_time_path)))
    
    return file_pairs


def extract_cropped_folder_from_result_path(result_path):

    result_path_obj = Path(result_path)
    # 获取 result_xxx 文件夹名称
    result_folder_name = result_path_obj.parent.name
    
    # 提取数字部分，如 result_153 -> 153
    if result_folder_name.startswith('result_'):
        folder_number = result_folder_name.replace('result_', '')
        cropped_folder = f"images_cropped/cropped_{folder_number}"
        return cropped_folder
    
    # 默认返回 cropped_1
    return "images_cropped/cropped_1"


def batch_process_folder(base_folder, model_paths, num_classes=7, skip_existing=False):
    print(f"\n{'='*80}")
    print(f"开始批量处理文件夹: {base_folder}")
    print(f"{'='*80}\n")
    
    # 查找所有 main_result.json 文件
    file_pairs = find_all_main_result_files(base_folder)
    
    if not file_pairs:
        print(f"[!] 未找到任何 main_result.json 文件")
        return
    
    print(f"[OK] 找到 {len(file_pairs)} 个 main_result.json 文件\n")
    
    # 由于所有任务使用相同的模型，只需加载一次
    # 注意：这里假设所有图片都在对应的 cropped_xxx 文件夹中
    # 如果图片文件夹不同，需要为每个任务单独处理
    print("正在加载模型...")
    # 这里暂时使用一个占位的 image_folder，实际会在处理时动态调整
    inference = SimpleInference(model_paths, "images_cropped/cropped_1", num_classes=num_classes)
    print()
    
    # 统计信息
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    # 处理每个文件
    for idx, (input_path, output_path) in enumerate(file_pairs, 1):
        # 检查是否跳过已存在的文件
        if skip_existing and os.path.exists(output_path):
            print(f"[{idx}/{len(file_pairs)}] 跳过 (已存在): {input_path}")
            skipped_count += 1
            continue
        
        print(f"\n{'='*80}")
        print(f"[{idx}/{len(file_pairs)}] 处理文件: {input_path}")
        print(f"{'='*80}")
        
        try:
            # 动态获取对应的图片文件夹
            image_folder = extract_cropped_folder_from_result_path(input_path)
            
            # 检查图片文件夹是否存在
            if not os.path.exists(image_folder):
                print(f"[!] 警告: 图片文件夹不存在 {image_folder}，使用默认文件夹")
                image_folder = "images_cropped/cropped_1"
            
            print(f"使用图片文件夹: {image_folder}")
            
            # 更新 inference 实例的 image_folder
            inference.image_folder = image_folder
            
            # 处理文件
            results = process_single_result(
                input_path, 
                output_path, 
                model_paths, 
                image_folder,
                num_classes=num_classes,
                inference_instance=inference
            )
            
            processed_count += 1
            print(f"\n[OK] 完成 [{idx}/{len(file_pairs)}]: {output_path}")
            
        except Exception as e:
            print(f"\n[X] 处理失败 [{idx}/{len(file_pairs)}]: {input_path}")
            print(f"    错误信息: {e}")
            error_count += 1
            import traceback
            traceback.print_exc()
    


def main():

    # 要处理的文件夹列表
    folders_to_process = [
        'result_list_ddl20',
        'result_list_ddl25',
        'result_list_ddl30',
        'result_list_ddl35',
        'result_list_ddl40',
        'result_list_ddl45',
        'result_list_ddl50',
    ]
    
    # 是否跳过已存在的 main_time.json 文件（True=跳过，False=覆盖）
    skip_existing = False
    
    # 分类数量
    num_classes = 7
    
    # 模型路径配置
    model_paths = {
        64: 'model/model_64.pth',
        128: 'model/model_128.pth',
        256: 'model/model_256.pth',
        512: 'model/model_512.pth'
    }
    
    # 检查模型文件是否存在
    print("\n检查模型文件...")
    all_models_exist = True
    for size, path in model_paths.items():
        if os.path.exists(path):
            print(f"  [OK] {size}px: {path}")
        else:
            print(f"  [X] {size}px: {path} (不存在)")
            all_models_exist = False
    
    if not all_models_exist:
        print("\n[X] 部分模型文件不存在，请检查模型路径")
        print("程序退出")
        return
    
    # 显示配置信息
    print(f"\n将处理以下文件夹:")
    for folder in folders_to_process:
        exists = os.path.exists(folder)
        status = "[OK]" if exists else "[X]"
        print(f"  {status} {folder}")
    print(f"\n跳过已存在文件: {'是' if skip_existing else '否'}")
    print(f"分类数量: {num_classes}")
    
    # 处理每个指定的文件夹
    for folder in folders_to_process:
        batch_process_folder(
            folder, 
            model_paths, 
            num_classes=num_classes,
            skip_existing=skip_existing
        )


if __name__ == '__main__':
    main()

