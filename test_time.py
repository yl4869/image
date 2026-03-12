import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import numpy as np
import time
import os
from model_torch import EarlyExitResNet18  # 假设你的模型保存在model_torch.py中


class LetterboxTransform:
    """实现letterbox变换的类"""

    def __init__(self, target_size, fill_color=(114, 114, 114)):
        self.target_size = target_size if isinstance(target_size, tuple) else (target_size, target_size)
        self.fill_color = fill_color

    def __call__(self, img):
        # 计算缩放比例
        width, height = img.size
        target_width, target_height = self.target_size

        # 计算缩放比例和填充
        scale = min(target_width / width, target_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        # 缩放图像
        img = img.resize((new_width, new_height), Image.BILINEAR)

        # 创建新图像并填充
        new_img = Image.new('RGB', (target_width, target_height), self.fill_color)
        new_img.paste(img, ((target_width - new_width) // 2, (target_height - new_height) // 2))

        return new_img


class ImagePredictor:
    def __init__(self, model_path, num_classes=2, target_size=32, device='cuda', force_target_size=False):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')
        
        # 加载检查点
        checkpoint = torch.load(model_path, map_location=self.device)
        
        # 从检查点获取配置
        if force_target_size:
            # 强制使用用户指定的target_size
            self.target_size = target_size
            print(f"强制使用指定的目标尺寸: {self.target_size}x{self.target_size}")
        else:
            # 使用检查点中保存的image_size
            self.target_size = checkpoint.get('image_size', target_size)
            print(f"使用检查点中的目标尺寸: {self.target_size}x{self.target_size}")
        
        self.num_classes = len(checkpoint.get('class_names', num_classes))
        
        # 初始化模型
        self.model = EarlyExitResNet18(num_classes=self.num_classes).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()

        # 图像预处理
        self.transform = transforms.Compose([
            LetterboxTransform(target_size=(self.target_size, self.target_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def load_images(self, image_paths):
        """加载并预处理一批图像"""
        images = []
        for img_path in image_paths:
            img = Image.open(img_path).convert('RGB')
            img = self.transform(img)
            images.append(img)
        return torch.stack(images).to(self.device)

    def predict_batch(self, image_tensor):
        """对一批图像进行预测"""
        with torch.no_grad():
            outputs = self.model.forward_train(image_tensor)
            # 获取每个exit的预测结果
            all_preds = [torch.argmax(output, dim=1).cpu().numpy() for output in outputs]
            # 获取最后一个exit的预测概率
            probs = torch.softmax(outputs[-1], dim=1).cpu().numpy()
        return all_preds, probs


    def estimate_batch_processing_time(self, image_paths, target_size, batch_sizes=[1, 5, 10, 20, 30, 50], num_repeats=5):
        """预估不同batch_size下的总处理时间（预处理+推理）"""
        print(f"开始batch_size处理时间预估实验 - 目标尺寸: {target_size}x{target_size}")

        # 创建predictor实例，强制使用指定尺寸
        predictor = ImagePredictor(
            model_path='model/model_128_epoch9.pth',
            num_classes=7,
            target_size=target_size,
            force_target_size=True
        )

        results = {}
        
        for batch_size in batch_sizes:
            if batch_size > len(image_paths):
                print(f"跳过batch_size={batch_size}，图片数量不足")
                continue
                
            print(f"测试batch_size: {batch_size}...")
            
            # 选择测试图片
            test_images = image_paths[:batch_size]
            
            # GPU预热
            print("  GPU预热中...")
            image_tensor = predictor.load_images(test_images)
            with torch.no_grad():
                for _ in range(10):  # 预热10次
                    _ = predictor.predict_batch(image_tensor)
            torch.cuda.synchronize()
            print("  GPU预热完成")
            
            # 测量总处理时间（预处理+推理）
            total_times = []
            
            for repeat in range(num_repeats + 1):  # 多运行一次用于预热
                torch.cuda.synchronize()
                start_time = time.perf_counter()
                
                # 预处理
                image_tensor = predictor.load_images(test_images)
                
                # 推理
                with torch.no_grad():
                    all_preds, probs = predictor.predict_batch(image_tensor)
                torch.cuda.synchronize()
                
                total_time = time.perf_counter() - start_time
                
                # 忽略第一次运行（预热）
                if repeat > 0:
                    total_times.append(total_time * 1000)  # 转换为毫秒
            
            # 计算统计值
            results[batch_size] = {
                'mean': np.mean(total_times),
                'std': np.std(total_times),
                'min': np.min(total_times),
                'max': np.max(total_times)
            }
            
            print(f"  总时间: {np.mean(total_times):.2f} ± {np.std(total_times):.2f} ms")
        
        # 输出简洁的结果表格
        print(f"\n{'=' * 50}")
        print("Batch Size处理时间结果")
        print(f"{'=' * 50}")
        print(f"{'Batch Size':^12}{'总时间(ms)':^15}{'标准差(ms)':^15}")
        print("-" * 50)
        
        for batch_size in batch_sizes:
            if batch_size not in results:
                continue
                
            result = results[batch_size]
            print(f"{batch_size:^12}{result['mean']:^15.2f}{result['std']:^15.2f}")
        
        return results


if __name__ == '__main__':
    # 配置参数
    MODEL_PATH = 'model/model_128_epoch9.pth'  # 你的模型路径
    IMAGE_DIR = "E:/BaiduNetdiskDownload/whole_coco/train/car"  # 包含测试图片的目录
    NUM_CLASSES = 7  # 你的分类类别数
    TARGET_SIZE = 64  # 输入尺寸
    BATCH_SIZE = 20  # 批处理图片数量

    # 获取测试图片路径
    image_extensions = ('.jpg', '.jpeg', '.png')
    test_images = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
                   if f.lower().endswith(image_extensions)]

    if not test_images:
        print("未找到测试图片。")
    else:
        print(f"找到 {len(test_images)} 张测试图片")
        
        # 创建predictor实例
        predictor = ImagePredictor(
            model_path=MODEL_PATH,
            num_classes=NUM_CLASSES,
            target_size=TARGET_SIZE,
            force_target_size=True  # 强制使用指定的target_size
        )
        
        # 运行batch_size处理时间预估实验
        batch_results = predictor.estimate_batch_processing_time(
            image_paths=test_images,
            target_size=TARGET_SIZE,
            batch_sizes=[1, 3, 5, 7, 9, 11],  # 可以修改这些batch_size
            num_repeats=20  # 可以修改重复次数
        )
        
        print(f"\n{'=' * 80}")
        print("实验完成！")
        print("你可以根据上述结果预估不同batch_size下的处理时间。")
        print(f"{'=' * 80}")
