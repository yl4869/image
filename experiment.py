import os
import subprocess
import shutil
import json
import time

# 配置
TASK_FILES_DIR = "tasks/task_files_ddl25"  # CSV任务文件目录
RESULT_DIR = "test/test2"  # 结果保存目录
FIFO_BATCH_EXE = "./fifo_batch"  # fifo_batch.c 编译后的可执行文件
CF_BATCH_EXE = "./cf_batch"  # cf-batch.c 编译后的可执行文件
FIFO_EXE = "./fifo" # fifo.c 编译后的可执行文件
NUM_EXPERIMENTS = 200  # 实验数量

# 输出文件名（程序运行后生成的文件）
FIFO_BATCH_OUTPUT = "output_fifo_batch.json"
CF_BATCH_OUTPUT = "output_cf_batch.json"
FIFO_OUTPUT = "output_fifo.json"

def ensure_executables():
    print("\n正在重新编译程序（确保使用最新代码）...")
    
    try:
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
        
        # 编译 fifo.c
        print(f"编译 fifo.c...")
        result = subprocess.run(["gcc", "fifo.c", "-o", FIFO_EXE],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[X] 编译 fifo.c 失败: {result.stderr}")
            return False
        print(f"[OK] 成功编译 {FIFO_EXE}")
        
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
    output_files_to_clean = [FIFO_BATCH_OUTPUT, CF_BATCH_OUTPUT, FIFO_OUTPUT, 
                             "missed_tasks_batch.json", "missed_tasks_cf_batch.json", "missed_tasks.json"]
    for output_file in output_files_to_clean:
        if os.path.exists(output_file):
            try:
                os.remove(output_file)
                print(f"    - 已删除旧文件: {output_file}")
            except Exception as e:
                print(f"    - 警告: 无法删除 {output_file}: {e}")
    
    # 运行 fifo_batch.exe
    print(f"\n[1] 运行 {FIFO_BATCH_EXE} (FIFO 批处理调度算法)...")
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

            # 检查是否有任务丢失
            missed_file = "missed_tasks_batch.json"
            if os.path.exists(missed_file):
                missed_result_path = os.path.join(result_folder, "fifo_batch_missed_tasks.json")
                shutil.copy(missed_file, missed_result_path)
                print(f"[!] 警告: 检测到任务丢失，详情已保存: {missed_result_path}")
                
                # 读取并显示丢失任务统计
                try:
                    with open(missed_file, 'r') as f:
                        missed_data = json.load(f)
                        print(f"    - 总任务: {missed_data.get('total_tasks', 'N/A')}")
                        print(f"    - 完成任务: {missed_data.get('completed_tasks', 'N/A')}")
                        print(f"    - 丢失任务: {missed_data.get('missed_tasks', 'N/A')}")
                        print(f"    - 丢失关键任务: {missed_data.get('missed_crucial', 'N/A')}")
                except Exception as e:
                    print(f"    - 读取丢失任务详情失败: {e}")
        else:
            print(f"[!] 警告: 未找到输出文件 {FIFO_BATCH_OUTPUT}")

    except subprocess.TimeoutExpired:
        print(f"[X] {FIFO_BATCH_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {FIFO_BATCH_EXE} 时出错: {e}")
        return False

    # 运行 cf-batch.exe
    print(f"\n[2] 运行 {CF_BATCH_EXE} (CF-BATCH 调度算法)...")
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

            # 检查是否有任务丢失
            missed_file = "missed_tasks_cf_batch.json"
            if os.path.exists(missed_file):
                missed_result_path = os.path.join(result_folder, "cf_batch_missed_tasks.json")
                shutil.copy(missed_file, missed_result_path)
                print(f"[!] 警告: 检测到任务丢失，详情已保存: {missed_result_path}")
                
                # 读取并显示丢失任务统计
                try:
                    with open(missed_file, 'r') as f:
                        missed_data = json.load(f)
                        print(f"    - 总任务: {missed_data.get('total_tasks', 'N/A')}")
                        print(f"    - 完成任务: {missed_data.get('completed_tasks', 'N/A')}")
                        print(f"    - 丢失任务: {missed_data.get('missed_tasks', 'N/A')}")
                        print(f"    - 丢失关键任务: {missed_data.get('missed_crucial', 'N/A')}")
                except Exception as e:
                    print(f"    - 读取丢失任务详情失败: {e}")
        else:
            print(f"[!] 警告: 未找到输出文件 {CF_BATCH_OUTPUT}")

    except subprocess.TimeoutExpired:
        print(f"[X] {CF_BATCH_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {CF_BATCH_EXE} 时出错: {e}")
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

            # 检查是否有任务丢失
            missed_file = "missed_tasks.json"
            if os.path.exists(missed_file):
                missed_result_path = os.path.join(result_folder, "fifo_missed_tasks.json")
                shutil.copy(missed_file, missed_result_path)
                print(f"[!] 警告: 检测到任务丢失，详情已保存: {missed_result_path}")
                
                # 读取并显示丢失任务统计
                try:
                    with open(missed_file, 'r') as f:
                        missed_data = json.load(f)
                        print(f"    - 总任务: {missed_data.get('total_tasks', 'N/A')}")
                        print(f"    - 完成任务: {missed_data.get('completed_tasks', 'N/A')}")
                        print(f"    - 丢失任务: {missed_data.get('missed_tasks', 'N/A')}")
                        print(f"    - 丢失关键任务: {missed_data.get('missed_crucial', 'N/A')}")
                except Exception as e:
                    print(f"    - 读取丢失任务详情失败: {e}")
        else:
            print(f"[!] 警告: 未找到输出文件 {FIFO_OUTPUT}")

    except subprocess.TimeoutExpired:
        print(f"[X] {FIFO_EXE} 运行超时 (>60秒)")
        return False
    except Exception as e:
        print(f"[X] 运行 {FIFO_EXE} 时出错: {e}")
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
        fifo_batch_result = os.path.join(result_folder, "fifo_batch_result.json")
        fifo_batch_missed = os.path.join(result_folder, "fifo_batch_missed_tasks.json")
        cf_batch_result = os.path.join(result_folder, "cf_batch_result.json")
        cf_batch_missed = os.path.join(result_folder, "cf_batch_missed_tasks.json")
        fifo_result = os.path.join(result_folder, "fifo_result.json")
        fifo_missed = os.path.join(result_folder, "fifo_missed_tasks.json")
        
        exp_summary = {
            "experiment_id": i,
            "task_file": f"tasks_{i}.csv",
            "fifo_batch_result_exists": os.path.exists(fifo_batch_result),
            "fifo_batch_missed_exists": os.path.exists(fifo_batch_missed),
            "cf_batch_result_exists": os.path.exists(cf_batch_result),
            "cf_batch_missed_exists": os.path.exists(cf_batch_missed),
            "fifo_result_exists": os.path.exists(fifo_result),
            "fifo_missed_exists": os.path.exists(fifo_missed)
        }
        
        # 尝试读取并统计任务数量和是否丢失
        try:
            if os.path.exists(fifo_batch_result):
                with open(fifo_batch_result, 'r') as f:
                    data = json.load(f)
                    # 统计任务总数（排除deadline条目）
                    task_count = 0
                    for batch in data:
                        if "images" in batch:
                            task_count += len(batch["images"])
                    exp_summary["fifo_batch_task_count"] = task_count

                # 检查是否有丢失任务文件
                if os.path.exists(fifo_batch_missed):
                    with open(fifo_batch_missed, 'r') as mf:
                        missed_data = json.load(mf)
                        exp_summary["fifo_batch_missed_count"] = missed_data.get("missed_tasks", 0)
                        exp_summary["fifo_batch_missed_crucial"] = missed_data.get("missed_crucial", 0)
                        exp_summary["fifo_batch_status"] = f"部分失败 (丢失{missed_data.get('missed_tasks', 0)}个任务)"
                else:
                    exp_summary["fifo_batch_status"] = "OK"

            if os.path.exists(cf_batch_result):
                with open(cf_batch_result, 'r') as f:
                    data = json.load(f)
                    # 统计任务总数（排除deadline条目）
                    task_count = 0
                    for batch in data:
                        if "images" in batch:
                            task_count += len(batch["images"])
                    exp_summary["cf_batch_task_count"] = task_count

                # 检查是否有丢失任务文件
                if os.path.exists(cf_batch_missed):
                    with open(cf_batch_missed, 'r') as mf:
                        missed_data = json.load(mf)
                        exp_summary["cf_batch_missed_count"] = missed_data.get("missed_tasks", 0)
                        exp_summary["cf_batch_missed_crucial"] = missed_data.get("missed_crucial", 0)
                        exp_summary["cf_batch_status"] = f"部分失败 (丢失{missed_data.get('missed_tasks', 0)}个任务)"
                else:
                    exp_summary["cf_batch_status"] = "OK"

            if os.path.exists(fifo_result):
                with open(fifo_result, 'r') as f:
                    data = json.load(f)
                    # fifo.c 输出格式现在与批处理版本一致（批次格式）
                    task_count = 0
                    for batch in data:
                        if "images" in batch:
                            task_count += len(batch["images"])
                    exp_summary["fifo_task_count"] = task_count

                # 检查是否有丢失任务文件
                if os.path.exists(fifo_missed):
                    with open(fifo_missed, 'r') as mf:
                        missed_data = json.load(mf)
                        exp_summary["fifo_missed_count"] = missed_data.get("missed_tasks", 0)
                        exp_summary["fifo_missed_crucial"] = missed_data.get("missed_crucial", 0)
                        exp_summary["fifo_status"] = f"部分失败 (丢失{missed_data.get('missed_tasks', 0)}个任务)"
                else:
                    exp_summary["fifo_status"] = "OK"

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
    print("-" * 160)
    print(f"{'实验ID':<8} {'任务文件':<18} {'FIFO_BATCH结果':<35} {'CF_BATCH结果':<35} {'FIFO结果':<35}")
    print("-" * 160)
    
    for exp in summary["experiments"]:
        exp_id = exp["experiment_id"]
        task_file = exp["task_file"]
        fifo_batch_status = exp.get("fifo_batch_status", "NOT FOUND")
        cf_batch_status = exp.get("cf_batch_status", "NOT FOUND")
        fifo_status = exp.get("fifo_status", "NOT FOUND")
        
        # 如果有丢失任务信息，添加到状态显示中
        if exp.get("fifo_batch_missed_exists", False):
            missed_count = exp.get("fifo_batch_missed_count", 0)
            missed_crucial = exp.get("fifo_batch_missed_crucial", 0)
            fifo_batch_status += f" [丢失:{missed_count}({missed_crucial}关键)]"
        
        if exp.get("cf_batch_missed_exists", False):
            missed_count = exp.get("cf_batch_missed_count", 0)
            missed_crucial = exp.get("cf_batch_missed_crucial", 0)
            cf_batch_status += f" [丢失:{missed_count}({missed_crucial}关键)]"
        
        if exp.get("fifo_missed_exists", False):
            missed_count = exp.get("fifo_missed_count", 0)
            missed_crucial = exp.get("fifo_missed_crucial", 0)
            fifo_status += f" [丢失:{missed_count}({missed_crucial}关键)]"
        
        print(f"{exp_id:<8} {task_file:<18} {fifo_batch_status:<35} {cf_batch_status:<35} {fifo_status:<35}")
    


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

