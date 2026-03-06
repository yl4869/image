## 项目结构

```
image/
├── 调度算法实现 (C)
│   ├── main.c              # 基础调度器实现
│   ├── fifo.c              # FIFO 调度算法
│   ├── fifo_batch.c        # FIFO 批处理调度算法
│   ├── cf-batch.c          # 分类感知批处理调度算法
│   ├── resizing.c          # 图像缩放调度算法
│
├── 深度学习模块 (Python)
│   ├── model_torch.py      # Early-Exit ResNet18 模型定义
│   ├── simple_inference.py # 图像推理引擎（单次推理任务）
│   └── model/              # 训练好的模型权重
│
├── 实验与评估
│   ├── experiment.py       # 实验主程序
│   ├── make_csv.py         # 生成任务 CSV 文件
│   └── 实验相关/
│       ├── 吞吐量.py       # 吞吐量可视化
│       ├── 准确率.py       # 准确率分析
│       └── miss率.py       # 截止期miss率分析
│
├── 结果处理
│   ├── batch_process_edf_results.py        # EDF 结果批处理
│   ├── batch_process_fifo_batch_results.py # FIFO-Batch 结果批处理
│   ├── batch_process_fifo_results.py       # FIFO 结果批处理
│   ├── batch_process_main_results.py       # 主算法结果批处理
│   ├── batch_process_resizing_results.py   # Resizing 结果批处理
│   ├── my_statistics.py    # 统计分析工具
│   └── 统计结果/           # 存储各种 DDL 下的性能指标
│
├── 数据
│   ├── tasks/              # 任务文件（CSV格式，不同截止期）
│   ├── images_cropped/     # 裁剪后的图像数据集
│   └── result_with_fifo_edf/ # 实验结果输出
│
└── 工具脚本
    └── delete_files_by_name.py # 文件清理工具（不重要，可删除）
```

## 各程序、文件使用说明

本节详细介绍项目中各个程序和文件的用法。程序按功能分为以下几类：

### 📑 程序总览

#### 1. 批处理推理程序系列（Python）
读取 C 程序生成的调度结果，执行实际的图像推理并记录性能数据：
- `batch_process_edf_results.py` - 处理 EDF 算法的调度结果
- `batch_process_fifo_batch_results.py` - 处理 FIFO-Batch 算法的调度结果
- `batch_process_fifo_results.py` - 处理 FIFO 算法的调度结果
- `batch_process_main_results.py` - 处理 Frame 主算法的调度结果
- `batch_process_resizing_results.py` - 处理 Resizing 算法的调度结果

#### 2. C 语言调度算法程序系列
实现不同的任务调度策略，生成调度方案（不执行实际推理）：
- `fifo.c` - FIFO 先进先出调度器（基准算法）
- `fifo_batch.c` - FIFO 批处理调度器（吞吐量优化）
- `cf-batch.c` - CF-Batch 分类感知调度器（关键任务优先）
- `main.c` - Frame主调度器（早期退出 + 动态调度）
- `resizing.c` - Resizing 调度器（图像尺寸动态调整）

#### 3. 统计分析工具（Python）
- `my_statistics.py` - 综合性能分析工具，对比五种算法的性能指标并生成报告

#### 4. 图像推理引擎（Python）
- `simple_inference.py` - 推理引擎核心类，负责加载模型、执行推理、性能测量

#### 5. 实验自动化工具（Python）
- `experiment.py` - 批量实验执行器，自动编译 C 程序并运行大规模实验

#### 6. 任务生成工具（Python）
- `make_csv.py` - 任务 CSV 文件生成器，从图像数据集批量生成任务文件

#### 7. 其他支持文件
- `model_torch.py` - Early-Exit ResNet18 模型定义（略）

---

### 1. 批处理推理程序系列

项目包含五个批处理推理程序，用于测试不同调度算法的性能表现。这些程序具有相同的代码结构，唯一区别在于读取的任务文件路径不同。

#### 📋 程序列表

| 程序名称 | 对应调度算法 | 读取的结果文件 |
|---------|-------------|--------------|
| `batch_process_edf_results.py` | **EDF (最早截止期优先)** | `*_edf_result.json` |
| `batch_process_fifo_batch_results.py` | **FIFO-Batch** | `*_fifo_batch_result.json` |
| `batch_process_fifo_results.py` | **FIFO** | `*_fifo_result.json` |
| `batch_process_main_results.py` | **Frame (主算法)** | `*_main_result.json` |
| `batch_process_resizing_results.py` | **Resizing** | `*_resizing_result.json` |

