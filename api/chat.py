import os
import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from tortoise.exceptions import DoesNotExist
from fastapi.templating import Jinja2Templates

from models import PIM, CDG, PSG
from .utils import PIMService, EntropyCalculator, AIGenerator

api_chat = APIRouter()
templates_path = os.path.join(pathlib.Path(__file__).parent.parent, "templates")
templates = Jinja2Templates(directory=templates_path)

DELTA_IEG_CONVERGENCE = 2  # 收敛次数
ROUND_MAX = 12  # 对话次数限制
ROUND_MIN = 6  # 对话次数限制
MAX_UNRELATED_RETRIES = 2  # 无关回答最多重复次数


@api_chat.get("/")
async def redirectToNew():
    """重定向至 /chat/new"""
    return RedirectResponse(url="/chat/new")


@api_chat.get("/{uid}")
async def getChat(request: Request, uid: str, no_sense: int = 0):
    """
    GET 请求, 返回问诊界面
    :param request: 请求对象
    :param uid: 唯一标识符
    :param no_sense: 初次描述是否合适
    :return: HTML 网页响应
    """
    if uid == "new":
        return templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
                "messages": [],
                "uid": uid,
                "no_sense": no_sense,
            }
        )

    # 数据库搜索
    try:
        pim = await PIM.get(uid=uid)
        return templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
                "messages": pim.qa_messages,
                "uid": uid,
                "show": 1,
            }
        )
    except DoesNotExist:
        return RedirectResponse(url="/chat/new")


