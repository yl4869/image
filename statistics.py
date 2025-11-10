import json
import os
from pathlib import Path
from typing import Dict, Set, Tuple, List


DEFAULT_DDL = 25 
DEFAULT_OUT = ""  



def load_task_catalog(task_dir: Path) -> Tuple[Dict[str, int], Dict[str, int]]:

	image_id_to_crucial: Dict[str, int] = {}
	image_id_to_is_non_critical: Dict[str, int] = {}

	for csv_path in sorted(task_dir.glob("*.csv")):
		try:
			with csv_path.open("r", encoding="utf-8") as f:
				header = f.readline()
				for line in f:
					line = line.strip()
					if not line:
						continue
					parts = [p.strip() for p in line.split(",")]
					if len(parts) < 5:
						continue
					_, _, task_id, crucial_str, category = parts[:5]
					image_id = f"{task_id}_{category}"
					crucial = 1 if crucial_str == "1" else 0
					image_id_to_crucial[image_id] = crucial
					image_id_to_is_non_critical[image_id] = 1 - crucial
		except Exception:
			continue

	return image_id_to_crucial, image_id_to_is_non_critical


def load_single_task_file(task_csv: Path) -> Dict[str, int]:
	image_id_to_crucial: Dict[str, int] = {}
	with task_csv.open("r", encoding="utf-8") as f:
		_ = f.readline()  # header
		for line in f:
			line = line.strip()
			if not line:
				continue
			parts = [p.strip() for p in line.split(",")]
			if len(parts) < 5:
				continue
			_, _, task_id, crucial_str, category = parts[:5]
			image_id = f"{task_id}_{category}"
			crucial = 1 if crucial_str == "1" else 0
			image_id_to_crucial[image_id] = crucial
	return image_id_to_crucial


def parse_main_time(main_time_path: Path) -> Tuple[Set[str], Set[str], Dict[str, str]]:
	processed_critical: Set[str] = set()
	processed_non_critical: Set[str] = set()
	predictions: Dict[str, str] = {}

	try:
		data = json.loads(main_time_path.read_text(encoding="utf-8"))
		if isinstance(data, list):
			for item in data:
				if not isinstance(item, dict):
					continue
				if "image_id" not in item:
		
					continue
				image_id = item.get("image_id")
				crucial = int(item.get("crucial", 0))
				if crucial == 1:
					processed_critical.add(image_id)
				else:
					processed_non_critical.add(image_id)
				if "predicted_class" in item:
					predictions[image_id] = item["predicted_class"]
	except Exception:
	
		pass

	return processed_critical, processed_non_critical, predictions


def parse_resizing_time(resizing_time_path: Path) -> Tuple[bool, Set[str], Set[str], Dict[str, str]]:
	processed_critical: Set[str] = set()
	processed_non_critical: Set[str] = set()
	predictions: Dict[str, str] = {}

	try:
		raw = resizing_time_path.read_text(encoding="utf-8").strip()
		if raw == "-1":
			return True, processed_critical, processed_non_critical, predictions
		data = json.loads(raw)
		if isinstance(data, list):
			is_flat = any(isinstance(item, dict) and "image_id" in item for item in data)
			if is_flat:
				for item in data:
					if not isinstance(item, dict) or "image_id" not in item:
						continue
					image_id = item.get("image_id")
					crucial = int(item.get("crucial", 0))
					predicted_class = item.get("predicted_class")
					if not image_id:
						continue
					if isinstance(predicted_class, str):
						predictions[image_id] = predicted_class
					if crucial == 1:
						processed_critical.add(image_id)
					else:
						processed_non_critical.add(image_id)
			else:
				for group in data:
					if not isinstance(group, dict):
						continue
					images: List[Dict] = group.get("images") or []
					for img in images:
						image_id = img.get("id")
						crucial = int(img.get("crucial", 0))
						predicted_class = img.get("predicted_class")
						if not image_id:
							continue
						if isinstance(predicted_class, str):
							predictions[image_id] = predicted_class
						if crucial == 1:
							processed_critical.add(image_id)
						else:
							processed_non_critical.add(image_id)
	except Exception:
		pass

	return False, processed_critical, processed_non_critical, predictions