#### 🎯 功能说明

这些程序的**共同功能**：
1. **加载多尺寸模型**：从 `model/` 目录加载 64px、128px、256px、512px 四个模型
2. **读取调度结果**：从对应的 JSON 文件读取 C 程序生成的任务批次
3. **批量推理处理**：按批次顺序执行图像分类推理
4. **性能测量**：
   - 记录每个批次的处理时间
   - 计算累计处理时间
   - 检测是否错过 deadline
   - 统计关键任务（crucial）的完成情况
5. **保存结果**：输出预测类别和性能指标到对应的 `*_time.json` 文件



#### 🚀 使用方法
    在main（）函数的folders_to_proces中输入要处理的任务文件夹路径，然后配置好参数即可运行


#### 📈 性能指标

每个程序会输出：
- ✅ **预测结果**：每张图片的预测类别和类别 ID
- ⏱️ **批次时间**：每个批次的处理时间（毫秒）
- 📊 **累计时间**：从开始到当前的总耗时
- ⚠️ **Deadline Miss**：错过截止期的图片列表
- 🎯 **关键任务标记**：标记 crucial=1 的重要任务


#### 🔗 相关文件说明

- **simple_inference.py**：提供 `SimpleInference` 类和 `process_single_result()` 函数
- **model_torch.py**：定义 Early-Exit ResNet18 模型结构
- **my_statistics.py**：用于统计所有实验结果的综合性能指标

---

### 2. C 语言调度算法程序系列

项目实现了五种不同的任务调度算法，均采用 C 语言编写。这些程序读取任务 CSV 文件，根据各自的调度策略生成任务批次，并输出 JSON 格式的调度结果供 Python 程序进行推理验证。
#### 📋 程序列表
| 程序名称 | 调度算法 | 输出文件 | 特性 |
|---------|---------|---------|------|
| `fifo.c` | **FIFO (先进先出)** | `output_fifo.json` | 单任务处理，无批处理 |
| `fifo_batch.c` | **FIFO-Batch** | `output_fifo_batch.json` | 相同尺寸批处理 |
| `cf-batch.c` | **CF-Batch** | `output_cf_batch.json` | 关键任务优先 + 批处理 |
| `main.c` | **Frame (主算法)** | `output_main.json` | 早期退出 + 动态调度 |
| `resizing.c` | **Resizing** | `output_resizing.json` | 图像尺寸调整优化 |
#### 📊 输入格式（CSV）
所有程序使用统一的 CSV 输入格式：
```csv
size,deadline,id,crucial,category
4,25.5,1,1,car
3,30.0,2,0,person
2,20.0,3,1,bicycle
```
**字段说明**：
- `size`：图像尺寸索引（1=64px, 2=128px, 3=256px, 4=512px）
- `deadline`：截止时间（毫秒）
- `id`：任务 ID
- `crucial`：关键任务标记（1=关键，0=非关键）
- `category`：图像类别（bench/bicycle/car/motorcycle/person/traffic light/train）
#### 📤 输出格式（JSON）
**调度结果文件** (`output_*.json`)：
**未完成任务文件** (`missed_tasks_*.json`)：
#### 🔗 工作流程
```
1. 生成任务 CSV
   └─ python make_csv.py

2. 运行调度器（C 程序）
   └─ ./main tasks/task_1.csv
   └─ 生成 output_main.json

3. 执行推理（Python 程序）
   └─ python batch_process_main_results.py
   └─ 读取 output_main.json
   └─ 生成 output_main_time.json
4. 统计分析
   └─ python my_statistics.py
   └─ 生成性能报告
```

---

### 3. my_statistics.py - 统计分析工具

`my_statistics.py` 是一个综合性能分析工具，用于对比五种调度算法（main、resizing、fifo、fifo_batch、cf_batch）在多个实验中的性能表现，并生成详细的 Markdown 格式统计报告。

#### 🎯 主要功能

1. **读取任务定义**：从 CSV 文件中读取所有任务，识别关键任务（crucial=1）
2. **解析推理结果**：读取各算法生成的 `*_time.json` 文件
3. **计算性能指标**：
   - **关键任务错失率（Miss Rate）**：未完成的关键任务占比
   - **关键任务准确率（Accuracy）**：已完成关键任务的分类准确率
   - **非关键任务处理量（Throughput）**：成功处理的非关键任务数量
