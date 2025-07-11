import json
import os
from typing import Set, Any, List, Dict
from collections import Counter


def extract_name_and_physical_form(data: Any, names: Set[str], physical_forms: Set[str], names_list: List[str] = None, physical_forms_list: List[str] = None):
    """
    递归遍历JSON数据，提取所有name和physical_form字段的值
    
    Args:
        data: JSON数据（可能是字典、列表或其他类型）
        names: 存储name字段值的集合（去重）
        physical_forms: 存储physical_form字段值的集合（去重）
        names_list: 存储所有name字段值的列表（用于频次统计）
        physical_forms_list: 存储所有physical_form字段值的列表（用于频次统计）
    """
    if names_list is None:
        names_list = []
    if physical_forms_list is None:
        physical_forms_list = []
        
    if isinstance(data, dict):
        # 如果是字典，遍历所有键值对
        for key, value in data.items():
            # 检查是否是name字段
            if key == "name" and isinstance(value, str) and value.strip():
                name = value.strip()
                names.add(name)
                names_list.append(name)
            
            # 检查是否是physical_form字段
            elif key == "physical_form" and isinstance(value, str) and value.strip():
                form = value.strip()
                physical_forms.add(form)
                physical_forms_list.append(form)
            
            # 递归处理值
            extract_name_and_physical_form(value, names, physical_forms, names_list, physical_forms_list)
    
    elif isinstance(data, list):
        # 如果是列表，遍历所有元素
        for item in data:
            extract_name_and_physical_form(item, names, physical_forms, names_list, physical_forms_list)


def process_single_file(file_path: str) -> tuple[Set[str], Set[str], List[str], List[str]]:
    """
    处理单个JSON文件，提取所有name和physical_form字段的值
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        (names集合, physical_forms集合, names列表, physical_forms列表)
    """
    names = set()
    physical_forms = set()
    names_list = []
    physical_forms_list = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
            # 尝试处理可能的嵌套结构
            if isinstance(json_data, dict) and "content" in json_data:
                json_data = json_data["content"]
            if isinstance(json_data, dict) and "final_structured_response" in json_data:
                json_data = json_data["final_structured_response"]
        # 递归提取name和physical_form字段
        extract_name_and_physical_form(json_data, names, physical_forms, names_list, physical_forms_list)
        
    except Exception as e:
        print(f"处理文件时出错 {file_path}: {e}")
        return set(), set(), [], []
    
    return names, physical_forms, names_list, physical_forms_list


def process_directory(directory_path: str) -> tuple[Set[str], Set[str], Dict[str, int], Dict[str, int]]:
    """
    处理目录中的所有JSON文件，提取所有name和physical_form字段的值
    
    Args:
        directory_path: 包含JSON文件的目录路径
        
    Returns:
        (names集合, physical_forms集合, names频次字典, physical_forms频次字典)
    """
    all_names = set()
    all_physical_forms = set()
    names_counter = Counter()  # 统计name频次
    physical_forms_counter = Counter()  # 统计physical_form频次
    processed_files = 0
    error_files = []
    
    print(f"开始处理目录: {directory_path}")
    
    # 遍历目录中的所有文件
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                print(f"正在处理: {os.path.basename(file_path)}")
                
                names, physical_forms, names_list, physical_forms_list = process_single_file(file_path)
                
                if names or physical_forms:
                    all_names.update(names)
                    all_physical_forms.update(physical_forms)
                    # 更新频次统计
                    names_counter.update(names_list)
                    physical_forms_counter.update(physical_forms_list)
                    processed_files += 1
                    print(f"  - 找到 {len(names)} 个name, {len(physical_forms)} 个physical_form")
                else:
                    error_files.append(file_path)
    
    print(f"\n处理完成!")
    print(f"成功处理 {processed_files} 个JSON文件")
    if error_files:
        print(f"处理失败 {len(error_files)} 个文件")
    
    print(f"总计找到 {len(all_names)} 个唯一的name字段")
    print(f"总计找到 {len(all_physical_forms)} 个唯一的physical_form字段")
    
    return all_names, all_physical_forms, dict(names_counter), dict(physical_forms_counter)


