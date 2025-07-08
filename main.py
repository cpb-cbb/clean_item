# -*- coding: utf-8 -*-
"""
一个高级脚本，用于对带有频次统计的属性列表进行两轮语义聚类和筛选。

该脚本通过一个主类 `PropertyClusterAnalyzer` 来组织整个流程，使其更具
模块化和可重用性。

工作流程:
1.  从复杂的 JSON 结构中加载属性及其频次。
2.  使用 SBERT 模型为所有属性生成语义向量。
3.  执行第一轮粗粒度聚类。
4.  在每个粗粒度簇内部，执行第二轮细粒度聚类。
5.  根据频率阈值，在细粒度簇内部进行合并。
6.  处理所有聚类和未聚类项，并将最终结果保存到 CSV 文件。
"""
import json
import torch
from sentence_transformers import SentenceTransformer, util
import pandas as pd
import csv
from typing import List, Dict, Any

class PropertyClusterAnalyzer:
    """
    一个用于对属性列表进行两轮语义聚类分析的类。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化分析器。

        Args:
            config (Dict[str, Any]): 包含所有配置参数的字典。
        """
        self.config = config
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"INFO: 使用设备 '{self.device}'")
        self.model = SentenceTransformer(config['sbert_model'], device=self.device)
        self.term_counts = {}
        self.terms_to_cluster = []
        self.unclustered_items = []

    def _load_data(self):
        """从输入JSON文件中加载和准备数据。"""
        print(f"🔄 步骤 1: 正在从 '{self.config['input_json_path']}' 加载数据...")
        try:
            with open(self.config['input_json_path'], "r", encoding="utf-8") as f:
                data = json.load(f)

            field_key = self.config['field_to_analyze']
            if field_key not in data or 'sorted_by_frequency' not in data[field_key]:
                raise ValueError(f"JSON 文件中未找到 '{field_key}' 或其下的 'sorted_by_frequency' 键")

            property_list = data[field_key]['sorted_by_frequency']
            df = pd.DataFrame(property_list, columns=['property', 'count'])
            
            self.terms_to_cluster = df['property'].tolist()
            self.term_counts = df.set_index('property')['count'].to_dict()

            print(f"  - 成功从 '{field_key}' 加载了 {len(self.terms_to_cluster)} 个唯一属性。")
            print("✅ 数据准备完成！")
        except FileNotFoundError:
            print(f"错误: 输入文件 '{self.config['input_json_path']}' 未找到。")
            exit()
        except (json.JSONDecodeError, ValueError) as e:
            print(f"错误: 解析 JSON 文件时出错: {e}")
            exit()

    def _perform_primary_clustering(self, term_embeddings):
        """执行第一轮初步聚类。"""
        print("\n🤖 步骤 2: 正在执行第一轮初步聚类...")
        print(f"  - 参数: 相似度阈值={self.config['primary_cluster_threshold']}, 最小簇大小={self.config['min_community_size']}")
        
        clusters = util.community_detection(
            term_embeddings,
            min_community_size=self.config['min_community_size'],
            threshold=self.config['primary_cluster_threshold']
        )
        print(f"✅ 初步聚类完成！共找到 {len(clusters)} 个簇。")
        
        # 处理结果并识别未聚类项
        clustered_indices = set()
        clustered_results = []
        for i, cluster_indices in enumerate(clusters):
            cluster_members = [{'property': self.terms_to_cluster[idx], 'count': self.term_counts.get(self.terms_to_cluster[idx], 0)} for idx in cluster_indices]
            clustered_results.append({
                'cluster_id': f"primary_{i+1}",
                'members': cluster_members
            })
            clustered_indices.update(cluster_indices)
        
        all_indices = set(range(len(self.terms_to_cluster)))
        unclustered_indices = all_indices - clustered_indices
        self.unclustered_items = [{'property': self.terms_to_cluster[idx], 'count': self.term_counts.get(self.terms_to_cluster[idx], 0)} for idx in unclustered_indices]
        
        print(f"  - {len(clustered_indices)} 个属性被初步聚类。")
        print(f"  - {len(unclustered_indices)} 个属性在第一轮未被聚类。")
        
        return clustered_results

    def _perform_secondary_clustering(self, primary_clusters: List[Dict]) -> List[Dict]:
        """在每个主簇内执行第二轮精聚类和合并。"""
        print("\n🔬 步骤 3: 正在执行第二轮精聚类与合并...")
        final_clusters = []
        
        for p_cluster in primary_clusters:
            members = [member['property'] for member in p_cluster['members']]
            if len(members) <= 1:
                # 如果主簇成员过少，直接视为一个最终簇
                final_clusters.append({
                    'sub_cluster_members': members,
                    'sub_cluster_total_frequency': sum(m['count'] for m in p_cluster['members'])
                })
                continue

            member_embeddings = self.model.encode(members, convert_to_tensor=True, show_progress_bar=False)
            sub_clusters_indices = util.community_detection(
                member_embeddings,
                min_community_size=1,
                threshold=self.config['secondary_cluster_threshold']
            )
            print(f"  - 在簇 {p_cluster['cluster_id']} 内部找到 {len(sub_clusters_indices)} 个子簇。")

            middle_clusters = []
            for indices in sub_clusters_indices:
                sub_members = [members[idx] for idx in indices]
                sub_freq = sum(self.term_counts.get(m, 0) for m in sub_members)
                middle_clusters.append({
                    'sub_cluster_members': sub_members,
                    'sub_cluster_total_frequency': sub_freq
                })
            
            if not middle_clusters:
                continue

            # 按频率排序并合并低频子簇
            sorted_middle = sorted(middle_clusters, key=lambda x: x['sub_cluster_total_frequency'], reverse=True)
            base_cluster = sorted_middle[0]
            retained_sub_clusters = []
            
            freq_threshold_value = self.config['file_count_for_threshold'] * self.config['frequency_threshold_percent']

            for i in range(1, len(sorted_middle)):
                sub_cluster = sorted_middle[i]
                if sub_cluster['sub_cluster_total_frequency'] < freq_threshold_value:
                    base_cluster['sub_cluster_members'].extend(sub_cluster['sub_cluster_members'])
                    base_cluster['sub_cluster_total_frequency'] += sub_cluster['sub_cluster_total_frequency']
                else:
                    retained_sub_clusters.append(sub_cluster)
            
            retained_sub_clusters.insert(0, base_cluster)
            final_clusters.extend(retained_sub_clusters)
            
        print(f"✅ 第二轮处理完成！共形成 {len(final_clusters)} 个最终簇。")
        return final_clusters

    def _save_results_to_csv(self, final_clusters: List[Dict]):
        """将最终结果保存到CSV文件。"""
        output_path = self.config['output_csv_path']
        print(f"\n💾 步骤 4: 正在将详细结果保存到 '{output_path}'...")
        
        csv_data = [['cluster_id', 'cluster_total_frequency', 'member_count', 'property', 'count']]
        cluster_id_counter = 1
        
        # 处理聚类后形成的簇
        sorted_clusters = sorted(final_clusters, key=lambda x: x['sub_cluster_total_frequency'], reverse=True)
        for cluster in sorted_clusters:
            total_freq = cluster['sub_cluster_total_frequency']
            member_count = len(cluster['sub_cluster_members'])
            for member in cluster['sub_cluster_members']:
                csv_data.append([
                    cluster_id_counter,
                    total_freq,
                    member_count,
                    member,
                    self.term_counts.get(member, 0)
                ])
            cluster_id_counter += 1
            
        # 处理未聚类的项
        others_group = []
        freq_threshold_value = self.config['file_count_for_threshold'] * self.config['frequency_threshold_percent']
        
        for item in self.unclustered_items:
            if item['count'] < freq_threshold_value:
                others_group.append(item)
            else:
                csv_data.append([
                    cluster_id_counter,
                    item['count'],
                    1,
                    item['property'],
                    item['count']
                ])
                cluster_id_counter += 1
        
        if others_group:
            total_others_freq = sum(item['count'] for item in others_group)
            for item in others_group:
                csv_data.append([
                    'Others',
                    total_others_freq,
                    len(others_group),
                    item['property'],
                    item['count']
                ])

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            
        print(f"✅ 结果已成功保存。")
        # 减去未聚类但满足频率阈值的项和'Others'
        new_property_count = cluster_id_counter - 1 - len([item for item in self.unclustered_items if item['count'] >= freq_threshold_value])
        if others_group:
            new_property_count -=1 # 如果有Others组，ID计数器会多一个
        
        print(f"\n🎉 所有流程完成！共定义了 {new_property_count} 个核心属性簇。")


    def run(self):
        """执行完整的聚类分析流程。"""
        self._load_data()
        
        print("\n🧠 正在为所有属性生成语义向量...")
        term_embeddings = self.model.encode(self.terms_to_cluster, convert_to_tensor=True, show_progress_bar=True)
        print(f"✅ 已为 {len(term_embeddings)} 个属性生成向量。")
        
        primary_clusters = self._perform_primary_clustering(term_embeddings)
        final_clusters = self._perform_secondary_clustering(primary_clusters)
        self._save_results_to_csv(final_clusters)


if __name__ == '__main__':
    # ==============================================================================
    # 配置区域
    # ==============================================================================
    CONFIG = {
        # --- 文件路径 ---
        "input_json_path": '/Volumes/mac_outstore/work/3-5-1000-item/extracted_fields_1000_sample.json',
        "output_csv_path": 'property_clusters_output_secondary.csv',
        
        # --- 数据字段 ---
        "field_to_analyze": 'names_frequency', # 可选 'names_frequency' 或 'physical_forms_frequency'
        
        # --- 模型与聚类参数 ---
        "sbert_model": 'all-MiniLM-L6-v2',
        "primary_cluster_threshold": 0.85,    # 第一轮聚类相似度阈值
        "secondary_cluster_threshold": 0.95,  # 第二轮聚类相似度阈值
        "min_community_size": 2,              # 第一轮聚类中，一个簇最少包含的成员数量
        
        # --- 频率筛选参数 ---
        "file_count_for_threshold": 1000,     # 用于计算频率百分比基数的总文件数
        "frequency_threshold_percent": 0.01   # 频率筛选阈值 (例如 0.01 代表 1%)
    }

    # 创建分析器实例并运行
    analyzer = PropertyClusterAnalyzer(CONFIG)
    analyzer.run()