4. **生成统计报告**：输出 Markdown 格式的对比分析报告

#### ⚙️ 配置参数
在文件开头可以配置以下参数：
```python
# 任务目录路径（{ddl} 会被替换为实际的 DDL 值）
DEFAULT_TASK_DIR = "tasks/task_files_ddl{ddl}"
# 结果目录路径（{ddl} 会被替换为实际的 DDL 值）
DEFAULT_RESULT_DIR = "result_with_fifo_edf/result_list_ddl{ddl}"
```
#### 🚀 使用方法

直接运行，程序会：
1. 读取 `tasks/task_files_ddl50/` 中的所有任务 CSV 文件
2. 读取 `result_with_fifo_edf/result_list_ddl50/` 中的所有推理结果
3. 生成 `ddl50_metrics_<timestamp>.md` 统计报告
#### 📂 输入文件结构
程序需要以下目录结构：

```
tasks/task_files_ddl25/
├── tasks_1.csv
├── tasks_2.csv
├── tasks_3.csv
└── ...

result_with_fifo_edf/result_list_ddl25/
├── result_1/
│   ├── main_time.json
│   ├── resizing_time.json
│   ├── fifo_time.json
│   ├── fifo_batch_time.json
│   └── cf_batch_time.json
├── result_2/
│   └── ...
└── ...
```
**命名规则**：
- 任务文件：`tasks_{编号}.csv`
- 结果目录：`result_{编号}/`
- 编号必须对应（如 `tasks_1.csv` 对应 `result_1/`）
#### 🔗 相关文件
- **输入**：由 C 调度程序生成的 `output_*.json`，经 Python 批处理程序处理后生成 `*_time.json`
- **输出**：Markdown 格式的统计报告，保存在当前目录或 `统计结果/` 目录
- **配合使用**：
  - `make_csv.py`：生成任务文件
  - `experiment.py`：批量运行实验
  - `batch_process_*_results.py`：处理推理结果
  - `实验相关/吞吐量.py`：可视化吞吐量对比
  - `实验相关/准确率.py`：可视化准确率对比
  - `实验相关/miss率.py`：可视化 miss 率对比

---

### 4. simple_inference.py - 图像推理引擎

#### 🎯 核心功能

1. **多模型管理**：同时加载和管理 4 个不同尺寸的 ResNet18 模型（64/128/256/512px）
2. **批量推理**：支持批量图像处理，利用 GPU 加速
3. **性能测量**：精确计时每个批次的处理时间和累计时间
4. **Deadline 检测**：自动判断任务是否在截止期内完成
5. **结果输出**：生成包含预测类别、时间统计、错失任务的 JSON 报告

**参数说明**：
- `json_file_path`: 输入的调度结果 JSON 文件
- `output_json_path`: 输出的推理结果 JSON 文件
- `model_paths`: 模型路径字典
- `image_folder`: 图像文件夹路径
- `num_classes`: 分类类别数量
- `inference_instance`: 可选，复用已有的 SimpleInference 实例

#### 🚀 使用方法

**方式一：直接运行（测试用）**
程序会：
1. 加载 `model/` 目录下的四个模型
2. 读取 `result_list/result_1/main_result.json`
3. 对 `images_cropped/cropped_1/` 中的图像进行推理
4. 输出结果到 `result_list/result_1/main_time.json`

**方式二：作为模块导入**

```python
from simple_inference import SimpleInference, process_single_result
# 配置模型路径
model_paths = {
    64: 'model/model_64.pth',
    128: 'model/model_128.pth',
    256: 'model/model_256.pth',
    512: 'model/model_512.pth'
}
# 方法 1: 使用便捷函数
process_single_result(
    json_file_path='result_list/result_1/main_result.json',
    output_json_path='result_list/result_1/main_time.json',
    model_paths=model_paths,
    image_folder='images_cropped/cropped_1',
    num_classes=7
)
# 方法 2: 使用类实例（适合批量处理）
inference = SimpleInference(model_paths, 'images_cropped/cropped_1', num_classes=7)
results = inference.process_json_file('result_list/result_1/main_result.json')
inference.save_results(results, 'result_list/result_1/main_time.json')
```
#### 📊 输入格式