def save_results(names: Set[str], physical_forms: Set[str], names_frequency: Dict[str, int] = None, physical_forms_frequency: Dict[str, int] = None, output_dir: str = "."):
    """
    保存提取结果到文件
    
    Args:
        names: name字段值的集合
        physical_forms: physical_form字段值的集合
        names_frequency: name字段的频次字典
        physical_forms_frequency: physical_form字段的频次字典
        output_dir: 输出目录
    """
    # 转换为排序列表
    names_list = sorted(list(names))
    physical_forms_list = sorted(list(physical_forms))
    
    # 创建基础JSON输出结构
    json_output = {
        "extraction_summary": {
            "total_names": len(names_list),
            "total_physical_forms": len(physical_forms_list)
        },
        "names": names_list,
        "physical_forms": physical_forms_list
    }
    
    # 如果有频次信息，添加到JSON输出中
    if names_frequency is not None:
        names_sorted_by_freq = sorted(names_frequency.items(), key=lambda x: x[1], reverse=True)
        json_output["names_frequency"] = {
            "total_occurrences": sum(names_frequency.values()),
            "unique_count": len(names_frequency),
            "frequency_stats": names_frequency,
            "sorted_by_frequency": names_sorted_by_freq
        }
        json_output["extraction_summary"]["total_name_occurrences"] = sum(names_frequency.values())
    
    if physical_forms_frequency is not None:
        physical_forms_sorted_by_freq = sorted(physical_forms_frequency.items(), key=lambda x: x[1], reverse=True)
        json_output["physical_forms_frequency"] = {
            "total_occurrences": sum(physical_forms_frequency.values()),
            "unique_count": len(physical_forms_frequency),
            "frequency_stats": physical_forms_frequency,
            "sorted_by_frequency": physical_forms_sorted_by_freq
        }
        json_output["extraction_summary"]["total_physical_form_occurrences"] = sum(physical_forms_frequency.values())
    
    json_file = os.path.join(output_dir, "extracted_fields.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    # 保存names到文本文件
    names_file = os.path.join(output_dir, "names.txt")
    with open(names_file, 'w', encoding='utf-8') as f:
        for name in names_list:
            f.write(f"{name}\n")
    
    # 保存physical_forms到文本文件
    forms_file = os.path.join(output_dir, "physical_forms.txt")
    with open(forms_file, 'w', encoding='utf-8') as f:
        for form in physical_forms_list:
            f.write(f"{form}\n")
    
    # 如果有频次信息，保存频次统计文件
    if names_frequency is not None:
        names_freq_file = os.path.join(output_dir, "names_frequency.txt")
        with open(names_freq_file, 'w', encoding='utf-8') as f:
            f.write("Name\tFrequency\n")
            names_sorted_by_freq = sorted(names_frequency.items(), key=lambda x: x[1], reverse=True)
            for name, freq in names_sorted_by_freq:
                f.write(f"{name}\t{freq}\n")
        print(f"  名称频次文件: {names_freq_file}")
    
    if physical_forms_frequency is not None:
        forms_freq_file = os.path.join(output_dir, "physical_forms_frequency.txt")
        with open(forms_freq_file, 'w', encoding='utf-8') as f:
            f.write("Physical Form\tFrequency\n")
            physical_forms_sorted_by_freq = sorted(physical_forms_frequency.items(), key=lambda x: x[1], reverse=True)
            for form, freq in physical_forms_sorted_by_freq:
                f.write(f"{form}\t{freq}\n")
        print(f"  物理形式频次文件: {forms_freq_file}")
    
    print(f"\n结果已保存到:")
    print(f"  JSON文件: {json_file}")
    print(f"  名称文件: {names_file}")
    print(f"  物理形式文件: {forms_file}")


def main():
    """
    主函数 - 处理JSON文件或文件夹
    """
    # 请修改这里的路径为您要处理的JSON文件或包含JSON文件的文件夹
    input_path = input("请输入JSON文件路径或包含JSON文件的文件夹路径: ").strip()
    
    # 去除可能的引号
    if input_path.startswith('"') and input_path.endswith('"'):
        input_path = input_path[1:-1]
    if input_path.startswith("'") and input_path.endswith("'"):
        input_path = input_path[1:-1]
    
    # 检查路径是否存在
    if not os.path.exists(input_path):
        print(f"错误: 路径不存在 - {input_path}")
        return
    
    # 判断是文件还是目录
    if os.path.isfile(input_path):
        # 处理单个文件
        if not input_path.endswith('.json'):
            print(f"警告: 文件似乎不是JSON格式 - {input_path}")
        print("处理单个JSON文件...")
        names, physical_forms, names_list, physical_forms_list = process_single_file(input_path)
        
        # 为单个文件计算频次
        names_frequency = Counter(names_list)
        physical_forms_frequency = Counter(physical_forms_list)
        
    elif os.path.isdir(input_path):
        # 处理目录中的所有JSON文件
        print("处理文件夹中的所有JSON文件...")
        names, physical_forms, names_frequency, physical_forms_frequency = process_directory(input_path)
        
    else:
        print(f"错误: 无法识别的路径类型 - {input_path}")
        return
    
    # 显示预览
    print("\n=== 提取结果预览 ===")
    
    if names:
        print(f"\nName字段 (前15个):")
        for i, name in enumerate(sorted(names)[:15]):
            print(f"  {i+1}. {name}")
        if len(names) > 15:
            print(f"  ... 还有 {len(names) - 15} 个")
    else:
        print("\n未找到name字段")
    
    if physical_forms:
        print(f"\nPhysical_form字段 (前15个):")
        for i, form in enumerate(sorted(physical_forms)[:15]):
            print(f"  {i+1}. {form}")
        if len(physical_forms) > 15:
            print(f"  ... 还有 {len(physical_forms) - 15} 个")
    else:
        print("\n未找到physical_form字段")
    
    # 询问是否保存结果
    if names or physical_forms:
        save_choice = input("\n是否保存结果到文件? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes', '是']:
            output_dir = input("输入保存目录 (默认当前目录): ").strip()
            if not output_dir:
                output_dir = "."
            
            os.makedirs(output_dir, exist_ok=True)
            save_results(names, physical_forms, names_frequency, physical_forms_frequency, output_dir)


if __name__ == "__main__":
    main()
