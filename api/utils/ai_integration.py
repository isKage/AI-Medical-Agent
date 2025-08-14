import asyncio
import os
import re
import sys
import json
import pathlib
from typing import List, Dict, Tuple, Union, Optional

import dashscope
from dashscope import Application
from http import HTTPStatus

import settings
from settings import API_KEY, PIM_01_APP_ID, PIM_02_APP_ID, PIM_03_APP_ID, PSG_APP_ID, CDG_01_APP_ID, CDG_02_APP_ID, PIM_02_APP_ID_PLUS, \
    EXPERIMENT_01_APP_ID, EXPERIMENT_02_APP_ID, EXPERIMENT_03_APP_ID


class AIGenerator:
    @classmethod
    async def _call_application(cls, messages, app_id):
        response = Application.call(
            api_key=API_KEY,
            app_id=app_id,
            messages=messages
        )
        return response

    # ================== I/O & web request, need async ==================
    # ------------------ PIM ------------------
    @classmethod
    async def pim01GeneratePrediction(cls, text: str) -> Optional[List[str]]:
        """
        根据初步描述生成预测疾病列表
        :param text: 患者初步描述
        :return: ['D1', 'D2', ...]
        """
        messages = [
            {
                "role": "user",
                "content":
                    f"初步描述\n{text}\n"
            }
        ]
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, PIM_01_APP_ID)  # 发送请求
                if response.status_code == HTTPStatus.OK:
                    disease_dict = cls._getJsonResponse(response.output.text)
                    return disease_dict.get('diseases', [])
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "PIM01")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    @classmethod
    async def pim02GenerateQuestion(
            cls,
            disease_name_list: List[str],
            symptom_name: str,
            known_symptom_name_list: List[str],
            qa: List[Dict[str, str]]
    ) -> str:
        """
        生成问题
        :param disease_name_list: 相关疾病
        :param symptom_name: 待问症状
        :param known_symptom_name_list: 已经提问过的症状
        :param qa: 问诊对话内容 [] 或 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
        :return: 问题生成 "..."
        """
        messages = [
            {
                "role": "user",
                "content":
                    f"**针对症状：{symptom_name} 提问**\n"
                    f"已经提问过的症状：{known_symptom_name_list}\n"
                    f"可能罹患的几种疾病：{disease_name_list}\n"
                    f"之前的对话内容：\n{qa}\n"
            }
        ]
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, PIM_02_APP_ID)  # 发送请求
                if response.status_code == HTTPStatus.OK:
                    return response.output.text.strip()
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "PIM02")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    @classmethod
    async def pim02GenerateQuestionPLUS(
            cls,
            disease_name_list: List[str],
            symptom_name: str,
            known_symptom_name_list: List[str],
            qa: List[Dict[str, str]]
    ) -> Dict[str, str | bool]:
        """
        生成问题 PLUS
        :param disease_name_list: 相关疾病
        :param symptom_name: 待问症状
        :param known_symptom_name_list: 已经提问过的症状
        :param qa: 问诊对话内容 [] 或 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]
        :return: 问题生成 {"skip": True | False, "question": "..."}
        """
        messages = [
            {
                "role": "user",
                "content":
                    f"针对症状：{symptom_name} 提问\n"
                    f"已经提问过的症状：{known_symptom_name_list}\n"
                    f"可能罹患的几种疾病：{disease_name_list}\n"
                    f"之前的对话内容：\n{qa}\n"
            }
        ]
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, PIM_02_APP_ID_PLUS)  # 发送请求
                if response.status_code == HTTPStatus.OK:
                    skip_question_dict = cls._getJsonResponse(response.output.text)
                    return skip_question_dict
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "PIM02")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    @classmethod
    async def pim03ExtractSymptom(cls, symptom_name: str, question: str, answer: str) -> Dict[str, bool]:
        """
        判断患者回答
        :param symptom_name: 被提问的症状名 ""
        :param question: 系统提问 ""
        :param answer: 患者回答 ""
        :return: {"is_related": Bool, "symptom": Bool | None}
        """
        messages = [
            {
                "role": "user",
                "content":
                    f"针对症状：{symptom_name} 提问\n"
                    f"医生提问：{question}\n"
                    f"患者回答：{answer}\n"
            }
        ]
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, PIM_03_APP_ID)
                if response.status_code == HTTPStatus.OK:
                    symptom_dict = cls._getJsonResponse(response.output.text)
                    return symptom_dict
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "PIM03")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    # ------------------ PSG ------------------
    @classmethod
    async def psg01GenerateReport(
            cls,
            disease_name: str,
            qa_messages: List[Dict[str, str]],
            symptoms: Dict[str, bool | None | str],
            patient_addition: str,
            knowledge_addition: Dict[str, List[str] | str],
    ) -> str:
        """
        PSG 患者报告
        :param disease_name: 可能疾病 "..."
        :param qa_messages: 问诊对话内容 [{'role': 'system', 'content': '...'}, {'role': 'user', 'content': '...'}, ...]
        :param symptoms: 是否出现某些症状的字典 {'S1': True, 'S2': False, 'S3': None}
        :param patient_addition: 患者补充的其他信息 "..."
        :param knowledge_addition: 有关疾病的补充信息 {'name': 'D1', 'desc': '...', 'category': ['...', ...], ...}
        :return: 患者报告 "..."
        """
        # 用户信息
        user_content = (f"- 可能疾病：{disease_name}\n"
                        f"- 问诊对话内容：\n{qa_messages}\n"
                        f"- 是否出现某些症状的字典：\n{symptoms}\n"
                        f"- 患者补充的其他信息：{patient_addition}\n"
                        f"- 有关疾病的补充信息：\n{knowledge_addition}\n")
        messages = [
            {
                "role": "user",
                "content": user_content
            },
        ]
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, PSG_APP_ID)  # 请求
                if response.status_code == HTTPStatus.OK:  # successful
                    return response.output.text
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "PSG01")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    # ------------------ CDG ------------------
    @classmethod
    async def cdg01GenerateInitial(
            cls,
            disease_prob_dict: Dict[str, float],
            qa_messages: List[Dict[str, str]],
            symptoms: Dict[str, bool | None | str],
            patient_addition: str
    ) -> Dict[str, str]:
        """
        生成初步疾病诊断和推理
        :param disease_prob_dict: top-k 疾病概率 {'D1': 0.3, 'D2': 0.2, 'D3': 0.1}
        :param qa_messages: 问诊对话内容 [{'role': 'system', 'content': '...'}, {'role': 'user', 'content': '...'}, ...]
        :param symptoms: 是否出现某些症状的字典 {'S1': True, 'S2': False, 'S3': None}
        :param patient_addition: 患者补充的其他信息 "..."
        :return: Dict {"disease": "最可能的疾病名", "reason": "诊断依据和推理过程"}
        """
        disease_name_list = list(disease_prob_dict.keys())
        user_content = (f"- 待选疾病列表：{disease_name_list}\n"
                        f"- 问诊对话内容：\n{qa_messages}\n"
                        f"- 是否出现某些症状的字典：\n{symptoms}\n"
                        f"- 患者提供的补充信息：{patient_addition}\n"
                        f"- 其他（推测患者患各个疾病的可能概率）：{disease_prob_dict}")
        messages = [
            {"role": "user", "content": user_content}
        ]
        disease_and_reason = {}  # 备选 {"disease": "最可能的疾病名", "reason": "诊断依据和推理过程"}
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, CDG_01_APP_ID)
                if response.status_code == HTTPStatus.OK:
                    disease_and_reason = cls._getJsonResponse(response.output.text)  # 请求并解析
                    break
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "CDG01")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e
        # 验证 disease_opt -> disease_opt_dict: {'D1': prob, ...}
        selected_disease = disease_and_reason.get("disease", [])
        disease_opt_dict = {}
        for d in selected_disease:
            if d in disease_name_list:
                disease_opt_dict[d] = disease_prob_dict[d]
        if len(disease_opt_dict) == 0:
            disease_opt_dict = disease_prob_dict
        disease_and_reason["disease"] = disease_opt_dict
        return disease_and_reason

    @classmethod
    async def cdg02GenerateSOAP(
            cls,
            disease_prob_dict: Dict[str, float],
            disease_opt_dict: Dict[str, float],
            initial_note: str,
            qa_messages: List[Dict[str, str]],
            symptoms: Dict[str, bool | None | str],
            patient_addition: str,
            knowledge_addition_list: List[Dict[str, str | List[str]]],
            table_str: str = ""
    ) -> str:
        """
        SOAP 病历生成
        :param disease_prob_dict: top-k 疾病概率 {'D1': 0.3, 'D2': 0.2, 'D3': 0.1}
        :param disease_opt_dict: 最可能疾病字典 {'D1': 0.3, 'D2': 0.2, 'D3': 0.1}
        :param initial_note: 初步诊断推理 "..."
        :param qa_messages: 问诊对话内容 [{'role': 'system', 'content': '...'}, {'role': 'user', 'content': '...'}, ...]
        :param symptoms: 是否出现某些症状的字典 {'S1': True, 'S2': False, 'S3': None}
        :param patient_addition: 患者补充的其他信息 "..."
        :param knowledge_addition_list: top-k 疾病专业知识 [{'name': 'D1', 'desc': '...', 'category': ['...', ...], ...}, ...]
        :param table_str: 症状表格 markdown 格式 |table|table|
        :return: SOAP 病历内容 markdown 格式 "..."
        """
        disease_name_list = list(disease_prob_dict.keys())
        user_content = (f"- 可能疾病列表：{disease_name_list}\n"
                        f"- 最可能疾病：{disease_opt_dict}\n"
                        f"- 初步诊断依据和推理过程：\n{initial_note}\n"
                        f"- 问诊对话内容：\n{qa_messages}\n"
                        f"- 是否出现某些症状的字典：\n{symptoms}\n"
                        f"- 患者提供的补充信息：{patient_addition}\n"
                        f"- “疾病-症状”的诊断表格，可根据“问诊对话内容”和“患者提供的补充信息”作适当修改。\n{table_str}\n"
                        f"- 有关疾病的专业知识：\n{knowledge_addition_list}")
        messages = [
            {"role": "user", "content": user_content}
        ]

        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, CDG_02_APP_ID)
                if response.status_code == HTTPStatus.OK:
                    return response.output.text
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "CDG02")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    # ------------------ EXPERIMENT ------------------
    @classmethod
    async def experiment01ExtractSymptom(
            cls,
            desc: str,
            real_symptom_dict: Dict[str, str | bool | None],
            required_symptom_list: List[str]
    ) -> Dict[str, bool | None]:
        """
        根据 real_symptom_dict 生成本系统的症状字典
        :param desc: 患者主诉
        :param real_symptom_dict: 真实症状发生与否字典 {'S1': True, ...} or {'S1': '是'}
        :param required_symptom_list: 需要询问的症状名列表 ['', ...]
        :return: 需要询问的症状发生与否字典 {'SA': True, 'SB': False, 'SC': None}
        """
        # 检查 real_symptom_dict
        symptom_ori = {}
        v_list = list(real_symptom_dict.values())
        if isinstance(v_list[0], bool):
            # 转换格式
            for k, v in real_symptom_dict.items():
                if v is True:
                    symptom_ori[k] = "是"
                elif v is False:
                    symptom_ori[k] = "否"
                else:
                    symptom_ori[k] = "尚不清楚"
        else:
            symptom_ori = real_symptom_dict

        user_content = (f"【提供的信息】\n患者主诉: **小儿疾病，患者为儿童。**{desc}\n"
                        f"真实的症状发生与否字典:\n{symptom_ori}\n"
                        f"\n【医生询问的症状】\n{required_symptom_list}")

        messages = [
            {"role": "user", "content": user_content}
        ]
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, EXPERIMENT_01_APP_ID)
                if response.status_code == HTTPStatus.OK:
                    symptom_dict = cls._getJsonResponse(response.output.text)
                    return symptom_dict
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "EXPERIMENT01")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    @classmethod
    async def experiment02SelectDisease(
            cls,
            desc: str,
            symptom_dict: Dict[str, str | bool | None],
            disease_prob_dict: Dict[str, float]
    ) -> Dict[str, float]:
        """
        预测前 k 个疾病
        :param desc: 初步描述 "..."
        :param symptom_dict: 症状 {'S1': True, ...} or {'S1': '是'}
        :param disease_prob_dict: 疾病概率 {'D1': 0.3, 'D2': 0.4, ...}
        :return: {'D1': 0.3, 'D2': 0.4, ...} k 个
        """
        symptoms = {}
        v_list = list(symptom_dict.values())
        if isinstance(v_list[0], bool):
            # 转换格式
            for k, v in symptom_dict.items():
                if v is True:
                    symptoms[k] = "是"
                elif v is False:
                    symptoms[k] = "否"
                else:
                    symptoms[k] = "尚不清楚"
        else:
            symptoms = symptom_dict

        user_content = (f"患者主诉: **小儿疾病，患者为儿童。**{desc}\n"
                        f"症状发生与否字典: \n{symptoms}\n"
                        f"预测的疾病概率: \n{disease_prob_dict}\n")
        messages = [
            {"role": "user", "content": user_content}
        ]
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, EXPERIMENT_02_APP_ID)
                if response.status_code == HTTPStatus.OK:
                    disease_name_list_dict = cls._getJsonResponse(response.output.text)
                    disease_name_list = disease_name_list_dict.get("disease", [])
                    new_disease_prob_dict = {}
                    for d_name in disease_name_list:
                        if d_name in disease_prob_dict:
                            new_disease_prob_dict[d_name] = disease_prob_dict[d_name]
                    if len(new_disease_prob_dict) == 0:
                        return disease_prob_dict
                    return new_disease_prob_dict
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "EXPERIMENT02")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    @classmethod
    async def experiment03PredictDiseaseOnly(
            cls,
            desc: str,
            symptom_dict: Dict[str, str | bool | None],
    ) -> List[str]:
        """
        预测前 k 个疾病
        :param desc: 初步描述 "..."
        :param symptom_dict: 症状 {'S1': True, ...} or {'S1': '是'}
        :return: ['D1', 'D2', 'D3', 'D4']
        """
        symptoms = {}
        v_list = list(symptom_dict.values())
        if isinstance(v_list[0], bool):
            # 转换格式
            for k, v in symptom_dict.items():
                if v is True:
                    symptoms[k] = "是"
                elif v is False:
                    symptoms[k] = "否"
                else:
                    symptoms[k] = "尚不清楚"
        else:
            symptoms = symptom_dict

        user_content = (f"患者主诉: **小儿疾病，患者为儿童。**{desc}\n"
                        f"症状发生与否字典: \n{symptoms}\n")
        messages = [
            {"role": "user", "content": user_content}
        ]
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await cls._call_application(messages, EXPERIMENT_03_APP_ID)
                if response.status_code == HTTPStatus.OK:
                    disease_name_list_dict = cls._getJsonResponse(response.output.text)
                    _disease_name_list = disease_name_list_dict.get("disease", [])
                    # disease_pred_list = []
                    # for d in _disease_name_list:
                    #     if d in disease_name_list:
                    #         disease_pred_list.append(d)
                    disease_pred_list = _disease_name_list
                    return disease_pred_list
                else:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待 0.5 秒
                        continue
                    error_info = cls._error_info_http(response, "EXPERIMENT03")
                    raise Exception(error_info + f" (Attempt {attempt + 1})")
            except Exception as e:
                raise e

    # ================== not I/O not async ==================
    @classmethod
    def _getJsonResponse(cls, content: str) -> dict:
        """JSON 解析"""
        # 寻找 Markdown 的 JSON 代码块
        match = re.search(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
        json_str = match.group(1) if match else content.strip()
        # 尝试解析
        try:
            res = json.loads(json_str)
            return res
        except Exception as e:
            raise e

    @classmethod
    def _error_info_http(cls, response, title: str = "NOK"):
        """API 请求失败的错误"""
        return f"[{title}] HTTP: {response.status_code}, ID: {response.request_id}, Code: {response.code}, Message: {response.message}"
