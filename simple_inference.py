import torch
from torchvision import transforms
from PIL import Image
import os
import json
from model_torch import EarlyExitResNet18

class SimpleInference:
    def __init__(self, model_paths, image_folder, num_classes=7):
        """
        初始化简化推理器
        
        Args:
            model_paths (dict): 模型路径字典，格式为 {size: 'path/to/model.pth'}
            image_folder (str): 图片文件夹路径
            num_classes (int): 类别数量
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.num_classes = num_classes
        self.image_folder = image_folder
        self.models = {}
        
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
                    print(f"✓ 成功加载模型: {size}px")
                except Exception as e:
                    print(f"✗ 加载模型 {size}px 失败: {e}")
            else:
                print(f"✗ 模型文件不存在: {model_path}")

    def get_transform(self, target_size):
        """获取图片预处理变换"""
        return transforms.Compose([
            transforms.Resize((target_size, target_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict_single_image(self, image_id, size):
        """
        对单张图片进行预测（使用完整4个阶段）
        
        Args:
            image_id (str): 图片ID
            size (int): 图片大小
            
        Returns:
            dict: 预测结果
        """
        if size not in self.models:
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': None,
                'error': f'模型 {size}px 未加载'
            }
        
        # 构建图片路径
        image_path = os.path.join(self.image_folder, f"{image_id}.jpg")
        
        if not os.path.exists(image_path):
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': None,
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
                
                # 获取类别名称
                predicted_class = f"Class_{prediction.item()}"
            
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': predicted_class
            }
            
        except Exception as e:
            return {
                'image_id': image_id,
                'size': size,
                'predicted_class': None,
                'error': str(e)
            }

    def process_json_file(self, json_file_path):
        """
        处理JSON文件中的所有批次，按顺序进行推理（使用完整4个阶段）
        
        Args:
            json_file_path (str): JSON文件路径
            
        Returns:
            list: 按顺序的预测结果列表
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                batches = json.load(f)
        except FileNotFoundError:
            print(f"✗ 文件不存在: {json_file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"✗ JSON解析错误: {e}")
            return []
        
        results = []
        
        for batch_idx, batch in enumerate(batches):
            size = batch.get('size')
            image_ids = batch.get('images', [])
            
            if not size or not image_ids:
                print(f"批次 {batch_idx + 1} 缺少必要信息，跳过")
                continue
            
            print(f"\n处理批次 {batch_idx + 1}: 大小={size}px, 图片数量={len(image_ids)}")
            
            # 按顺序处理批次中的每张图片
            for image_id in image_ids:
                result = self.predict_single_image(image_id, size)
                results.append(result)
                
                if 'error' in result:
                    print(f"  ✗ {image_id}: {result['error']}")
                else:
                    print(f"  ✓ {image_id}: {result['predicted_class']}")
        
        return results

    def save_results(self, results, output_file_path):
        """
        将预测结果保存到JSON文件（简化格式）
        
        Args:
            results (list): 预测结果列表
            output_file_path (str): 输出JSON文件路径
        """
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 预测结果已保存到: {output_file_path}")
        except Exception as e:
            print(f"✗ 保存结果到JSON文件失败: {e}")


def main():
    # 定义模型路径（按图片大小映射）
    model_paths = {
        64: 'model/model_64.pth',
        128: 'model/model_128.pth',
        256: 'model/model_256.pth',
        512: 'model/model_512.pth'
    }
    
    # 图片文件夹路径（请根据实际情况修改）
    image_folder = "images"  # 修改为您的图片文件夹路径
    
    # 初始化推理器
    inference = SimpleInference(model_paths, image_folder, num_classes=7)
    
    if not inference.models:
        print("没有成功加载任何模型，退出程序")
        return
    
    # 从JSON文件读取批次信息并进行预测
    json_file_path = "output.json"  # 输入JSON文件路径
    output_json_path = "prediction_results.json"  # 输出JSON文件路径
    
    print(f"\n开始处理...")
    print(f"输入JSON文件: {json_file_path}")
    print(f"图片文件夹: {image_folder}")
    print(f"推理模式: 完整4个阶段")
    print(f"结果将保存到: {output_json_path}")
    
    # 处理所有批次
    results = inference.process_json_file(json_file_path)
    
    if results:
        # 统计信息
        total_images = len(results)
        successful_images = sum(1 for r in results if 'error' not in r)
        failed_images = total_images - successful_images
        
        print(f"\n=== 处理完成 ===")
        print(f"总图片数: {total_images}")
        print(f"成功处理: {successful_images}")
        print(f"处理失败: {failed_images}")
        
        # 保存结果
        inference.save_results(results, output_json_path)
    else:
        print("没有处理任何图片")


if __name__ == '__main__':
    main()