@api_chat.post("/{uid}")
async def sendChat(uid: str, message: str = Form(...)):
    """
    POST 请求, 核心: 异步处理 发送请求 生成问题 获取症状 更新概率 判断结束
    :param uid: 唯一标识符
    :param message: 患者的填写/回答
    :return: JSON 格式返回
    """
    """发送消息的API端点"""
    # Part 1: 第一次发送
    if uid == "new":
        # 1. 不能为空
        if message.strip() == "":
            return JSONResponse({
                "status": "redirect",
                "redirect_url": "/chat/new?no_sense=1"
            })

        # 2. 第一次问诊记录
        """PIM01 预测疾病列表"""
        disease_name_list = await AIGenerator.pim01GeneratePrediction(message)
        # 2.1 信息不足
        if len(disease_name_list) == 0:
            return JSONResponse({
                "status": "redirect",
                "redirect_url": "/chat/new?no_sense=1"
            })
        # 2.2 搜索数据库
        disease_prob_dict = await PIMService.precise_search(disease_name_list)  # {'D1': 0.1, ...}
        disease_name_list = list(disease_prob_dict.keys())

        pim = await PIM.create()  # 创建用户
        uid = pim.uid  # 获取 uid

        # 添加疾病概率
        pim.diseases = [disease_prob_dict]

        first_sys_message = {"role": "system", "content": "你好！我是AI医生助手。请您尽可能具体详细地描述一下您的症状。"}
        user_message = {"role": "user", "content": message}
        qa_messages = [first_sys_message, user_message]

        # 计算 IEG
        symptom_IEG = await EntropyCalculator.calculateIEG(disease_prob_dict)
        pim.ieg = [symptom_IEG]  # 添加 IEG

        symptom_name, _ = EntropyCalculator.max_ieg(symptom_IEG)
        pim.symptom_opt = symptom_name

        """ PIM02 生成问题"""
        question = await AIGenerator.pim02GenerateQuestion(disease_name_list, symptom_name, [], qa_messages)

        ai_message = {"role": "system", "content": question}
        qa_messages.append(ai_message)

        # 添加问诊对话
        pim.qa_messages = qa_messages

        await pim.save()

        return JSONResponse({
            "status": "redirect",
            "user_message": user_message,
            "ai_message": ai_message,
            "redirect_url": f"/chat/{uid}"
        })

    if message.strip() == "":  # 不能为空
        return JSONResponse({
            "status": "redirect",
            "redirect_url": f"/chat/{uid}"
        })

    # Part 2: 后续问答
    try:
        pim = await PIM.get(uid=uid)  # 数据库搜索
    except DoesNotExist:
        return JSONResponse({
            "status": "redirect",
            "redirect_url": "/chat/new"
        })

    # symptom_name, _ = EntropyCalculator.max_ieg(pim.ieg[-1])
    symptom_name = pim.symptom_opt

    # 问诊对话内容
    user_message = {"role": "user", "content": message}  # 添加用户消息到历史记录
    qa_messages = pim.qa_messages

    question = "..."
    for qa_idx in range(len(qa_messages) - 1, -1, -1):
        if qa_messages[qa_idx].get("role") == "system":
            question = qa_messages[qa_idx].get("content")
            break

    """PIM03 判断症状是否发生"""
    pim03 = await AIGenerator.pim03ExtractSymptom(symptom_name, question, message)  # {"is_related": Bool, "symptom": Bool | None}
    symptom_TFN = pim03.get("symptom", None)

    symbol = 0
    # 若不相关
    if not pim03.get("is_related", False):
        count = pim.unrelated_count + 1  # 计数加一
        pim.unrelated_count = count

        if count <= MAX_UNRELATED_RETRIES:  # 可以重新回答
            pim.is_related = False  # 标记不相关
            # 更新最后一条患者回答
            if qa_messages[-1].get("role") == "system":
                qa_messages.append(user_message)
            else:
                qa_messages[-1] = user_message
            await pim.save()

            # 重新回答
            return JSONResponse({
                "status": "success",
                "user_message": user_message,
                "ai_message": {"role": "system", "content": question},
                "count": count
            })
        else:  # 超过次数, 跳过当前问题
            pim.unrelated_count = 0
            pim.is_related = True
            symbol = 1

            # 更新最后一条患者回答
            if qa_messages[-1].get("role") == "system":
                qa_messages.append(user_message)
            else:
                qa_messages[-1] = user_message

            symptom_TFN = None  # 跳过, 当前症状为 None

    if pim.is_related is False:
        qa_messages[-1] = user_message
        # 相关回答, 重置
        pim.unrelated_count = 0
        pim.is_related = True
    elif pim.is_related is True and symbol == 1:
        qa_messages[-1] = user_message
    else:
        qa_messages.append(user_message)

    symptom_dict = pim.symptoms  # 原始症状是否字典 {'S1': True, ...} or {}

    await pim.save()  # 结束前先保存

    """结束标志 1 """
    if len(symptom_dict) >= len(pim.ieg[0]):  # 症状询问完毕
        return JSONResponse({
            "status": "endChat"
        })
    if len(qa_messages) / 2 > ROUND_MAX:  # 轮次要求
        return JSONResponse({
            "status": "endChat"
        })

    new_known_symptom_dict = {symptom_name: symptom_TFN}  # 新症状 {'S2': False}

    # origin_disease_prob = await PIMService.precise_search(list(pim.diseases[-1].keys()))
    # disease_prob_dict = await EntropyCalculator.updateDiseaseProb(origin_disease_prob, new_known_symptom_dict, symptom_dict)
    latest_disease_prob_dict = await PIM.get(uid=uid).values("diseases")
    latest_disease_prob_dict = latest_disease_prob_dict.get("diseases")[-1]
    disease_prob_dict = await EntropyCalculator.updateDiseaseProbV2(latest_disease_prob_dict, new_known_symptom_dict, symptom_dict)

    pim.diseases.append(disease_prob_dict)  # 新疾病概率
    symptom_dict[symptom_name] = symptom_TFN  # 新症状是否字典, 未保存入数据库

    # 计算最新 IEG
    symptom_IEG = await EntropyCalculator.calculateIEG(disease_prob_dict, symptom_dict)
    symptom_name, max_ieg_value = EntropyCalculator.max_ieg(symptom_IEG)
    pim.symptom_opt = symptom_name  # 更新 max_ieg symptom
    ieg_temp = pim.ieg
    ieg_temp.append(symptom_IEG)

    delta_ieg_list = pim.delta_ieg
    if len(ieg_temp) > 1:
        _, v1 = EntropyCalculator.max_ieg(ieg_temp[-2])
        _, v2 = EntropyCalculator.max_ieg(ieg_temp[-1])
        delta_ieg_list.append(abs((v1 - v2) / v1))

    await pim.save()  # 结束前先保存

    # """ PIM02 生成问题"""
    # disease_name_list = list(disease_prob_dict.keys())
    # known_symptom_name_list = list(symptom_dict.keys())
    # question = await AIGenerator.pim02GenerateQuestion(disease_name_list, symptom_name, known_symptom_name_list, qa_messages)
    """ PIM02 生成问题"""
    while 1:
        disease_name_list = list(disease_prob_dict.keys())
        known_symptom_name_list = list(symptom_dict.keys())
        skip_question = await AIGenerator.pim02GenerateQuestionPLUS(disease_name_list, symptom_name, known_symptom_name_list, qa_messages)
        f = skip_question.get('skip', True)
        # 测试 debug
        if symptom_name in ["食欲不振", "面色苍白", "血压下降"]:
            f = True
        if not f:
            break
        symptom_dict[symptom_name] = None  # 跳过 symptom_name
        # 重新计算
        symptom_IEG = await EntropyCalculator.calculateIEG(disease_prob_dict, symptom_dict)
        symptom_name, max_ieg_value = EntropyCalculator.max_ieg(symptom_IEG)
        pim.symptom_opt = symptom_name  # 更新 max_ieg symptom
        ieg_temp.append(symptom_IEG)
    question = skip_question.get('question', '')

    # 添加问诊对话
    ai_message = {"role": "system", "content": question}
    qa_messages.append(ai_message)

    pim.qa_messages = qa_messages
    await pim.save()

    """结束标志 2 """
    if len(qa_messages) / 2 < ROUND_MIN:  # 最少轮次限制
        should_stop = False
    else:
        should_stop = PIMService.isConvergence(delta_ieg_list, DELTA_IEG_CONVERGENCE)  # 收敛次数
    if should_stop:
        return JSONResponse({
            "status": "endChat"
        })

    # 返回JSON响应
    return JSONResponse({
        "status": "success",
        "user_message": user_message,
        "ai_message": ai_message
    })