读取 C 程序生成的 JSON 文件：
**格式说明**：
- 每个批次包含 `size`（图像尺寸）和 `images`（图像列表）
- `images` 可以是字符串（普通任务）或对象（关键任务）
- 最后一个元素是 `deadline` 对象（以秒为单位）
#### 📤 输出格式

生成包含推理结果和性能数据的 JSON 文件：
**输出包含**：
- **图像结果**：每张图像的预测类别和是否为关键任务
- **批次信息**：批次处理时间和累计时间
- **Deadline 信息**：截止期和错过截止期的图像列表

---

### 5. experiment.py - 批量实验执行器
`experiment.py` 是一个自动化批量实验执行工具，用于一次性运行多个调度算法在大量任务集上的实验，并自动收集和汇总结果。这是进行大规模性能对比实验的核心工具。
#### 🎯 核心功能
1. **自动编译**：每次运行时自动重新编译所有 C 调度算法程序，确保使用最新代码
2. **批量执行**：自动运行指定数量的实验，每个实验包含多个调度算法
3. **结果管理**：自动组织和保存每个实验的结果文件
4. **错误处理**：检测并记录任务丢失、超时等异常情况
5. **汇总报告**：生成详细的实验汇总报告，包含统计信息和状态表格
#### ⚙️ 配置参数
程序开头的配置参数：
```python
# 任务文件目录
TASK_FILES_DIR = "tasks/task_files_ddl25"  # CSV 任务文件目录,可修改ddl的后缀更换目标文件

# 结果保存目录
RESULT_DIR = "test/test2"  # 结果保存目录

# 可执行文件路径
FIFO_BATCH_EXE = "./fifo_batch"  # fifo_batch.c 编译后的可执行文件
CF_BATCH_EXE = "./cf_batch"      # cf-batch.c 编译后的可执行文件
FIFO_EXE = "./fifo"              # fifo.c 编译后的可执行文件

# 实验数量
NUM_EXPERIMENTS = 200  # 要运行的实验数量

# 输出文件名（C 程序生成的临时文件）
FIFO_BATCH_OUTPUT = "output_fifo_batch.json"
CF_BATCH_OUTPUT = "output_cf_batch.json"
FIFO_OUTPUT = "output_fifo.json"
```
#### 🚀 使用方法

**步骤 1：准备任务文件**

确保任务文件已准备好：
```
tasks/task_files_ddl25/
├── tasks_1.csv
├── tasks_2.csv
├── tasks_3.csv
├── ...
└── tasks_200.csv
```

**步骤 2：配置实验参数**

根据需求修改 `experiment.py` 中的配置：
- `TASK_FILES_DIR`：任务文件所在目录
- `RESULT_DIR`：结果保存目录
- `NUM_EXPERIMENTS`：要运行的实验数量（1-200）

**步骤 3：运行实验**
```bash
python experiment.py
```
**步骤 4：查看结果**

实验完成后，结果保存在指定的 `RESULT_DIR` 目录下：
```
test/test2/
├── result_1/
│   ├── fifo_batch_result.json
│   ├── cf_batch_result.json
│   ├── fifo_result.json
│   └── (可能包含 *_missed_tasks.json)
├── result_2/
│   └── ...
├── ...
└── experiment_summary.json  # 汇总报告
```
#### 📊 实验流程

每个实验的执行流程：

```
1. 清理旧的输出文件
   └─ 删除临时 JSON 文件（避免混淆）

2. 运行 fifo_batch.exe
   └─ 读取 tasks_N.csv
   └─ 生成 output_fifo_batch.json
   └─ 复制到 result_N/fifo_batch_result.json
   └─ 检测并复制 missed_tasks_batch.json（如有）

3. 运行 cf_batch.exe
   └─ 读取 tasks_N.csv
   └─ 生成 output_cf_batch.json
   └─ 复制到 result_N/cf_batch_result.json
   └─ 检测并复制 missed_tasks_cf_batch.json（如有）

4. 运行 fifo.exe
   └─ 读取 tasks_N.csv
   └─ 生成 output_fifo.json
   └─ 复制到 result_N/fifo_result.json
   └─ 检测并复制 missed_tasks.json（如有）

5. 记录实验结果和状态
```

#### 📈 输出文件说明