def compute_metrics_for_ddl(ddl: int, workspace: Path) -> Tuple[str, Dict[str, float]]:
	task_dir = workspace / f"task_files_ddl{ddl}"
	result_dir = workspace / f"result_list_ddl{ddl}"

	if not task_dir.exists() or not result_dir.exists():
		raise FileNotFoundError(f"Required directories not found for ddl{ddl}")


	total_critical = 0
	total_main_processed_critical: int = 0
	total_resize_processed_critical: int = 0
	total_main_non_critical: int = 0
	total_resize_non_critical: int = 0


	main_correct = 0
	main_total_for_acc = 0
	resize_correct = 0
	resize_total_for_acc = 0

	for sub in sorted(result_dir.iterdir()):
		if not sub.is_dir():
			continue
		main_time = sub / "main_time.json"
		resizing_time = sub / "resizing_time.json"


		name = sub.name  
		if not name.startswith("result_"):
			continue
		idx = name.replace("result_", "")
		task_csv = task_dir / f"tasks_{idx}.csv"
		if not task_csv.exists():
			continue
		task_map = load_single_task_file(task_csv)  # image_id -> crucial
		folder_total_critical = sum(1 for v in task_map.values() if v == 1)
		total_critical += folder_total_critical

		# main_time
		if main_time.exists():
			c_crit, c_non, preds = parse_main_time(main_time)
			c_crit = {i for i in c_crit if i in task_map and task_map[i] == 1}
			c_non = {i for i in c_non if i in task_map and task_map[i] == 0}
			total_main_processed_critical += len(c_crit)
			total_main_non_critical += len(c_non)
			for iid in c_crit:
				if iid in preds:
					main_total_for_acc += 1
					true_cls = iid.split("_")[-1]
					if preds[iid] == true_cls:
						main_correct += 1

		# resizing_time with special -1 handling
		if resizing_time.exists():
			invalid, r_crit, r_non, r_preds = parse_resizing_time(resizing_time)
			if not invalid:
				# Filter to tasks that belong to this folder
				r_crit = {i for i in r_crit if i in task_map and task_map[i] == 1}
				r_non = {i for i in r_non if i in task_map and task_map[i] == 0}
				total_resize_processed_critical += len(r_crit)
				total_resize_non_critical += len(r_non)
				# accuracy for this folder
				for iid in r_crit:
					if iid in r_preds:
						resize_total_for_acc += 1
						true_cls = iid.split("_")[-1]
						if r_preds[iid] == true_cls:
							resize_correct += 1
			# if invalid (-1), treat as all missed: do not add any processed ids

	def miss_rate(processed_critical_count: int) -> float:
		if total_critical == 0:
			return 0.0
		return 1.0 - (processed_critical_count / total_critical)

	main_miss_rate = miss_rate(total_main_processed_critical)
	resize_miss_rate = miss_rate(total_resize_processed_critical)

	# 3) Accuracy on processed critical (only where we have predictions)
	def true_class_from_image_id(image_id: str) -> str:
		# image_id format is like '64_19_car' → true class is the last part after the final underscore
		return image_id.split("_")[-1]

	def accuracy_ratio(correct: int, total_for_acc: int) -> float:
		if total_for_acc == 0:
			return 0.0
		return correct / total_for_acc

	main_critical_accuracy = accuracy_ratio(main_correct, main_total_for_acc)
	resize_critical_accuracy = accuracy_ratio(resize_correct, resize_total_for_acc)

	# Build Markdown content
	lines: List[str] = []
	lines.append(f"# DDL{ddl} 结果统计（main 与 resizing 算法对比）")
	lines.append("")
	lines.append("仅统计 main_time.json 与 resizing_time.json；若某任务的 resizing_time.json 为 -1，则视为全部错失。")
	lines.append("准确率按已处理的关键任务统计：从时间文件条目读取 predicted_class 与图片名真实类别对比。")
	lines.append("")
	lines.append("## 1) 关键任务总数（来自 task_files_ddl）")
	lines.append(f"- DDL{ddl} 关键任务总数: {total_critical}")
	lines.append("")
	lines.append("## 2) 关键任务错失率（已处理关键任务/总关键任务）")
	lines.append(f"- main 错失率: {main_miss_rate:.4f}  （已处理关键任务数: {total_main_processed_critical} / 总关键任务数: {total_critical}）")
	lines.append(f"- resizing 错失率: {resize_miss_rate:.4f}  （已处理关键任务数: {total_resize_processed_critical} / 总关键任务数: {total_critical}）")
	lines.append("")
	lines.append("## 3) 关键任务准确率（仅统计已处理且有预测记录的关键任务）")
	lines.append(f"- main 准确率: {main_critical_accuracy:.4f}")
	lines.append(f"- resizing 准确率: {resize_critical_accuracy:.4f}")
	lines.append("")
	lines.append("## 4) 非关键任务处理量（条目数去重）")
	lines.append(f"- main 非关键处理量: {total_main_non_critical}")
	lines.append(f"- resizing 非关键处理量: {total_resize_non_critical}")
	lines.append("")

	md = "\n".join(lines)
	metrics = {
		"total_critical": float(total_critical),
		"main_miss_rate": main_miss_rate,
		"resize_miss_rate": resize_miss_rate,
		"main_critical_accuracy": main_critical_accuracy,
		"resize_critical_accuracy": resize_critical_accuracy,
		"main_non_critical_throughput": float(total_main_non_critical),
		"resize_non_critical_throughput": float(total_resize_non_critical),
	}
	return md, metrics


def main():
	workspace = Path(".")
	ddl = DEFAULT_DDL
	out_name = DEFAULT_OUT or f"ddl{ddl}_metrics.md"

	md, _ = compute_metrics_for_ddl(ddl, workspace)

	out_path = workspace / out_name
	out_path.write_text(md, encoding="utf-8")
	print(f"Wrote {out_path}")


if __name__ == "__main__":
	main()

