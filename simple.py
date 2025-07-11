import json
import os
from typing import Set, Any, List, Dict
from collections import Counter

def extract_values(data: Any, keys_to_extract: List[str], results: Dict[str, Dict[str, Any]]):
    """
    递归遍历JSON数据，提取所有指定key字段的值。

    Args:
        data: JSON数据（可能是字典、列表或其他类型）。
        keys_to_extract: 需要提取的key的列表。
        results: 存储提取结果的字典。
                 结构: {"key_name": {"unique_values": set(), "all_values": list()}}
    """
    if isinstance(data, dict):
        # 如果是字典，遍历所有键值对
        for key, value in data.items():
            # 检查当前key是否是需要提取的目标之一
            if key in keys_to_extract and isinstance(value, str) and value.strip():
                stripped_value = value.strip()
                results[key]["unique_values"].add(stripped_value)
                results[key]["all_values"].append(stripped_value)
            
            # 递归处理值
            extract_values(value, keys_to_extract, results)
    
    elif isinstance(data, list):
        # 如果是列表，遍历所有元素
        for item in data:
            extract_values(item, keys_to_extract, results)


def process_single_file(file_path: str, keys_to_extract: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    处理单个JSON文件，提取所有指定key字段的值。

    Args:
        file_path: JSON文件路径。
        keys_to_extract: 需要提取的key的列表。
        
    Returns:
        一个包含唯一值集合和所有值列表的结果字典。
    """
    # 初始化结果结构
    results = {key: {"unique_values": set(), "all_values": []} for key in keys_to_extract}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            # 尝试处理一些常见的嵌套结构
            if isinstance(json_data, dict) and "content" in json_data:
                json_data = json_data["content"]
            if isinstance(json_data, dict) and "final_structured_response" in json_data:
                json_data = json_data["final_structured_response"]
        
        # 递归提取字段
        extract_values(json_data, keys_to_extract, results)
        
    except Exception as e:
        print(f"处理文件时出错 {file_path}: {e}")
        # 出错时返回空的结果结构
        return {key: {"unique_values": set(), "all_values": []} for key in keys_to_extract}
    
    return results


def process_directory(directory_path: str, keys_to_extract: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    处理目录中的所有JSON文件，提取并聚合所有指定key字段的值。

    Args:
        directory_path: 包含JSON文件的目录路径。
        keys_to_extract: 需要提取的key的列表。
        
    Returns:
        一个包含唯一值集合和频次统计(Counter)的聚合结果字典。
    """
    # 初始化聚合结果结构
    aggregated_results = {key: {"unique_values": set(), "counter": Counter()} for key in keys_to_extract}
    processed_files = 0
    error_files = []
    
    print(f"开始处理目录: {directory_path}")
    
    # 遍历目录中的所有文件
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                print(f"正在处理: {os.path.basename(file_path)}")
                
                single_file_results = process_single_file(file_path, keys_to_extract)
                
                found_something = False
                for key in keys_to_extract:
                    if single_file_results[key]["unique_values"]:
                        found_something = True
                        # 更新唯一值集合
                        aggregated_results[key]["unique_values"].update(single_file_results[key]["unique_values"])
                        # 更新频次统计
                        aggregated_results[key]["counter"].update(single_file_results[key]["all_values"])
                
                if found_something:
                    processed_files += 1
                    summary = ", ".join([f"{len(single_file_results[k]['unique_values'])}个{k}" for k in keys_to_extract if single_file_results[k]['unique_values']])
                    print(f"  - 找到 {summary}")
                else:
                    error_files.append(file_path)
    
    print(f"\n处理完成!")
    print(f"成功处理 {processed_files} 个JSON文件")
    if error_files:
        print(f"处理失败或未找到任何指定字段的文件 {len(error_files)} 个")
    
    for key in keys_to_extract:
        print(f"总计找到 {len(aggregated_results[key]['unique_values'])} 个唯一的 '{key}' 字段")

    return aggregated_results


def save_results(results: Dict[str, Dict[str, Any]], keys_to_extract: List[str], output_dir: str = "."):
    """
    保存提取结果到文件。

    Args:
        results: 包含唯一值和频次统计的结果字典。
        keys_to_extract: 提取的key的列表。
        output_dir: 输出目录。
    """
    # 创建基础JSON输出结构
    json_output = {
        "extraction_summary": {},
    }

    print("\n结果将保存到:")
    
    for key in keys_to_extract:
        data = results.get(key, {"unique_values": set(), "counter": Counter()})
        unique_values_list = sorted(list(data["unique_values"]))
        frequency_counter = data["counter"]
        
        # 更新JSON总览
        json_output["extraction_summary"][f"total_unique_{key}"] = len(unique_values_list)
        json_output["extraction_summary"][f"total_{key}_occurrences"] = sum(frequency_counter.values())
        
        # 添加详细数据到JSON
        json_output[key] = unique_values_list
        
        # 添加频次信息到JSON
        if frequency_counter:
            sorted_by_freq = sorted(frequency_counter.items(), key=lambda x: x[1], reverse=True)
            json_output[f"{key}_frequency"] = {
                "total_occurrences": sum(frequency_counter.values()),
                "unique_count": len(frequency_counter),
                "frequency_stats": dict(frequency_counter),
                "sorted_by_frequency": sorted_by_freq
            }

        # 保存唯一值到文本文件
        values_file = os.path.join(output_dir, f"{key}.txt")
        with open(values_file, 'w', encoding='utf-8') as f:
            for value in unique_values_list:
                f.write(f"{value}\n")
        print(f"  - {key} 唯一值文件: {values_file}")

        # 保存频次统计文件
        if frequency_counter:
            freq_file = os.path.join(output_dir, f"{key}_frequency.txt")
            with open(freq_file, 'w', encoding='utf-8') as f:
                f.write(f"{key}\tFrequency\n")
                sorted_by_freq = sorted(frequency_counter.items(), key=lambda x: x[1], reverse=True)
                for value, freq in sorted_by_freq:
                    f.write(f"{value}\t{freq}\n")
            print(f"  - {key} 频次文件: {freq_file}")

    # 保存总的JSON文件
    json_file = os.path.join(output_dir, "extracted_fields_summary.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"\n  - 汇总JSON文件: {json_file}")


def main():
    """
    主函数 - 处理JSON文件或文件夹
    """
    input_path = input("请输入JSON文件路径或包含JSON文件的文件夹路径: ").strip()
    
    # 去除可能的引号
    if input_path.startswith(('"', "'")) and input_path.endswith(('"', "'")):
        input_path = input_path[1:-1]
    
    if not os.path.exists(input_path):
        print(f"错误: 路径不存在 - {input_path}")
        return

    # 获取用户想要提取的key
    keys_str = input("请输入要提取的key，用逗号分隔 (例如: name, physical_form, author): ").strip()
    if not keys_str:
        print("错误: 未输入任何key。")
        return
    keys_to_extract = [key.strip() for key in keys_str.split(',') if key.strip()]

    final_results = {key: {"unique_values": set(), "counter": Counter()} for key in keys_to_extract}

    if os.path.isfile(input_path):
        if not input_path.endswith('.json'):
            print(f"警告: 文件似乎不是JSON格式 - {input_path}")
        print("处理单个JSON文件...")
        single_file_results = process_single_file(input_path, keys_to_extract)
        # 转换格式以匹配聚合结果的结构
        for key in keys_to_extract:
            final_results[key]["unique_values"] = single_file_results[key]["unique_values"]
            final_results[key]["counter"] = Counter(single_file_results[key]["all_values"])
            
    elif os.path.isdir(input_path):
        print("处理文件夹中的所有JSON文件...")
        final_results = process_directory(input_path, keys_to_extract)
        
    else:
        print(f"错误: 无法识别的路径类型 - {input_path}")
        return
    
    # 显示预览
    print("\n=== 提取结果预览 ===")
    found_any_results = False
    for key in keys_to_extract:
        unique_values = final_results[key]["unique_values"]
        if unique_values:
            found_any_results = True
            print(f"\n字段 '{key}' (前15个):")
            sorted_values = sorted(list(unique_values))
            for i, value in enumerate(sorted_values[:15]):
                print(f"  {i+1}. {value}")
            if len(unique_values) > 15:
                print(f"  ... 还有 {len(unique_values) - 15} 个")
        else:
            print(f"\n未在任何文件中找到字段 '{key}'")
    
    # 询问是否保存结果
    if found_any_results:
        save_choice = input("\n是否保存结果到文件? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes', '是']:
            output_dir = input("输入保存目录 (默认当前目录): ").strip()
            if not output_dir:
                output_dir = "."
            
            os.makedirs(output_dir, exist_ok=True)
            save_results(final_results, keys_to_extract, output_dir)
    else:
        print("\n没有提取到任何数据，无需保存。")


if __name__ == "__main__":
    main()
