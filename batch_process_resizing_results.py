import os
import json
from pathlib import Path
from simple_inference import SimpleInference, process_single_result


def find_all_resizing_result_files(base_folder):
    base_path = Path(base_folder)
    if not base_path.exists():
        print(f"[X] 文件夹不存在: {base_folder}")
        return []
    
    file_pairs = []
    # 遍历所有子目录
    for result_dir in sorted(base_path.iterdir()):
        if result_dir.is_dir():
            resizing_result_path = result_dir / "resizing_result.json"
            if resizing_result_path.exists():
                resizing_time_path = result_dir / "resizing_time.json"
                file_pairs.append((str(resizing_result_path), str(resizing_time_path)))
    
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


def check_if_minus_one(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # 检查是否为 [-1]
        if isinstance(content, list) and len(content) == 1 and content[0] == -1:
            return True
        return False
    except Exception as e:
        print(f"[!] 检查文件时出错: {e}")
        return False


def save_minus_one_result(output_path):
    """
    保存 [-1] 到输出文件
    
    Args:
        output_path: 输出文件路径
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump([-1], f, ensure_ascii=False, indent=2)
        print(f"[OK] 已保存 [-1] 到: {output_path}")
    except Exception as e:
        print(f"[X] 保存 [-1] 失败: {e}")


def batch_process_folder(base_folder, model_paths, num_classes=7, skip_existing=False):
    # 查找所有 resizing_result.json 文件
    file_pairs = find_all_resizing_result_files(base_folder)
    
    if not file_pairs:
        print(f"[!] 未找到任何 resizing_result.json 文件")
        return
    
    print(f"[OK] 找到 {len(file_pairs)} 个 resizing_result.json 文件\n")
    
    # 由于所有任务使用相同的模型，只需加载一次
    print("正在加载模型...")
    # 这里暂时使用一个占位的 image_folder，实际会在处理时动态调整
    inference = SimpleInference(model_paths, "images_cropped/cropped_1", num_classes=num_classes)
    print()
    
    # 统计信息
    processed_count = 0
    skipped_count = 0
    minus_one_count = 0
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
            # 检查是否为 [-1] 的特殊情况
            if check_if_minus_one(input_path):
                print(f"检测到特殊文件内容: [-1]")
                save_minus_one_result(output_path)
                minus_one_count += 1
                print(f"\n[OK] 完成 (特殊) [{idx}/{len(file_pairs)}]: {output_path}")
                continue
            
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
    
    # 打印总结
    print(f"\n{'='*80}")
    print(f"批量处理完成")
    print(f"{'='*80}")
    print(f"总文件数:   {len(file_pairs)}")
    print(f"已处理:     {processed_count}")
    print(f"[-1]文件:   {minus_one_count}")
    print(f"已跳过:     {skipped_count}")
    print(f"失败:       {error_count}")
    print(f"{'='*80}\n")


def main():
    folders_to_process = [
        'result_with_fifo_edf/result_list_ddl20',

    ]
    
    # 是否跳过已存在的 resizing_time.json 文件（True=跳过，False=覆盖）
    skip_existing = False
    
    # 分类数量
    num_classes = 7
    
    # 模型路径配置
    model_paths = {
        64: 'back/model/model_64.pth',
        128: 'back/model/model_128.pth',
        256: 'back/model/model_256.pth',
        512: 'back/model/model_512.pth'
    }
    
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

