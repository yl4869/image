#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除指定文件夹中所有指定名称的文件
支持递归搜索子文件夹
"""

import os
import sys
from pathlib import Path

# ==================== 配置区域 ====================
# 在这里直接修改以下两个变量，然后运行程序

# 要删除的文件名（可以是完整文件名或部分匹配）
TARGET_FILE_NAME = "resizing_time.json"

# 要搜索的文件夹路径
SEARCH_FOLDER = "result_with_fifo_edf"

# 是否显示详细信息（True/False）
SHOW_DETAILS = True

# 是否在删除前确认（True/False）
CONFIRM_BEFORE_DELETE = True

# ==================== 配置区域结束 ====================


def find_files_by_name(folder_path, file_name):
    """
    递归查找指定文件夹中所有匹配的文件
    
    Args:
        folder_path: 要搜索的文件夹路径
        file_name: 要查找的文件名
    
    Returns:
        匹配的文件路径列表
    """
    matching_files = []
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"[错误] 文件夹不存在: {folder_path}")
        return matching_files
    
    if not folder.is_dir():
        print(f"[错误] 路径不是文件夹: {folder_path}")
        return matching_files
    
    print(f"\n正在搜索文件夹: {folder_path}")
    print(f"查找文件名: {file_name}")
    print("-" * 60)
    
    # 递归搜索所有文件
    try:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file == file_name or file_name in file:
                    file_path = os.path.join(root, file)
                    matching_files.append(file_path)
                    if SHOW_DETAILS:
                        print(f"  找到: {file_path}")
    except Exception as e:
        print(f"[错误] 搜索文件时出错: {e}")
    
    return matching_files


def delete_files(file_list, confirm=True):
    """
    删除文件列表中的所有文件
    
    Args:
        file_list: 要删除的文件路径列表
        confirm: 是否在删除前确认
    
    Returns:
        成功删除的文件数量
    """
    if not file_list:
        print("\n没有找到匹配的文件。")
        return 0
    
    print(f"\n找到 {len(file_list)} 个匹配的文件:")
    for i, file_path in enumerate(file_list, 1):
        print(f"  {i}. {file_path}")
    
    if confirm:
        print("\n" + "=" * 60)
        response = input(f"确认要删除这 {len(file_list)} 个文件吗？(yes/no): ").strip().lower()
        if response not in ['yes', 'y', '是']:
            print("操作已取消。")
            return 0
    
    deleted_count = 0
    failed_count = 0
    
    print("\n开始删除文件...")
    print("-" * 60)
    
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
                if SHOW_DETAILS:
                    print(f"  [✓] 已删除: {file_path}")
            else:
                print(f"  [!] 文件不存在（可能已被删除）: {file_path}")
        except Exception as e:
            failed_count += 1
            print(f"  [X] 删除失败: {file_path}")
            print(f"      错误信息: {e}")
    
    print("-" * 60)
    print(f"\n删除完成!")
    print(f"  成功删除: {deleted_count} 个文件")
    if failed_count > 0:
        print(f"  删除失败: {failed_count} 个文件")
    
    return deleted_count


def main():
    """主函数"""
    print("=" * 60)
    print("文件删除工具")
    print("=" * 60)
    
    # 检查配置
    if not TARGET_FILE_NAME:
        print("[错误] 请设置 TARGET_FILE_NAME 变量")
        return
    
    if not SEARCH_FOLDER:
        print("[错误] 请设置 SEARCH_FOLDER 变量")
        return
    
    # 查找文件
    matching_files = find_files_by_name(SEARCH_FOLDER, TARGET_FILE_NAME)
    
    # 删除文件
    if matching_files:
        delete_files(matching_files, confirm=CONFIRM_BEFORE_DELETE)
    else:
        print("\n没有找到匹配的文件。")
    
    print("\n程序执行完成。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断。")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

