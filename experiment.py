import os
import subprocess
import shutil
import json
import time

# 配置
TASK_FILES_DIR = "task_files_ddl50"  # CSV任务文件目录
RESULT_DIR = "result_list_ddl50"  # 结果保存目录
MAIN_EXE = "main.exe"  # main.c编译后的可执行文件
RESIZING_EXE = "resizing.exe"  # resizing.c编译后的可执行文件
FIFO_EXE = "fifo.exe"  # fifo.c 编译后的可执行文件
FIFO_BATCH_EXE = "fifo_batch.exe"  # fifo_batch.c 编译后的可执行文件
NUM_EXPERIMENTS = 200  # 实验数量

# 输出文件名（程序运行后生成的文件）
MAIN_OUTPUT = "output.json"
MAIN_MISSED_OUTPUT = "missed_tasks.json"  # main.exe 任务丢失时输出的文件
RESIZING_OUTPUT = "output_resizing.json"
FIFO_OUTPUT = "output_fifo.json"
FIFO_BATCH_OUTPUT = "output_fifo_batch.json"
CF_BATCH_EXE = "cf-batch.exe"  # cf-batch.c 编译后的可执行文件
CF_BATCH_OUTPUT = "output_cf_batch.json"

def ensure_executables():
    print("\n正在重新编译程序（确保使用最新代码）...")
    
    try:
        # 编译 main.c
        print(f"编译 main.c...")
        result = subprocess.run(["gcc", "main.c", "-o", MAIN_EXE], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[X] 编译 main.c 失败: {result.stderr}")
            return False
        print(f"[OK] 成功编译 {MAIN_EXE}")
        
        # 编译 resizing.c
        print(f"编译 resizing.c...")
        result = subprocess.run(["gcc", "resizing.c", "-o", RESIZING_EXE], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[X] 编译 resizing.c 失败: {result.stderr}")
            return False
        print(f"[OK] 成功编译 {RESIZING_EXE}")

        # 编译 fifo.c
        print(f"编译 fifo.c...")
        result = subprocess.run(["gcc", "fifo.c", "-o", "fifo.exe"],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[X] 编译 fifo.c 失败: {result.stderr}")
            return False
        print(f"[OK] 成功编译 fifo.exe")
        
        # 编译 fifo_batch.c
        print(f"编译 fifo_batch.c...")
        result = subprocess.run(["gcc", "fifo_batch.c", "-o", FIFO_BATCH_EXE],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[X] 编译 fifo_batch.c 失败: {result.stderr}")
            return False
        print(f"[OK] 成功编译 {FIFO_BATCH_EXE}")
        
        # 编译 cf-batch.c
        print(f"编译 cf-batch.c...")
        result = subprocess.run(["gcc", "cf-batch.c", "-o", CF_BATCH_EXE],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[X] 编译 cf-batch.c 失败: {result.stderr}")
            return False
        print(f"[OK] 成功编译 {CF_BATCH_EXE}")
        
    except FileNotFoundError:
        print("[X] 错误: 未找到 gcc 编译器，请确保已安装 gcc")
        return False
    
    print("[OK] 编译完成！\n")
    return True

def run_experiment(experiment_id):
    """运行单个实验"""
    print(f"\n{'='*60}")
    print(f"实验 {experiment_id} / {NUM_EXPERIMENTS}")
    print(f"{'='*60}")
    
    # 准备路径
    task_file = os.path.join(TASK_FILES_DIR, f"tasks_{experiment_id}.csv")
    result_folder = os.path.join(RESULT_DIR, f"result_{experiment_id}")
    
    print(f"任务文件: {task_file}")
    print(f"结果保存到: {result_folder}")
    
    # 检查任务文件是否存在
    if not os.path.exists(task_file):
        print(f"[X] 任务文件不存在: {task_file}")
        return False
    
    # 创建结果文件夹
    os.makedirs(result_folder, exist_ok=True)
    
    # 清理上一次实验遗留的输出文件（防止混淆）
    print("\n[0] 清理旧的输出文件...")
    output_files_to_clean = [MAIN_OUTPUT, MAIN_MISSED_OUTPUT, RESIZING_OUTPUT, FIFO_OUTPUT, FIFO_BATCH_OUTPUT]
    for output_file in output_files_to_clean:
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                print(f"    - 已删除旧文件: {output_file}")
            except Exception as e:
                print(f"    - 警告: 无法删除 {output_file}: {e}")
    
    # 运行 main.exe
    print(f"\n[1] 运行 {MAIN_EXE} (动态调度算法)...")
    start_time = time.time()
    try:
        result = subprocess.run([MAIN_EXE, task_file], 
                              capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            print(f"[X] {MAIN_EXE} 运行失败")
            print(f"错误输出: {result.stderr}")
            return False
        
        print(f"[OK] {MAIN_EXE} 运行成功 (耗时: {elapsed:.2f}秒)")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")
        
        # 复制结果文件
        if os.path.exists(MAIN_OUTPUT):
            main_result_path = os.path.join(result_folder, "main_result.json")
            shutil.copy(MAIN_OUTPUT, main_result_path)
            print(f"[OK] 结果已保存: {main_result_path}")
        else:
            print(f"[!] 警告: 未找到输出文件 {MAIN_OUTPUT}")
        
        # 检查并复制丢失任务文件（如果存在）
        if os.path.exists(MAIN_MISSED_OUTPUT):
            missed_result_path = os.path.join(result_folder, "main_missed_tasks.json")
            shutil.copy(MAIN_MISSED_OUTPUT, missed_result_path)
            print(f"[!] 警告: 检测到任务丢失，详情已保存: {missed_result_path}")
            
            # 读取并显示丢失任务统计
            try:
                with open(MAIN_MISSED_OUTPUT, 'r') as f:
                    missed_data = json.load(f)
                    print(f"    - 总任务: {missed_data.get('total_tasks', 'N/A')}")
                    print(f"    - 完成任务: {missed_data.get('completed_tasks', 'N/A')}")
                    print(f"    - 丢失任务: {missed_data.get('missed_tasks', 'N/A')}")
                    print(f"    - 丢失关键任务: {missed_data.get('missed_crucial', 'N/A')}")
            except Exception as e:
                print(f"    - 读取丢失任务详情失败: {e}")
    
    except subprocess.TimeoutExpired:
        print(f"[X] {MAIN_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {MAIN_EXE} 时出错: {e}")
        return False
    
    # 运行 resizing.exe
    print(f"\n[2] 运行 {RESIZING_EXE} (贪心调度算法)...")
    start_time = time.time()
    try:
        result = subprocess.run([RESIZING_EXE, task_file], 
                              capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            print(f"[X] {RESIZING_EXE} 运行失败")
            print(f"错误输出: {result.stderr}")
            return False
        
        print(f"[OK] {RESIZING_EXE} 运行成功 (耗时: {elapsed:.2f}秒)")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")
        
        # 复制结果文件
        if os.path.exists(RESIZING_OUTPUT):
            resizing_result_path = os.path.join(result_folder, "resizing_result.json")
            shutil.copy(RESIZING_OUTPUT, resizing_result_path)
            print(f"[OK] 结果已保存: {resizing_result_path}")
            
            # 检查是否有任务丢失
            with open(RESIZING_OUTPUT, 'r') as f:
                data = json.load(f)
                if data and data[0] == -1:
                    print(f"[!] 警告: 贪心调度算法检测到任务丢失 (deadline不足)")
        else:
            print(f"[!] 警告: 未找到输出文件 {RESIZING_OUTPUT}")
    
    except subprocess.TimeoutExpired:
        print(f"[X] {RESIZING_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {RESIZING_EXE} 时出错: {e}")
        return False

    # 运行 fifo.exe
    print(f"\n[3] 运行 {FIFO_EXE} (FIFO 调度算法)...")
    start_time = time.time()
    try:
        result = subprocess.run([FIFO_EXE, task_file],
                              capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time

        if result.returncode != 0:
            print(f"[X] {FIFO_EXE} 运行失败")
            print(f"错误输出: {result.stderr}")
            return False

        print(f"[OK] {FIFO_EXE} 运行成功 (耗时: {elapsed:.2f}秒)")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")

        # 复制结果文件
        if os.path.exists(FIFO_OUTPUT):
            fifo_result_path = os.path.join(result_folder, "fifo_result.json")
            shutil.copy(FIFO_OUTPUT, fifo_result_path)
            print(f"[OK] 结果已保存: {fifo_result_path}")

            # 检查是否有任务丢失（与其他算法一致的 -1 语义）
            try:
                with open(FIFO_OUTPUT, 'r') as f:
                    data = json.load(f)
                    if data and isinstance(data, list) and len(data) > 0 and data[0] == -1:
                        print(f"[!] 警告: FIFO 调度检测到任务丢失 (deadline不足)")
            except Exception:
                pass
        else:
            print(f"[!] 警告: 未找到输出文件 {FIFO_OUTPUT}")

    except subprocess.TimeoutExpired:
        print(f"[X] {FIFO_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {FIFO_EXE} 时出错: {e}")
        return False
    
    # 运行 fifo_batch.exe
    print(f"\n[4] 运行 {FIFO_BATCH_EXE} (FIFO 批处理调度算法)...")
    start_time = time.time()
    try:
        result = subprocess.run([FIFO_BATCH_EXE, task_file],
                              capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time

        if result.returncode != 0:
            print(f"[X] {FIFO_BATCH_EXE} 运行失败")
            print(f"错误输出: {result.stderr}")
            return False

        print(f"[OK] {FIFO_BATCH_EXE} 运行成功 (耗时: {elapsed:.2f}秒)")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")

        # 复制结果文件
        if os.path.exists(FIFO_BATCH_OUTPUT):
            fifo_batch_result_path = os.path.join(result_folder, "fifo_batch_result.json")
            shutil.copy(FIFO_BATCH_OUTPUT, fifo_batch_result_path)
            print(f"[OK] 结果已保存: {fifo_batch_result_path}")

            # 检查是否有任务丢失（与其他算法一致的 -1 语义）
            try:
                with open(FIFO_BATCH_OUTPUT, 'r') as f:
                    data = json.load(f)
                    if data and isinstance(data, list) and len(data) > 0 and data[0] == -1:
                        print(f"[!] 警告: FIFO 批处理调度检测到任务丢失 (deadline不足)")
            except Exception:
                pass
        else:
            print(f"[!] 警告: 未找到输出文件 {FIFO_BATCH_OUTPUT}")

    except subprocess.TimeoutExpired:
        print(f"[X] {FIFO_BATCH_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {FIFO_BATCH_EXE} 时出错: {e}")
        return False

    # 运行 cf-batch.exe
    print(f"\n[5] 运行 {CF_BATCH_EXE} (CF-BATCH 调度算法)...")
    start_time = time.time()
    try:
        result = subprocess.run([CF_BATCH_EXE, task_file],
                              capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time

        if result.returncode != 0:
            print(f"[X] {CF_BATCH_EXE} 运行失败")
            print(f"错误输出: {result.stderr}")
            return False

        print(f"[OK] {CF_BATCH_EXE} 运行成功 (耗时: {elapsed:.2f}秒)")
        if result.stdout:
            print(f"输出: {result.stdout.strip()}")

        # 复制结果文件
        if os.path.exists(CF_BATCH_OUTPUT):
            cf_batch_result_path = os.path.join(result_folder, "cf_batch_result.json")
            shutil.copy(CF_BATCH_OUTPUT, cf_batch_result_path)
            print(f"[OK] 结果已保存: {cf_batch_result_path}")

            # 检查是否有任务丢失（与其他算法一致的 -1 语义）
            try:
                with open(CF_BATCH_OUTPUT, 'r') as f:
                    data = json.load(f)
                    if data and isinstance(data, list) and len(data) > 0 and data[0] == -1:
                        print(f"[!] 警告: CF-BATCH 调度检测到任务丢失 (deadline不足)")
            except Exception:
                pass
        else:
            print(f"[!] 警告: 未找到输出文件 {CF_BATCH_OUTPUT}")

    except subprocess.TimeoutExpired:
        print(f"[X] {CF_BATCH_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {CF_BATCH_EXE} 时出错: {e}")
        return False

    print(f"\n[OK] 实验 {experiment_id} 完成!")
    return True


def generate_summary():
    """生成实验汇总报告"""
    print(f"\n{'='*60}")
    print("生成实验汇总报告...")
    print(f"{'='*60}\n")
    
    summary = {
        "total_experiments": NUM_EXPERIMENTS,
        "experiments": []
    }
    
    for i in range(1, NUM_EXPERIMENTS + 1):
        result_folder = os.path.join(RESULT_DIR, f"result_{i}")
        main_result = os.path.join(result_folder, "main_result.json")
        main_missed = os.path.join(result_folder, "main_missed_tasks.json")
        resizing_result = os.path.join(result_folder, "resizing_result.json")
        
        exp_summary = {
            "experiment_id": i,
            "task_file": f"tasks_{i}.csv",
            "main_result_exists": os.path.exists(main_result),
            "main_missed_exists": os.path.exists(main_missed),
            "resizing_result_exists": os.path.exists(resizing_result)
        }
        
        # 尝试读取并统计任务数量和是否丢失
        try:
            if os.path.exists(main_result):
                with open(main_result, 'r') as f:
                    data = json.load(f)
                    # 统计任务总数（排除deadline条目）
                    task_count = 0
                    for batch in data:
                        if "images" in batch:
                            task_count += len(batch["images"])
                    exp_summary["main_task_count"] = task_count

                # 检查是否有丢失任务文件
                if os.path.exists(main_missed):
                    with open(main_missed, 'r') as mf:
                        missed_data = json.load(mf)
                        exp_summary["main_missed_count"] = missed_data.get("missed_tasks", 0)
                        exp_summary["main_missed_crucial"] = missed_data.get("missed_crucial", 0)
                        exp_summary["main_status"] = f"部分失败 (丢失{missed_data.get('missed_tasks', 0)}个任务)"
                else:
                    exp_summary["main_status"] = "OK"

            if os.path.exists(resizing_result):
                with open(resizing_result, 'r') as f:
                    data = json.load(f)
                    # 检查是否任务丢失
                    if isinstance(data, list) and len(data) > 0 and data[0] == -1:
                        exp_summary["resizing_status"] = "FAILED (任务丢失)"
                    else:
                        task_count = 0
                        for batch in data:
                            if "images" in batch:
                                task_count += len(batch["images"])
                        exp_summary["resizing_task_count"] = task_count
                        exp_summary["resizing_status"] = "OK"

        except Exception as e:
            print(f"[!] 读取结果或统计时出错: {e}")

        summary["experiments"].append(exp_summary)
    
    # 保存汇总报告
    summary_file = os.path.join(RESULT_DIR, "experiment_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] 汇总报告已保存: {summary_file}\n")
    
    # 打印汇总表格
    print("实验结果汇总:")
    print("-" * 100)
    print(f"{'实验ID':<8} {'任务文件':<18} {'Main结果':<35} {'Resizing结果':<35}")
    print("-" * 100)
    
    for exp in summary["experiments"]:
        exp_id = exp["experiment_id"]
        task_file = exp["task_file"]
        main_status = exp.get("main_status", "NOT FOUND")
        resizing_status = exp.get("resizing_status", "NOT FOUND")
        
        # 如果有丢失任务信息，添加到状态显示中
        if exp.get("main_missed_exists", False):
            missed_count = exp.get("main_missed_count", 0)
            missed_crucial = exp.get("main_missed_crucial", 0)
            main_status += f" [丢失:{missed_count}({missed_crucial}关键)]"
        

    


def main():
     # 每次运行时重新编译，确保使用最新代码
    if not ensure_executables():
        print("[X] 编译失败，退出")
        return
    
    # 创建结果目录
    os.makedirs(RESULT_DIR, exist_ok=True)
    # 运行所有实验
    success_count = 0
    fail_count = 0
    for i in range(1, NUM_EXPERIMENTS + 1):
        if run_experiment(i):
            success_count += 1
        else:
            fail_count += 1
    
    # 生成汇总报告
    generate_summary()
if __name__ == "__main__":
    main()

