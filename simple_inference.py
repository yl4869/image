import torch
from torchvision import transforms
from PIL import Image
import os
import json
import time
from model_torch import EarlyExitResNet18

class SimpleInference:
    def __init__(self, model_paths, image_folder, num_classes=7):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        try:
            torch.backends.cudnn.benchmark = True
        except Exception:
            pass
        self.num_classes = num_classes
        self.image_folder = image_folder
        self.models = {}
        self.warmed_sizes = set()
        
        # 类别映射：根据训练时的文件夹顺序
        self.class_mapping = {
            0: "bench",
            1: "bicycle", 
            2: "car",
            3: "motorcycle",
            4: "person",
            5: "traffic light",
            6: "train"
        }
        
        # 加载所有模型
        for size, model_path in model_paths.items():
            if os.path.exists(model_path):
                try:
                    model = EarlyExitResNet18(num_classes=num_classes)
                    checkpoint = torch.load(model_path, map_location=self.device)
                    model.load_state_dict(checkpoint['model_state_dict'])
                    model = model.to(self.device)
                    model.eval()
                    
                    self.models[size] = model
                    print(f"[OK] 成功加载模型: {size}px")
                except Exception as e:
                    print(f"[X] 加载模型 {size}px 失败: {e}")
            else:
                print(f"[X] 模型文件不存在: {model_path}")

    def get_transform(self, target_size):
        return transforms.Compose([
            transforms.Resize((target_size, target_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def load_images_batch(self, image_ids, size):
        """批量加载并预处理图像，返回 (tensor, 有效image_id列表, 缺失image_id列表)"""
        transform = self.get_transform(size)
        images = []
        valid_ids = []
        missing_ids = []
        for image_id in image_ids:
            image_path = os.path.join(self.image_folder, f"{image_id}.jpg")
            if not os.path.exists(image_path):
                missing_ids.append(image_id)
                continue
            img = Image.open(image_path).convert('RGB')
            img = transform(img)
            images.append(img)
            valid_ids.append(image_id)
        if not images:
            return None, valid_ids, missing_ids
        return torch.stack(images).to(self.device), valid_ids, missing_ids

    def predict_batch(self, input_tensor, size):
        with torch.inference_mode():
            outputs = self.models[size](input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            _, predictions = torch.max(probabilities, dim=1)
        pred_ids = predictions.detach().cpu().tolist()
        pred_names = [self.class_mapping.get(pid, f"Unknown_Class_{pid}") for pid in pred_ids]
        return pred_ids, pred_names

    def predict_single_image(self, image_id, size):
        if size not in self.models:
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': None,
                'predicted_class_id': None,
                'error': f'模型 {size}px 未加载'
            }
        
        # 构建图片路径
        image_path = os.path.join(self.image_folder, f"{image_id}.jpg")
        
        if not os.path.exists(image_path):
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': None,
                'predicted_class_id': None,
                'error': f'图片文件不存在: {image_path}'
            }
        
        try:
            # 加载和预处理图片
            image = Image.open(image_path).convert('RGB')
            transform = self.get_transform(size)
            input_tensor = transform(image).unsqueeze(0).to(self.device)
            
            # 进行预测（使用完整4个阶段）
            with torch.no_grad():
                outputs = self.models[size](input_tensor)
                probabilities = torch.softmax(outputs, dim=1)
                confidence, prediction = torch.max(probabilities, dim=1)
                
                # 获取类别ID和对应的实际类别名称
                predicted_class_id = prediction.item()
                predicted_class = self.class_mapping.get(predicted_class_id, f"Unknown_Class_{predicted_class_id}")
            
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': predicted_class,
                'predicted_class_id': predicted_class_id
            }
            
        except Exception as e:
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': None,
                'predicted_class_id': None,
                'error': str(e)
            }

    def process_json_file(self, json_file_path):
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                batches = json.load(f)
        except FileNotFoundError:
            print(f"[X] 文件不存在: {json_file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"[X] JSON解析错误: {e}")
            return []
        
        # 解析deadline（由C端在数组末尾追加的对象 {"deadline": <float>}）
        deadline_ms = None
        if isinstance(batches, list) and len(batches) > 0 and isinstance(batches[-1], dict) and 'deadline' in batches[-1]:
            try:
                deadline_value = float(batches[-1]['deadline'])
                # C端以秒为单位，这里统一转换为毫秒
                deadline_ms = deadline_value * 1000.0
            except (TypeError, ValueError):
                deadline_ms = None
            # 从批次数组中移除deadline占位对象
            batches = batches[:-1]
        
        results = []
        cumulative_time = 0.0  # 累计时间，初始为0（毫秒）
        missed_deadline_images = []  # 记录错过截止期的图片ID
        
        for batch_idx, batch in enumerate(batches):
            size = batch.get('size')
            image_items = batch.get('images', [])
            # 兼容字符串ID或对象{ id, crucial }
            normalized_items = []
            for it in image_items:
                if isinstance(it, str):
                    normalized_items.append({'id': it, 'crucial': 0})
                elif isinstance(it, dict) and 'id' in it:
                    normalized_items.append({'id': it.get('id'), 'crucial': 1 if it.get('crucial') else 0})
            image_ids = [it['id'] for it in normalized_items]
            id_to_crucial = {it['id']: it['crucial'] for it in normalized_items}
            
            if not size or not image_ids:
                print(f"批次 {batch_idx + 1} 缺少必要信息，跳过")
                continue
            
            print(f"\n处理批次 {batch_idx + 1}: 大小={size}px, 图片数量={len(image_ids)}")
            
            # 先为缺失的图片写入错误结果
            missing_ids = []
            valid_ids = []
            for image_id in image_ids:
                image_path = os.path.join(self.image_folder, f"{image_id}.jpg")
                if not os.path.exists(image_path):
                    missing_ids.append(image_id)
                    results.append({
                        'image_id': image_id,
                        'size': size,
                        'predicted_class': None,
                        'predicted_class_id': None,
                        'error': f'图片文件不存在: {image_path}',
                        'crucial': 1 if id_to_crucial.get(image_id, 0) else 0
                    })
                    print(f"  [X] {image_id}: 图片文件不存在")
                else:
                    valid_ids.append(image_id)
            
            batch_count = 0
            if len(valid_ids) > 0:
                # 完整批次预热
                for _ in range(7):
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    warm_tensor, _, _ = self.load_images_batch(valid_ids, size)
                    if warm_tensor is not None:
                        with torch.inference_mode():
                            _ = self.models[size](warm_tensor)
                        if torch.cuda.is_available():
                            torch.cuda.synchronize()

                # 正式计时：包含批量加载+预处理+推理（忽略第1次）
                stabilize_runs = 3
                measured_times_ms = []
                pred_ids = []
                pred_names = []
                for run_idx in range(stabilize_runs):
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    batch_start_time = time.perf_counter()

                    input_tensor, _, _ = self.load_images_batch(valid_ids, size)
                    with torch.inference_mode():
                        pred_ids, pred_names = self.predict_batch(input_tensor, size)

                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    batch_end_time = time.perf_counter()
                    measured_times_ms.append((batch_end_time - batch_start_time) * 1000)

                batch_count = len(valid_ids)
                if len(measured_times_ms) > 1:
                    batch_processing_time = min(measured_times_ms[1:])
                else:
                    batch_processing_time = measured_times_ms[0]

                # 将结果写入
                for img_id, pid, pname in zip(valid_ids, pred_ids, pred_names):
                    results.append({
                        'image_id': img_id,
                        'size': size,
                        'predicted_class': pname,
                        'predicted_class_id': pid,
                        'crucial': 1 if id_to_crucial.get(img_id, 0) else 0
                    })
                    print(f"  [OK] {img_id}: {pname}")
            else:
                # 如果没有有效图片，设置时间为0
                batch_start_time = time.perf_counter()
                batch_end_time = batch_start_time
            batch_processing_time = (batch_end_time - batch_start_time) * 1000  # 转换为毫秒
            cumulative_time += batch_processing_time
            
            # 判断是否错过deadline（以批次结束时间为所有图片完成时间）
            if deadline_ms is not None and cumulative_time > deadline_ms and len(valid_ids) > 0:
                missed_deadline_images.extend(valid_ids)
            
            # 添加批次时间信息到结果中
            batch_time_info = {
                'batch_info': {
                    'batch_index': batch_idx + 1,
                    'size': size,
                    'image_count': len(image_ids),
                    'batch_processing_time_ms': round(batch_processing_time, 2),
                    'cumulative_time_ms': round(cumulative_time, 2)
                }
            }
            results.append(batch_time_info)
            
            print(f"  批次 {batch_idx + 1} 完成: 处理时间={batch_processing_time:.2f}ms, 累计时间={cumulative_time:.2f}ms")
        
        if deadline_ms is not None:
            deadline_seconds = deadline_ms / 1000.0
            results.append({
                'deadline': round(deadline_seconds, 2),
                'missed_deadline_images': missed_deadline_images
            })
        else:
            results.append({
                'deadline': None,
                'missed_deadline_images': missed_deadline_images
            })
        
        return results

    def save_results(self, results, output_file_path):
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] 预测结果已保存到: {output_file_path}")
        except Exception as e:
            print(f"[X] 保存结果到JSON文件失败: {e}")


def main():
    model_paths = {
        64: 'model/model_64.pth',
        128: 'model/model_128.pth',
        256: 'model/model_256.pth',
        512: 'model/model_512.pth'
    }
    # 图片文件夹路径
    image_folder = 'images_cropped/cropped_1'  # 图片文件夹路径
    # 从JSON文件读取批次信息并进行预测
    json_file_path = "result_list/result_1/main_result.json"  
    output_json_path = "result_list/result_1/main_time.json"  
    inference = SimpleInference(model_paths, image_folder, num_classes=7)
    # 处理所有批次
    results = inference.process_json_file(json_file_path)
    inference.save_results(results, output_json_path)
if __name__ == '__main__':
    main()