@api_chat.post("/addition/{uid}")
async def goToAddition(uid: str, addition: str = Form(...)):
    """
    获取额外信息, 生成 CDG 和 PSG 记录
    :param uid: 唯一标识符
    :param addition: 患者填写的额外信息 (未来可拓展成其他信息)
    :return: JSON 返回
    """
    """PIM OBJ"""
    try:
        pim = await PIM.get(uid=uid)
    except DoesNotExist:
        return JSONResponse({
            "status": "redirect",
            "redirect_url": "/chat/new"
        })

    pim.addition = addition

    disease_prob_dict = pim.diseases[-1]
    qa_messages = pim.qa_messages
    symptoms_ = pim.symptoms  # {'S': Bool | None}
    symptoms = {}
    for k, v in symptoms_.items():
        if v is True:
            symptoms[k] = "是"
        elif v is False:
            symptoms[k] = "否"
        else:
            symptoms[k] = "未知"
    # {'S': "是" | "否" | "未知"}
    patient_addition = addition

    # 等待初步报告生成
    disease_and_reason = await AIGenerator.cdg01GenerateInitial(disease_prob_dict, qa_messages, symptoms, patient_addition)
    # {"disease": {"疾病1": 0.4, ...}, "reason": "诊断依据和推理过程"}
    await pim.save()

    """CDG 01 Initial"""
    disease_opt_dict = disease_and_reason.get("disease", {})
    disease_opt, _ = EntropyCalculator.max_ieg(disease_opt_dict)
    reason = disease_and_reason.get("reason", "")
    try:
        cdg = await CDG.get(uid=uid)
        cdg.disease_opt = disease_opt
        cdg.disease_opt_dict = disease_opt_dict
        cdg.initial = reason
        await cdg.save()
    except DoesNotExist:
        cdg = await CDG.create(uid=uid, pim=pim, disease_opt=disease_opt, disease_opt_dict=disease_opt_dict, initial=reason)

    """PSG Report ORM create"""
    try:
        psg = await PSG.get(uid=uid)
        psg.disease_opt = disease_opt
        await psg.save()
    except DoesNotExist:
        psg = await PSG.create(uid=uid, pim=pim, disease_opt=disease_opt)

    # 然后再返回页面
    return JSONResponse({
        "status": "redirect",
        "redirect_url": f"/report/{uid}"
    })
