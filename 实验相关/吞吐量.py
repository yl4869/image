import matplotlib.pyplot as plt
import numpy as np


xlabel = "Time (ms)"
ylabel = "Non-critical tasks processed"
title = "Non-critical Task Throughput"

# 横坐标：20ms 到 50ms，每 5ms 一个点
x_values = np.arange(10, 55, 5)
x_ticks = x_values.copy()

# 定义多条曲线数据（示例），键为图例标签
# 请将数组替换为真实的吞吐量数据（单位建议为 images/s），长度需与 x_values 相同
raw_series_data = {
	r"A$^2$R$^2$-Batch":      [423,1205,1952, 2399, 2568, 2642, 2671, 2677, 2677],
	"RTS2022":  [155,859,1554, 2063, 2458, 2577, 2677, 2677, 2677],
	"fifo_batch": [662,1527,1885, 2446, 2561, 2616, 2656, 2676, 2677],
	"fifo":       [473,785,955, 1206, 1453, 1584, 1773, 1954, 2036],
	"cf_batch":   [333,599,1086, 1652, 2151, 2436, 2560, 2610, 2639],
}
series_data = {
	label: [value / 200 for value in values]
	for label, values in raw_series_data.items()
}

# 校验数据长度
for label, data in series_data.items():
	assert len(data) == len(x_values), f"{label} 的数据长度与 X 轴不匹配"

# 创建图形
plt.figure(figsize=(6, 4))

# 绘制曲线
markers = ["o", "s", "^", "D", "x"]
linestyles = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
for idx, (label, data) in enumerate(series_data.items()):
	marker = markers[idx % len(markers)]
	linestyle = linestyles[idx % len(linestyles)]
	plt.plot(x_values, data, label=label, marker=marker, linestyle=linestyle)

# 坐标轴设置
plt.xlim(5, 55)
plt.xticks(x_ticks)
plt.ylim(0, max(max(vals) for vals in series_data.values()) * 1.1)

# 标签、标题、图例
plt.xlabel(xlabel)
plt.ylabel(ylabel)
plt.title(title)
plt.legend()
plt.grid(True, linestyle=":", alpha=0.7)

# 导出
plt.tight_layout()
plt.savefig("non_critical_throughput.png", dpi=300)
print("图像已保存为 'non_critical_throughput.png'")
