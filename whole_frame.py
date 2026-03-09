import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import numpy as np
import time
import os

# 从你的文件导入模型类
from model_torch import EarlyExitResNet18


class LetterboxTransform:
    """保持纵横比的缩放填充 (Letterbox)"""

    def __init__(self, target_size, fill_color=(114, 114, 114)):
        self.target_size = target_size if isinstance(target_size, tuple) else (target_size, target_size)
        self.fill_color = fill_color

    def __call__(self, img):
        width, height = img.size
        target_width, target_height = self.target_size
        scale = min(target_width / width, target_height / height)
        new_width, new_height = int(width * scale), int(height * scale)
        img = img.resize((new_width, new_height), Image.BILINEAR)
        new_img = Image.new('RGB', (target_width, target_height), self.fill_color)
        new_img.paste(img, ((target_width - new_width) // 2, (target_height - new_height) // 2))
        return new_img


class ProfessionalPredictor:
    def __init__(self, model_path, num_classes=78, target_size=224):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.target_size = target_size

        # 初始化并加载模型
        self.model = EarlyExitResNet18(num_classes=num_classes)
        # 注意：这里假设你的权重文件是 state_dict。如果是整个模型，请用 torch.load(model_path)
        state_dict = torch.load(model_path, map_location=self.device)
        # 兼容处理：检查是否是全字典还是仅 state_dict
        if 'model_state_dict' in state_dict:
            self.model.load_state_dict(state_dict['model_state_dict'])
        else:
            self.model.load_state_dict(state_dict)

        self.model.to(self.device)
        self.model.eval()

        # 统一预处理流程 [对应区别1]
        self.transform = transforms.Compose([
            LetterboxTransform(target_size=self.target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict_with_stats(self, image_path, num_repeats=20):
        print(f"正在对图片 {os.path.basename(image_path)} 进行 {num_repeats} 次性能测试...")

        # GPU 预热
        img_temp = Image.open(image_path).convert('RGB')
        input_temp = self.transform(img_temp).unsqueeze(0).to(self.device)
        with torch.no_grad():
            for _ in range(5):
                _ = self.model(input_temp)

        total_times = []

        for i in range(num_repeats):
            # 记录起始点并强制同步 [对应区别2]
            if self.device.type == 'cuda':
                torch.cuda.synchronize()
            start_time = time.perf_counter()

            # 1. 预处理 (包含在总时间内) [对应区别1]
            img = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(img).unsqueeze(0).to(self.device)

            # 2. 推理 (全过程推理，不设 target_stage)
            with torch.no_grad():
                output = self.model(input_tensor)

            # 记录结束点并强制同步 [对应区别2]
            if self.device.type == 'cuda':
                torch.cuda.synchronize()
            end_time = time.perf_counter()

            total_times.append((end_time - start_time) * 1000)  # 毫秒

        # 结果统计 [对应区别3]
        mean_time = np.mean(total_times)
        std_time = np.std(total_times)

        # 获取最后一次预测的结果
        prob = F.softmax(output, dim=1)
        conf, pred_class = torch.max(prob, 1)

        print("-" * 50)
        print(f"预测结果: 类别 ID {pred_class.item()} (置信度 {conf.item():.4f})")
        print(f"全流程耗时统计 (预处理 + 推理):")
        print(f"  平均耗时: {mean_time:.2f} ms")
        print(f"  标准差:   {std_time:.2f} ms")
        print(f"  最短耗时: {np.min(total_times):.2f} ms")
        print("-" * 50)


if __name__ == "__main__":
    # 配置
    # 使用基于脚本位置的路径，确保从任何目录运行都能找到文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    WEIGHTS = os.path.join(script_dir, "model", "model_128.pth")
    IMAGE = os.path.join(script_dir, "temp.jpg")
    CLASSES = 7  # 根据你的训练集修改
    SIZE = 1980  # 根据你的训练集修改

    predictor = ProfessionalPredictor(model_path=WEIGHTS, num_classes=CLASSES, target_size=SIZE)
    predictor.predict_with_stats(IMAGE, num_repeats=20)