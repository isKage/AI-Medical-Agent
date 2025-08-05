import os
import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from tortoise.exceptions import DoesNotExist
from fastapi.templating import Jinja2Templates

from models import PIM, EVAL

api_eval = APIRouter()
templates_path = os.path.join(pathlib.Path(__file__).parent.parent, "templates")
templates = Jinja2Templates(directory=templates_path)


@api_eval.get("/")
async def redirectToNew():
    """重定向至 /"""
    return RedirectResponse(url="/")


@api_eval.get("/doctor/{uid}")
async def doctorEvalHTML(request: Request, uid: str):
    doctor_fields = list(enumerate(
        [
            "1、 信息准确地反映了患者【当前状态】",
            "2、 内容准确，符合患者【真实情况，没有编造信息】",
            "3、 信息全面，【未遗漏重要内容】",
            "4、 信息【对制定治疗计划有帮助】",
            "5、 内容【结构清晰】、条理清楚",
            "6、 内容【易于理解】，表达清楚",
            "7、 内容【简明扼要】，没有冗余",
            "8、 对关键信息进行了【整合与归纳】",
            "9、 内容前后【一致】，无较大的出入",
        ]
    ))
    # 数据库查询 len(existing_scores) = len(fields) + 2
    try:
        _eval = await EVAL.get(uid=uid)
        existing_scores = _eval.doctor_eval
    except DoesNotExist:
        existing_scores = []

    return templates.TemplateResponse(
        "eval.html",
        {
            "request": request,
            "uid": uid,
            "mode": "doctor",
            "fields": doctor_fields,
            "existing_scores": existing_scores
        }
    )


@api_eval.get("/patient/{uid}")
async def patientEvalHTML(request: Request, uid: str):
    patient_fields = list(enumerate(
        [
            # 对话
            "1、对话时，系统提问涵盖【全面】，没有遗漏重要内容",
            "2、系统的提问没有冒犯到您，让您感受到【被尊重和理解】",
            "3、对话时，系统提出的问题【表达清晰】，易于理解",
            "4、与系统的对话【流畅自然】",
            "5、提问的语气让您感到了安心和【信任】",
            # 报告
            "6、系统生成的【报告清晰明了】",
            "7、报告【充分解释】了您的病情，没有遗漏信息",
            "8、报告【解释清楚了进一步检查和就诊的原因】",
            "9、报告给出的【就医建议实用且有帮助】",
            # 整体
            "10、系统十分专业，【具备为您提供医疗服务和诊断的能力】",
            "11、您【愿意采纳】系统提供的建议",
            "12、您【愿意再次使用】该系统"
        ]
    ))
    # 数据库查询
    try:
        _eval = await EVAL.get(uid=uid)
        existing_scores = _eval.patient_eval
    except DoesNotExist:
        existing_scores = []
    return templates.TemplateResponse(
        "eval.html",
        {
            "request": request,
            "uid": uid,
            "mode": "patient",
            "fields": patient_fields,
            "existing_scores": existing_scores
        }
    )


@api_eval.post("/{mode}/{uid}")
async def sendEval(request: Request, mode: str, uid: str):
    try:
        pim = await PIM.get(uid=uid)
    except DoesNotExist:
        return JSONResponse(
            {
                "status": "redirect",
                "redirect_url": "/chat/new"
            }
        )

    form_data = await request.form()
    v = list(form_data.values())
    eval_values_list = [form_data[f"q{i}"] for i in range(len(v) - 2)]  # 分数类
    eval_values_list.append(form_data["positive"])
    eval_values_list.append(form_data["negative"])

    try:
        eval = await EVAL.get(uid=uid)
        if mode == "doctor":
            eval.doctor_eval = eval_values_list
        else:
            eval.patient_eval = eval_values_list
        await eval.save()
    except DoesNotExist:
        if mode == "doctor":
            await EVAL.create(uid=uid, doctor_eval=eval_values_list, pim=pim)
        else:
            await EVAL.create(uid=uid, patient_eval=eval_values_list, pim=pim)

    redirect_url = f"/report/{uid}" if mode == "patient" else f"/note/{uid}"

    return JSONResponse(
        {
            "status": "success",
            "uid": uid,
            "redirect_url": redirect_url
        }
    )
