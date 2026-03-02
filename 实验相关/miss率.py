import matplotlib.pyplot as plt
import numpy as np


xlabel = "Time(ms)"
ylabel = "deadline miss rate(%)"
title = "High-criticality deadline miss rate"


# 2. 定义数据
# --- 请在这里替换为您自己的数据 ---
# 横坐标 (X-axis): 20ms 到 50ms, 步长 5ms
x_values = np.arange(10, 55, 5)
x_ticks = np.arange(10, 55, 5)

# 使用多个系列数据（示例），键为图例标签
# 请将数组替换为真实的 deadline miss rate (%) 数据，长度需与 x_values 相同
series_data = {
	r"A$^2$R$^2$-Batch":      [15.61,0.96,0, 0, 0, 0, 0, 0, 0],
	"RTS2022":  [93.95,62.28,36.67,18.86, 7.19, 3.33, 0, 0, 0],
	"fifo_batch": [77.63,59.12,45, 27.11, 15.96, 7.98, 3.51, 1.23, 0.79],
	"fifo":       [89.21,82.28,79.65, 72.02, 63.42, 59.04, 51.32, 44.74, 39.04],
	"cf_batch":   [53.86,31.84,12.98, 4.91, 2.37, 0, 0, 0, 0],
}

# 检查所有曲线的数据长度
for label, data in series_data.items():
	assert len(data) == len(x_values), f"{label} 的数据长度与 X 轴不匹配"

# 3. 创建图形
# 设置图像大小，使其更适合论文（例如，6x4英寸）
plt.figure(figsize=(6, 4))

# 绘制多条曲线并区分标记/线型，方便黑白打印
markers = ["o", "s", "^", "D", "x"]
linestyles = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
for idx, (label, data) in enumerate(series_data.items()):
	marker = markers[idx % len(markers)]
	linestyle = linestyles[idx % len(linestyles)]
	plt.plot(x_values, data, label=label, marker=marker, linestyle=linestyle)

# 4. 设置坐标轴（严格按照您的要求）
# Y轴 (纵坐标): 精度 50 到 100
plt.ylim(-5, 105)

# X轴 (横坐标): 20 到 50
plt.xlim(5, 55)
# 设置更稀疏的 X 轴刻度，避免拥挤
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
plt.savefig("average_deadline_miss.png", dpi=300)  # 保存为高分辨率PNG，适合论文

print("图像已保存为 'average_deadline_miss.png'")