# 用法说明

本指南将引导您完成“语义属性聚类分析工具”的安装、配置和运行。

## 1. 环境准备

### 安装依赖库

首先，请确保您的系统已安装 Python 3.8 或更高版本。然后，打开您的终端或命令行工具，使用 pip 安装所有必需的 Python 库。

```
pip install torch sentence-transformers pandas numpy

```

- `torch`: PyTorch 深度学习框架，是 `sentence-transformers` 的基础。
- `sentence-transformers`: 用于加载 SBERT 模型并生成高质量语义向量的核心库。
- `pandas`: 用于高效地处理和转换从 JSON 文件中加载的数据。
- `numpy`: `pandas` 的依赖库，用于数值计算。

## 2. 准备输入数据

脚本需要一个特定结构的 JSON 文件作为输入。请确保您的 JSON 文件包含一个顶级键（例如 `names_frequency`），该键的值是一个对象，其中必须包含一个名为 `sorted_by_frequency` 的键。

`sorted_by_frequency` 的值应该是一个列表，其中每个元素都是一个包含两个值的小列表：`[属性名, 频率]`。

**示例 `input.json` 文件结构:**

```
{
  "names_frequency": {
    "total_unique_names": 150,
    "sorted_by_frequency": [
      ["螺杆", 120],
      ["螺丝钉", 85],
      ["螺钉", 82],
      ["固定栓", 15],
      ["金属杆", 9],
      ["铁棒", 7]
    ]
  },
  "physical_forms_frequency": {
    "total_unique_forms": 50,
    "sorted_by_frequency": [
      ["固体", 200],
      ["条状", 150],
      ["长条状", 145]
    ]
  }
}

```

## 3. 配置脚本

打开 `main.py` 文件，在文件底部的 `if __name__ == '__main__':` 代码块中，您会找到一个名为 `CONFIG` 的 Python 字典。请根据您的需求修改这些参数。

```
CONFIG = {
    # --- 文件路径 ---
    # 修改为您的输入JSON文件的绝对或相对路径
    "input_json_path": 'path/to/your/input.json',

    # 定义输出CSV文件的路径和名称
    "output_csv_path": 'property_clusters_output_secondary.csv',

    # --- 数据字段 ---
    # 指定要分析的JSON文件中的顶级键
    "field_to_analyze": 'names_frequency',

    # --- 模型与聚类参数 ---
    # SBERT模型名称，'all-MiniLM-L6-v2' 是一个轻量且高效的选择
    "sbert_model": 'all-MiniLM-L6-v2',

    # 第一轮聚类相似度阈值 (0.0 - 1.0)。值越高，聚类越严格。
    "primary_cluster_threshold": 0.85,

    # 第二轮聚类相似度阈值。通常应高于第一轮以实现精细划分。
    "secondary_cluster_threshold": 0.95,

    # 在第一轮聚类中，形成一个簇所需的最少成员数量。
    "min_community_size": 2,

    # --- 频率筛选参数 ---
    # 用于计算频率百分比基数的总文件数或总记录数。
    "file_count_for_threshold": 1000,

    # 频率筛选阈值。低于 (基数 * 此百分比) 的簇将被合并或归入'Others'。
    "frequency_threshold_percent": 0.01 # 代表 1%
}

```

## 4. 运行脚本

完成配置后，在您的终端中导航到脚本所在的目录，然后执行以下命令：

```
python main.py

```

脚本将开始执行，并按顺序在控制台打印出每个步骤的进度和信息。

## 5. 查看结果

脚本运行完毕后，您将在 `output_csv_path` 指定的位置找到一个 CSV 文件。该文件包含了所有聚类的详细信息。

**输出 CSV 文件格式说明:**

| 列名 | 说明 |
| --- | --- |
| `cluster_id` | 簇的唯一标识符。一个数字，或 "Others"。 |
| `cluster_total_frequency` | 该簇内所有成员的频率总和。 |
| `member_count` | 该簇包含的成员数量。 |
| `property` | 簇内的具体属性名。 |
| `count` | 该具体属性自身的频率。 |

您可以使用 Microsoft Excel、Google Sheets 或任何支持 CSV 格式的工具打开此文件，以进行排序、筛选和进一步的分析。