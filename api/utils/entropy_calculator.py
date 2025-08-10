import os
import sys
import pathlib

import numpy
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Union, Optional

from models import DiseaseProb, MedicalKnowledge, SymptomProb


class EntropyCalculator:
    epsilon = 1e-8  # 用于数值稳定的小常数
    MIN_PROB_THRESHOLD = 0.001  # 最小保留概率

    # ======================= I/O 操作 异步 =======================

    @classmethod
    async def calculateIEG(
            cls,
            disease_prob_dict: Dict[str, float],
            known_symptom_dict: Optional[Dict[str, bool | None]] = None,
    ) -> Dict[str, float | numpy.float16]:
        """
        计算各个症状对应的 IEG 并返回最优的症状 & IEG 值
        :param disease_prob_dict: 最新疾病概率字典 {'D1': 0.1, 'D2': 0.4, ...}
        :param known_symptom_dict: 已获得的症状字典 {'S1': True, 'S2': False, 'S3': None}
        :return: {'S5': 0.1332, 'S4': 0.1132, ...}
        """
        # Step 1: H0
        disease_prob_list = list(disease_prob_dict.values())
        H0 = cls._H(disease_prob_list)

        # Step 2: 获取 Disease & Symptom 的信息
        _, symptom_prob_dict, sd_relation = await cls.SDInfo(disease_prob_dict, known_symptom_dict)

        # Step 3: 获取 Symptom-Disease Matrix
        disease_name_list = list(disease_prob_dict.keys())
        symptom_name_list = list(symptom_prob_dict.keys())
        sd_df = cls.SDMatrix(disease_name_list, symptom_name_list, sd_relation)
        sd_matrix = sd_df.values.astype(np.float16)

        # Step 4: 归一化/标准化
        p_s = np.array(list(symptom_prob_dict.values()), dtype=np.float16)
        p_s = cls._safe_normalize(p_s)  # P(S_k)

        p_d = np.array(disease_prob_list, np.float16)
        p_d = cls._safe_normalize(p_d)  # P(D_l)

        # Step 5: P(S_k | D_l)
        after_mul_p_s = sd_matrix * p_s
        row_sum_matrix = after_mul_p_s.sum(axis=1, keepdims=True)  # shape = (N_S, 1)
        row_sum_matrix = np.where(row_sum_matrix == 0, cls.epsilon, row_sum_matrix)  # 防止除以 0
        p_s_d = after_mul_p_s / row_sum_matrix  # P(S_k | D_l) shape = (N, N_S)

        # Step 6.1: P(D_l | S_k)
        p_d_s = cls._mask_calculate_bayes(sd_matrix == 1, p_s_d, p_d, p_s)

        # Step 6.2: P(D_l | not S_k)
        p_d_not_s = cls._mask_calculate_bayes(sd_matrix == 1, 1 - p_s_d, p_d, p_s)

        # Step 7: 计算各个症状的 IEG
        symptom_IEG = {}
        H_occ = {}
        H_nok = {}
        for i, s in enumerate(symptom_name_list):
            H_occ[s] = cls._H(p_d_s[:, i], sd_matrix[:, i] > cls.epsilon)
            H_nok[s] = cls._H(p_d_not_s[:, i], sd_matrix[:, i] > cls.epsilon)
        for i, symptom_name in enumerate(symptom_name_list):
            # H_cond = H_occ[symptom_name] * p_s[i] + H_nok[symptom_name] * (1 - p_s[i])
            # H_cond = H_occ[symptom_name] + H_nok[symptom_name]
            symptom_IEG[symptom_name] = min(
                float(abs(H0 - H_occ[symptom_name]) / max(abs(H0), cls.epsilon)),
                float(abs(H0 - H_nok[symptom_name]) / max(abs(H0), cls.epsilon))
            )
        return symptom_IEG

    @classmethod
    async def updateDiseaseProb(
            cls,
            disease_prob_dict: Dict[str, float],
            new_known_symptom_dict: Optional[Dict[str, bool | None]] = None,
            known_symptom_dict: Optional[Dict[str, bool | None]] = None,
    ):
        """
        更新疾病概率
        :param disease_prob_dict: 当前疾病概率 (待更新) {'D1': 0.1, 'D2': 0.4, ...}
        :param new_known_symptom_dict: 最新获取的症状信息 {'S6': True | False | None}
        :param known_symptom_dict: 当前疾病概率 (待更新) {'S1': True, 'S2': False, 'S3': None}
        :return: 最新的疾病概率 {'D1': 0.1, 'D2': 0.4, ...}
        """
        # flag = list(new_known_symptom_dict.values())[0]
        # 最简单情况, 若为 None 则不更新
        # if flag is None:
        #     return disease_prob_dict

        # Step 1: old 疾病概率
        disease_prob_list = list(disease_prob_dict.values())

        # Step 2: 获取 Disease & Symptom 的信息
        _, symptom_prob_dict, sd_relation = await cls.SDInfo(disease_prob_dict)

        # Step 3: 获取 Symptom-Disease Matrix
        disease_name_list = list(disease_prob_dict.keys())
        symptom_name_list = list(symptom_prob_dict.keys())
        sd_df = cls.SDMatrix(disease_name_list, symptom_name_list, sd_relation)
        sd_matrix = sd_df.values.astype(np.float16)

        # Step 4: 归一化/标准化
        p_s = np.array(list(symptom_prob_dict.values()), dtype=np.float16)
        p_s = cls._safe_normalize(p_s)  # P(S_k)

        p_d = np.array(disease_prob_list, np.float16)
        p_d = cls._safe_normalize(p_d)  # P(D_l)

        # Step 5: P(S_k | D_l)
        after_mul_p_s = sd_matrix * p_s
        row_sum_matrix = after_mul_p_s.sum(axis=1, keepdims=True)  # shape = (N_S, 1)
        row_sum_matrix = np.where(row_sum_matrix == 0, cls.epsilon, row_sum_matrix)  # 防止除以 0
        p_s_d = after_mul_p_s / row_sum_matrix  # P(S_k | D_l) shape = (N, N_S)

        # Step 6.1: P(D_l | S_k)
        # p_d_s = cls._mask_calculate_bayes(sd_matrix == 1, p_s_d, p_d, p_s)

        # Step 6.2: P(D_l | not S_k)
        # p_d_not_s = cls._mask_calculate_bayes(sd_matrix == 1, 1 - p_s_d, p_d, p_s)

        # Step 7: 返回最新疾病概率
        if new_known_symptom_dict is not None:
            (new_symptom_name, flag), = new_known_symptom_dict.items()
            known_symptom_dict[new_symptom_name] = flag

        SetTrue = []
        SetFalse = []
        for s_name, s_flag in known_symptom_dict.items():
            col_idx = sd_df.columns.get_loc(s_name)
            if s_flag is True:
                SetTrue.append(col_idx)
            elif s_flag is False:
                SetFalse.append(col_idx)
            else:
                continue

        new_disease_prob_dict = {}
        for i, d_name in enumerate(disease_name_list):
            # a. 需要计算的 Symptom: True
            SetTrue_ = []
            for s_idx in SetTrue:
                if sd_matrix[i, s_idx] == 1:
                    SetTrue_.append(s_idx)
            # b. 需要计算的 Symptom: False
            SetFalse_ = []
            for s_idx in SetFalse:
                if sd_matrix[i, s_idx] == 1:
                    SetFalse_.append(s_idx)

            prod = np.prod(np.clip(p_s_d[i, SetTrue_], cls.MIN_PROB_THRESHOLD, None))
            prod_not = np.prod(np.clip((1 - p_s_d)[i, SetFalse_], cls.MIN_PROB_THRESHOLD, None))
            p_d_i = p_d[i] * prod * prod_not
            new_disease_prob_dict[d_name] = float(p_d_i)
        sum_p = sum(list(new_disease_prob_dict.values()))
        if sum_p < cls.epsilon:
            sum_p = 1
            updated_disease_prob = {k: (v + cls.MIN_PROB_THRESHOLD) / sum_p for k, v in new_disease_prob_dict.items()}
        else:
            updated_disease_prob = {k: v / sum_p for k, v in new_disease_prob_dict.items()}
        return cls._temperature_scaling(updated_disease_prob, temperature=5.0)

    @classmethod
    async def SDInfo(
            cls,
            diseases: Union[List[str], Dict[str, float]],
            known_symptom_dict: Optional[Dict[str, bool | None]] = None,
    ) -> Tuple[Dict[str, float] | None, Dict[str, float], Dict[str, List[str]]]:
        """
        根据疾病信息合并全部症状, 返回 "疾病-症状" 信息 (未归一化)
        :param diseases: 疾病信息 ['D1', 'D2', ...] 或者 {'D1': 0.1, 'D2': 0.4, ...}
        :param known_symptom_dict: 已获取的症状 {'S1': True, 'S2': False, 'S3': None}
        :return ({'D1': 0.1, 'D2': 0.4, ...}, {'S1': 0.43, 'S2': 0.01, ...}, {'D1': ['S1', ...], ...})
        """
        # part 1: 疾病概率
        # diseases_prob_dict = await cls.getDiseaseProbDict(diseases)

        # part 2: 疾病-症状关系表 & 症状概率
        symptom_prob_dict, sd_relation = await cls.getSymptomProbDict_SDRelation(diseases, known_symptom_dict)

        return None, symptom_prob_dict, sd_relation

    @classmethod
    async def getSymptomProbDict_SDRelation(
            cls,
            diseases: Union[List[str], Dict[str, float]],
            known_symptom_dict: Optional[Dict[str, bool | None]] = None,
    ) -> Tuple[Dict[str, float], Dict[str, List[str]]]:
        """获取疾病对应的所有症状 & 症状概率字典"""
        if known_symptom_dict is None:
            known_symptom_dict = {}
        known_symptom_list = list(known_symptom_dict.keys())

        # step 1: 疾病-症状关系表
        sd_relation = {}
        disease_name_list = list(diseases.keys()) if isinstance(diseases, dict) else diseases
        symptom_of_one_disease_dict = await MedicalKnowledge.filter(name__in=disease_name_list).values("name", "symptom")
        # [{'name': 'xxx', 'symptom': []}, {'name': 'xxx', 'symptom': []}, ...]
        for item in symptom_of_one_disease_dict:
            _disease_name = item.get("name")
            _symptom_list = item.get("symptom")
            _symptom_list = [_symptom for _symptom in _symptom_list if _symptom not in known_symptom_list]
            sd_relation[_disease_name] = _symptom_list

        # step 2: 获取所有症状
        symptom_set = set()
        for _, __symptom_list in sd_relation.items():
            for __symptom in __symptom_list:
                symptom_set.add(__symptom)
        symptom_list = list(symptom_set)

        # step 3: 症状概率
        symptom_prob_dict_list = await SymptomProb.filter(symptom__in=symptom_list).values("symptom", "probability")
        # [{'symptom': 'xxx', 'probability': 0.3}, {'symptom': 'xxx', 'probability': 0.3}, ...]
        symptom_prob_dict = {}
        for item in symptom_prob_dict_list:
            _symptom_name = item.get("symptom")
            _symptom_prob = item.get("probability")
            symptom_prob_dict[_symptom_name] = _symptom_prob

        return symptom_prob_dict, sd_relation

    # ======================= 无 I/O 操作 无异步 =======================
    @classmethod
    def max_ieg(cls, symptom_IEG: Dict[str, float]) -> Tuple[str, float]:
        """字典值最大的键 & 值"""
        k_max = max(symptom_IEG, key=symptom_IEG.get)
        v_max = symptom_IEG[k_max]
        return k_max, v_max

    @classmethod
    def SDMatrix(
            cls,
            disease_name_list: List[str],
            symptom_name_list: List[str],
            sd_relation: Dict[str, List[str]]
    ) -> pd.DataFrame:
        """
        疾病-症状
        :param disease_name_list: 疾病名列表 ['D1', 'D2', ...]
        :param symptom_name_list: 症状名列表 ['S1', 'S2', ...]
        :param sd_relation: 疾病-症状关系表 {'D1': ['S1', 'S2'], 'D2': ['S1', 'S2'], ...}
        :return:
            SDMatrix: (len(disease_name_list), len(symptom_name_list)) 1 代表当前疾病有当前症状, 否则为 0
        """
        # 创建索引映射
        disease_to_index = {d: i for i, d in enumerate(disease_name_list)}
        symptom_to_index = {s: i for i, s in enumerate(symptom_name_list)}

        SDMatrix = np.zeros((len(disease_name_list), len(symptom_name_list)), dtype=int)
        for disease, symptoms in sd_relation.items():
            if disease in disease_to_index:
                disease_idx = disease_to_index[disease]
                for symptom in symptoms:
                    if symptom in symptom_to_index:
                        symptom_idx = symptom_to_index[symptom]
                        SDMatrix[disease_idx, symptom_idx] = 1
        SDDataFrame = pd.DataFrame(SDMatrix, index=disease_name_list, columns=symptom_name_list)
        return SDDataFrame

    @classmethod
    def _H(cls, p: Union[List[float], numpy.ndarray], mask=None) -> Union[float, numpy.float16]:
        """计算熵"""
        if isinstance(p, list):
            p = numpy.array(p, numpy.float64)

        # [NaN, inf, 负值] -> 0
        p = np.nan_to_num(p, nan=0.0, posinf=0.0, neginf=0.0)

        if mask is None:
            mask = p > 0  # only consider p > 0

        p = np.clip(p, cls.MIN_PROB_THRESHOLD, 1.0)
        return -np.sum(p[mask] * np.log(p[mask] + cls.epsilon))

    @classmethod
    def _safe_normalize(cls, vec: np.ndarray) -> np.ndarray:
        """对一维向量进行安全归一化"""
        vec = np.nan_to_num(vec, nan=0.0, posinf=1.0, neginf=0.0)
        vec = np.clip(vec, 0.0, None)  # 负值归 0
        total = np.sum(vec)
        if total <= 0:
            return np.zeros_like(vec)
        return vec / total

    @classmethod
    def _mask_calculate_bayes(cls, mask, pBunderA, pA, pB):
        """P(B | A) = exp(log(pAunderB) + log(pB) - log(pA))"""
        rows, cols = np.where(mask)
        log_pAunderB = np.zeros_like(pBunderA)

        safe_pBunderA = np.clip(pBunderA, cls.MIN_PROB_THRESHOLD, None)
        safe_pA = np.clip(pA, cls.MIN_PROB_THRESHOLD, None)
        safe_pB = np.clip(pB, cls.MIN_PROB_THRESHOLD, None)

        log_pAunderB[rows, cols] = (
                np.log(safe_pBunderA[rows, cols]) +
                np.log(safe_pA[rows]) -
                np.log(safe_pB[cols])
        )

        # max_log_p_d_s = np.max(log_pAunderB, axis=1, keepdims=True)
        # pAunderB = np.where(mask, np.exp(log_pAunderB - max_log_p_d_s), 0.0)
        pAunderB = np.where(mask, np.exp(log_pAunderB), 0.0)
        pAunderB = pAunderB / np.sum(pAunderB)

        return pAunderB

    @classmethod
    def _temperature_scaling(cls, disease_prob: Dict[str, float], temperature=5.0) -> Dict[str, float]:
        """Softmax 想法, 归一化概率"""
        disease_name = list(disease_prob.keys())
        p = np.array(list(disease_prob.values()))

        p_scaled = p ** (1 / temperature)  # [P(D_i)]^(1/T)
        p_scaled /= p_scaled.sum()
        return dict(zip(disease_name, p_scaled))
