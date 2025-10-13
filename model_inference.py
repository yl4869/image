import torch
from torchvision import transforms
from PIL import Image
import os
import json
from model_torch import EarlyExitResNet18

class MultiModelInference:
    def __init__(self, model_paths, num_classes=7):
        """
        初始化多模型推理器
        
        Args:
            model_paths (dict): 模型路径字典，格式为 {'model_name': 'path/to/model.pth'}
            num_classes (int): 类别数量
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.num_classes = num_classes
        self.models = {}
        # 加载所有模型
        for model_name, model_path in model_paths.items():
            if os.path.exists(model_path):
                try:
                    model = EarlyExitResNet18(num_classes=num_classes)
                    checkpoint = torch.load(model_path, map_location=self.device)
                    model.load_state_dict(checkpoint['model_state_dict'])
                    model = model.to(self.device)
                    model.eval()
                    
                    self.models[model_name] = model
                   
                except Exception as e:
                    print(f"✗ 加载模型 {model_name} 失败: {e}")
            else:
                print(f"✗ 模型文件不存在: {model_path}")
        

    
    def get_transform(self, target_size):
        return transforms.Compose([
            transforms.Resize((target_size, target_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def predict_batch_images(self, image_paths, model_name, target_size=512, target_stage=4):
        """
        对多张图片进行批量预测
        
        Args:
            image_paths (list): 图片路径列表
            model_name (str): 要使用的模型名称
            target_size (int): 目标图片大小
            target_stage (int): 目标阶段 (1-4)
            
        Returns:
            list: 预测结果列表
        """
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 未加载，可用模型: {list(self.models.keys())}")
        
        results = []
        transform = self.get_transform(target_size)
        
        for image_path in image_paths:
            if not os.path.exists(image_path):
                print(f"警告: 图片文件不存在: {image_path}")
                continue
                
            try:
                # 加载和预处理图片
                image = Image.open(image_path).convert('RGB')
                input_tensor = transform(image).unsqueeze(0).to(self.device)
                
                # 进行预测
                with torch.no_grad():
                    outputs = self.models[model_name](input_tensor, target_stage=target_stage)
                    probabilities = torch.softmax(outputs, dim=1)
                    confidence, prediction = torch.max(probabilities, dim=1)
                    
                    # 获取类别名称
                    predicted_class = f"Class_{prediction.item()}"
                
                results.append({
                    'image_path': image_path,
                    'predicted_class': predicted_class,
                    'predicted_class_id': prediction.item(),
                    'confidence': confidence.item(),
                    'probabilities': probabilities.cpu().numpy()[0]
                })
                
            except Exception as e:
                print(f"处理图片 {image_path} 时出错: {e}")
                results.append({
                    'image_path': image_path,
                    'error': str(e)
                })
        
        return results
    
    def print_batch_results(self, results):
        """
        Args:
            results (list): 预测结果列表
        """
        for i, result in enumerate(results):
            if 'error' in result:
                print(f"图片 {i+1}: {result['image_path']} - 处理失败: {result['error']}")
                continue
                
            print(f"图片 {i+1}: {result['image_path']}")
            print(f"  预测类别: {result['predicted_class']} (ID: {result['predicted_class_id']})")
    
    def load_batches_from_json(self, json_file_path):
        """
        从JSON文件加载批次信息
        
        Args:
            json_file_path (str): JSON文件路径
            
        Returns:
            list: 批次信息列表
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                batches = json.load(f)
            return batches
        except FileNotFoundError:
            print(f"✗ 文件不存在: {json_file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ JSON解析错误: {e}")
            return []
        except Exception as e:
            print(f"✗ 读取文件时出错: {e}")
            return []
    
    def get_model_name_by_size(self, size):
        """
        根据图片大小获取对应的模型名称
        
        Args:
            size (int): 图片大小 (64, 128, 256, 512)
            
        Returns:
            str: 模型名称
        """
        size_to_model = {
            64: 'model_64',
            128: 'model_128', 
            256: 'model_256',
            512: 'model_512'
        }
        return size_to_model.get(size, None)
    
    def predict_batches_from_json(self, json_file_path, image_base_path="", target_stage=4):
        """
        从JSON文件读取批次信息并进行预测
        
        Args:
            json_file_path (str): JSON文件路径
            image_base_path (str): 图片文件的基础路径
            target_stage (int): 目标阶段 (1-4)
            
        Returns:
            dict: 所有批次的预测结果
        """
        batches = self.load_batches_from_json(json_file_path)
        if not batches:
            return {}
        
        all_results = {}
        
        for batch_idx, batch in enumerate(batches):
            size = batch.get('size')
            image_ids = batch.get('images', [])
            
            if not size or not image_ids:
                print(f"批次 {batch_idx + 1} 缺少必要信息，跳过")
                continue
            
            # 获取对应的模型名称
            model_name = self.get_model_name_by_size(size)
            if not model_name:
                print(f"批次 {batch_idx + 1}: 不支持的大小 {size}，跳过")
                continue
            
            if model_name not in self.models:
                print(f"批次 {batch_idx + 1}: 模型 {model_name} 未加载，跳过")
                continue
            
            # 构建图片路径
            image_paths = []
            for image_id in image_ids:
                if image_base_path:
                    # 如果提供了基础路径，尝试构建完整路径
                    image_path = os.path.join(image_base_path, f"{image_id}.jpg")
                else:
                    # 否则直接使用image_id作为路径
                    image_path = f"{image_id}.jpg"
                image_paths.append(image_path)
            
            print(f"\n处理批次 {batch_idx + 1}: 大小={size}, 模型={model_name}, 图片数量={len(image_paths)}")
            
            # 进行预测
            try:
                results = self.predict_batch_images(image_paths, model_name, size, target_stage)
                all_results[f"batch_{batch_idx + 1}"] = {
                    'batch_id': batch_idx + 1,
                    'size': size,
                    'model_name': model_name,
                    'target_stage': target_stage,
                    'image_count': len(image_paths),
                    'image_ids': image_ids,
                    'image_paths': image_paths,
                    'predictions': results,
                    'status': 'success'
                }
                self.print_batch_results(results)
            except Exception as e:
                print(f"批次 {batch_idx + 1} 预测失败: {e}")
                all_results[f"batch_{batch_idx + 1}"] = {
                    'batch_id': batch_idx + 1,
                    'size': size,
                    'model_name': model_name,
                    'target_stage': target_stage,
                    'image_count': len(image_paths),
                    'image_ids': image_ids,
                    'image_paths': image_paths,
                    'error': str(e),
                    'status': 'failed'
                }
        
        return all_results
    
    def save_results_to_json(self, results, output_file_path, summary_info=None):
        """
        将预测结果保存到JSON文件
        
        Args:
            results (dict): 预测结果字典
            output_file_path (str): 输出JSON文件路径
            summary_info (dict): 汇总信息
        """
        try:
            # 创建完整的输出结构
            output_data = {
                "prediction_summary": summary_info or {},
                "batches": results,
                "timestamp": self.get_current_timestamp()
            }
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"✓ 预测结果已保存到: {output_file_path}")
        except Exception as e:
            print(f"✗ 保存结果到JSON文件失败: {e}")
    
    def get_current_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
         

