import numpy as np
from typing import Dict, List, Tuple, Any, Union, Optional

from models import DiseaseProb, MedicalKnowledge

DELTA_IEG_CONVERGENCE = 2  # 收敛次数


class PIMService:
    epsilon = 1e-8

    # ================== I/O, need async ==================
    @classmethod
    async def precise_search(cls, disease_name_list: List[str]) -> Dict[str, float]:
        """
        精确搜索疾病, 获得初始疾病概率分布
        :param disease_name_list: AI 预测的疾病列表
        :return: 符合数据库的疾病概率表 {'D1': 0.3, 'D2':0.4, ...}
        """
        qs = await DiseaseProb.filter(disease__in=disease_name_list).values_list('disease', 'probability')

        matched_disease = dict(qs)
        prob_sum = sum(matched_disease.values())
        matched_disease = {d_name: prob / prob_sum for d_name, prob in matched_disease.items()}
        matched_disease = {k: v for k, v in matched_disease.items() if v >= 1e-8}  # drop prob = 0
        return cls._temperature_scaling(matched_disease)  # 平滑放缩

    @classmethod
    async def knowledge_query(cls, disease_name_list: List[str]) -> List[Dict]:
        """
        根据疾病名查找知识库
        :param disease_name_list: 疾病名列表
        :return: 数据库专业医学知识作为补充 [{'name': 'D1', 'desc': '...'}, ...]
        """
        query_set = await MedicalKnowledge.filter(name__in=disease_name_list).values()
        return query_set

    @classmethod
    async def tableStr(cls, disease_name_list: List[str], symptoms: Dict[str, float]) -> str:
        """转换表格"""
        qs = await MedicalKnowledge.filter(name__in=disease_name_list).values_list("name", "symptom")
        disease_symptom_relation = dict(qs)

        # 表格
        table_str = ["|疾病|已发生的症状|未发生的症状|其他未体现的症状|\n|-|-|-|-|"]

        for d in disease_name_list:
            all_symptoms_of_d = disease_symptom_relation.get(d, [])
            d_s = []
            d_not_s = []
            d_not_sure = []
            for s in all_symptoms_of_d:
                flag = symptoms.get(s, None)
                if flag is True:
                    d_s.append(s)
                elif flag is False:
                    d_not_s.append(s)
                else:
                    d_not_sure.append(s)
            row = f"|{d}|{'、'.join(d_s)}|{'、'.join(d_not_s)}|{'、'.join(d_not_sure)}|"
            table_str.append(row)
        table_str = '\n'.join(table_str)
        return table_str

    # ================== not I/O, not need async ==================
    @classmethod
    def top_k_items(cls, d: Dict[str, float], k: int = 5):
        """字典的 top-k 个键值对"""
        sorted_items = sorted(d.items(), key=lambda x: x[1], reverse=True)  # 按值降序排序

        result = []
        threshold = None

        for i, (key, value) in enumerate(sorted_items):
            if i < k:
                result.append((key, value))
                threshold = value
            elif value == threshold:
                result.append((key, value))
            else:
                break

        return dict(result)

    @classmethod
    def isConvergence(cls, delta_ieg_list: List[float], convergence: int = DELTA_IEG_CONVERGENCE) -> bool:
        """
        delta IEG 收敛, 即连续
        :param delta_ieg_list: (IEG2 - IEG1) / IEG1 的列表 [float, ...]
        :param convergence: 收敛次数
        :return: True / False
        """
        if len(delta_ieg_list) < 2:
            return False
        convergence_num = 0
        i = len(delta_ieg_list) - 2
        while i >= 0 and delta_ieg_list[i] >= delta_ieg_list[i + 1]:
            convergence_num += 1
            i -= 1
        if convergence_num >= convergence:
            return True
        return False

    @classmethod
    def _temperature_scaling(cls, disease_prob: Dict[str, float], temperature=5.0) -> Dict[str, float]:
        """Softmax 想法, 归一化概率"""
        disease_name = list(disease_prob.keys())
        p = np.array(list(disease_prob.values()))

        p_scaled = p ** (1 / temperature)  # [P(D_i)]^T
        p_scaled /= p_scaled.sum()
        return dict(zip(disease_name, p_scaled))
