import matplotlib.pyplot as plt
import numpy as np


xlabel = "Time(ms)"
ylabel = "Accuracy(%)"
title = "High-criticality Average Accuracy"


# 2. 定义数据
# --- 请在这里替换为您自己的数据 ---
# 横坐标 (X-axis): 20ms 到 50ms, 步长 5ms
x_values = np.arange(10, 55, 5)
x_ticks = x_values.copy()
# 定义多条曲线数据（示例值），键为图例标签
# 请用真实的 accuracy (%) 数据替换，长度需与 x_values 相同
series_data = {
	r"A$^2$R$^2$-Batch":      [59.39,70.09,71.84, 72.46, 72.63, 73.25, 73.25, 73.25, 73.33],
	"RTS2022":  [4.3,27.19,46.58, 59.21, 67.81, 70.88, 73.6, 73.25, 73.42],
	"fifo_batch": [17.54,29.74,39.21, 50.79, 60.61, 67.02, 70.44, 72.37, 72.81],
	"fifo":       [6.93,11.67,13.6, 18.95, 24.65, 28.16, 33.68, 38.33, 42.46],
	"cf_batch":   [34.91,50.79,63.77, 70, 71.75, 73.6, 73.6, 73.6, 73.6],
}

# 校验数据长度
for label, data in series_data.items():
	assert len(data) == len(x_values), f"{label} 的数据长度与 X 轴不匹配"

# 3. 创建图形
# 设置图像大小，使其更适合论文（例如，6x4英寸）
plt.figure(figsize=(6, 4))

# 绘制多条曲线并为每条曲线设置不同标记/线型
markers = ["o", "s", "^", "D", "x"]
linestyles = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
for idx, (label, data) in enumerate(series_data.items()):
	marker = markers[idx % len(markers)]
	linestyle = linestyles[idx % len(linestyles)]
	plt.plot(x_values, data, label=label, marker=marker, linestyle=linestyle)

# 4. 设置坐标轴（严格按照您的要求）
# Y轴 (纵坐标): 精度 50 到 100
plt.ylim(-5, 85)

# X轴 (横坐标): 20 到 50
plt.xlim(5, 55)
# 设置 X 轴刻度，20/25/30/35/40/45/50 全部显示
plt.xticks(x_ticks)

# 5. 添加标签和标题
plt.xlabel(xlabel)
plt.ylabel(ylabel)
plt.title(title)

# s 6. 添加图例和网格
plt.legend()  # 显示图例 (Label 'A' 和 'B')
plt.grid(True, linestyle=":", alpha=0.7)  # 添加辅助网格线

# 7. 优化布局并保存图像
plt.tight_layout()  # 自动调整布局，防止标签重叠
plt.savefig("paper_line_plot.png", dpi=300)  # 保存为高分辨率PNG，适合论文

print("图像已保存为 'paper_line_plot.png'")