def main():
    # 定义要加载的模型路径
    model_paths = {
        'model_64': 'model/model_64_epoch14.pth',
        'model_128': 'model/model_128_epoch9.pth', 
        'model_256': 'model/model_256_epoch11.pth',
        'model_512': 'model/model_512_epoch13.pth'
    }
    
    # 初始化多模型推理器
    inference = MultiModelInference(model_paths, num_classes=7)
    
    if not inference.models:
        print("没有成功加载任何模型，退出程序")
        return
    
    # 从JSON文件读取批次信息并进行预测
    json_file_path = "output.json"  # 输入JSON文件路径
    output_json_path = "prediction_results.json"  # 输出JSON文件路径
    image_base_path = ""  # 图片基础路径，如果为空则直接使用image_id作为路径
    target_stage = 3  # 目标阶段
    
    print(f"\n从JSON文件读取批次信息: {json_file_path}")
    print(f"图片基础路径: {image_base_path if image_base_path else '使用image_id作为路径'}")
    print(f"目标阶段: {target_stage}")
    print(f"结果将保存到: {output_json_path}")
    
    # 从JSON文件预测所有批次
    try:
        all_results = inference.predict_batches_from_json(json_file_path, image_base_path, target_stage)
        
        if all_results:
            print(f"\n=== 预测完成 ===")
            print(f"总共处理了 {len(all_results)} 个批次")
            
            # 统计信息
            total_images = 0
            successful_batches = 0
            failed_batches = 0
            total_successful_images = 0
            
            for batch_name, batch_info in all_results.items():
                if batch_info.get('status') == 'success':
                    image_count = batch_info.get('image_count', 0)
                    total_images += image_count
                    total_successful_images += image_count
                    successful_batches += 1
                    print(f"{batch_name}: {batch_info['size']}px, {image_count}张图片 - 成功")
                else:
                    failed_batches += 1
                    print(f"{batch_name}: {batch_info.get('size', 'N/A')}px - 处理失败: {batch_info.get('error', '未知错误')}")
            
            # 创建汇总信息
            summary_info = {
                "total_batches": len(all_results),
                "successful_batches": successful_batches,
                "failed_batches": failed_batches,
                "total_images": total_images,
                "successful_images": total_successful_images,
                "target_stage": target_stage,
                "input_json_file": json_file_path
            }
            
            # 保存结果到JSON文件
            inference.save_results_to_json(all_results, output_json_path, summary_info)
            
        else:
            # 即使没有结果，也保存一个空的JSON文件
            empty_results = {}
            empty_summary = {
                "total_batches": 0,
                "successful_batches": 0,
                "failed_batches": 0,
                "total_images": 0,
                "successful_images": 0,
                "message": "没有成功处理任何批次",
                "input_json_file": json_file_path
            }
            inference.save_results_to_json(empty_results, output_json_path, empty_summary)
            
    except Exception as e:
        print(f"JSON预测失败: {e}")
        # 保存错误信息到JSON文件
        error_results = {}
        error_summary = {
            "error": str(e),
            "message": "预测过程中发生错误",
            "input_json_file": json_file_path
        }
        inference.save_results_to_json(error_results, output_json_path, error_summary)

if __name__ == '__main__':
    main()