**1. 调度结果文件** (`*_result.json`)

每个算法生成一个结果文件，包含任务批次信息：
```json
[
  {
    "size": 256,
    "images": ["1_car", {"id": "2_person", "crucial": 1}]
  },
  {"deadline": 1.5}
]
```

**2. 任务丢失文件** (`*_missed_tasks.json`)

如果有任务超过截止期未完成，会生成此文件：
```json
{
  "total_tasks": 100,
  "completed_tasks": 85,
  "missed_tasks": 15,
  "missed_crucial": 3,
  "missed_task_list": [...]
}
```

#### 🔗 工作流程

完整的实验流程：

```
1. make_csv.py
   └─ 生成任务 CSV 文件（tasks_1.csv ~ tasks_200.csv）

2. experiment.py (本程序)
   └─ 自动编译 C 程序
   └─ 批量运行所有调度算法
   └─ 生成调度结果 JSON 文件

3. batch_process_*_results.py
   └─ 读取调度结果
   └─ 执行实际推理
   └─ 生成推理结果和性能数据

4. my_statistics.py
   └─ 统计分析所有实验
   └─ 生成性能对比报告

5. 实验相关/*.py
   └─ 可视化性能数据
   └─ 生成图表
```

---

### 6. make_csv.py - 任务 CSV 文件生成器

`make_csv.py` 是一个自动化工具，用于从图像数据集批量生成任务 CSV 文件。它扫描指定的图像文件夹，解析图像文件名，并根据配置规则生成符合调度算法要求的任务文件。

#### 🎯 核心功能
1. **批量扫描图像**：自动扫描多个图像文件夹（如 cropped_1 到 cropped_200）
2. **文件名解析**：从图像文件名提取尺寸、ID 和类别信息
3. **关键任务分配**：根据图像尺寸概率性地标记关键任务
4. **CSV 生成**：为每个文件夹生成对应的任务 CSV 文件
5. **统一配置**：支持统一设置 deadline 和输出目录

#### ⚙️ 配置参数
程序开头的配置参数：

# 截止时间设置
DEADLINE = 20.0  # 统一的截止时间（毫秒）
# 目录配置
BASE_DIR = "images_cropped"  # 图片文件夹根目录
OUTPUT_DIR = "task_files_ddl20"  # 输出 CSV 文件的文件夹
# 关键任务概率（根据图像尺寸）
CRUCIAL_PROB = {
    64: 0.2,   # 64×64：20% 概率为关键任务
    128: 0.4,  # 128×128：40% 概率为关键任务
    256: 0.7,  # 256×256：70% 概率为关键任务
    512: 1.0   # 512×512：100% 概率为关键任务
}
# 尺寸映射：实际像素 -> 索引
SIZE_MAPPING = {
    64: 1,
    128: 2,
    256: 3,
    512: 4
}
```
#### 📝 图像文件命名规范

程序要求图像文件遵循特定的命名格式：

```
{size}_{id}_{category}.jpg
```

**示例**：
```
64_19_car.jpg          → 尺寸=64, ID=64_19, 类别=car
128_5_person.jpg       → 尺寸=128, ID=128_5, 类别=person
256_42_bicycle.jpg     → 尺寸=256, ID=256_42, 类别=bicycle
512_8_traffic_light.jpg → 尺寸=512, ID=512_8, 类别=traffic_light
```

**字段说明**：
- `size`：图像尺寸（64/128/256/512）
- `id`：任务 ID（由 size_编号 组成）
- `category`：图像类别（可包含下划线，如 traffic_light）

#### 🚀 使用方法

**步骤 1：准备图像数据集**

确保图像按文件夹组织：
```
images_cropped/
├── cropped_1/
│   ├── 64_1_car.jpg
│   ├── 128_2_person.jpg
│   ├── 256_3_bicycle.jpg
│   └── ...
├── cropped_2/
│   └── ...
├── ...
└── cropped_200/
    └── ...
```

**步骤 2：配置参数**
根据需求修改 `make_csv.py` 中的配置：
- `DEADLINE`：设置任务截止时间（建议值：10-50 毫秒）
- `OUTPUT_DIR`：输出目录名（建议包含 DDL 信息，如 `task_files_ddl25`）
- `CRUCIAL_PROB`：调整不同尺寸的关键任务比例
**步骤 3：运行程序**

```bash
python make_csv.py
```
