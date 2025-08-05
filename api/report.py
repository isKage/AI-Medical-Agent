import asyncio
import os
import pathlib
import markdown

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from tortoise.exceptions import DoesNotExist
from fastapi.templating import Jinja2Templates

from models import PIM, PSG, MedicalKnowledge
from .utils import AIGenerator

api_report = APIRouter()
templates_path = os.path.join(pathlib.Path(__file__).parent.parent, "templates")
templates = Jinja2Templates(directory=templates_path)


@api_report.get('/')
async def redirectToNew():
    """重定向至 /chat/new"""
    return RedirectResponse(url="/chat/new")


@api_report.get('/{uid}')
async def showHTML(request: Request, uid: str):
    """展示页面, 数据由 JS 发送请求加载"""
    info = None
    # info = {
    #     "basic": [
    #         {"name": "性别", "value": "男"},
    #         {"name": "年龄", "value": "45"},
    #         {"name": "身高", "value": "170"},
    #         {"name": "体重", "value": "60"},
    #     ],
    #     "examination": [
    #         {"name": "血压", "value": "..."},
    #         {"name": "血糖", "value": "..."},
    #         {"name": "血脂", "value": "..."},
    #         {"name": "收缩压", "value": "..."},
    #         {"name": "舒张压", "value": "..."},
    #     ],
    # }

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "uid": uid,  # str
            "report": "",
            "info": info
        }
    )


@api_report.put('/{uid}')
async def getReport(uid: str):
    """获取 uid 患者的报告"""
    try:
        psg = await PSG.get(uid=uid)
        report_html = markdown.markdown(psg.report, extensions=['extra', 'markdown.extensions.tables'])
    except DoesNotExist:
        return JSONResponse({
            "status": "redirect",
            "redirect_url": f"/chat/{uid}"
        })

    return JSONResponse({
        "status": "success",
        "uid": uid,
        "report": report_html
    })


@api_report.post('/{uid}')
async def generateReport(uid: str):
    """生成 uid 患者的报告"""
    try:
        pim = await PIM.get(uid=uid)
        psg = await PSG.get(uid=uid)
    except DoesNotExist:
        return JSONResponse({
            "status": "redirect",
            "redirect_url": f"/chat/{uid}"
        })

    disease_name = psg.disease_opt
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
    patient_addition = pim.addition
    try:
        knowledge_addition = await MedicalKnowledge.get(name=disease_name).values()
    except DoesNotExist:
        knowledge_addition = []

    try:
        # 生成报告
        report = await AIGenerator.psg01GenerateReport(disease_name, qa_messages, symptoms, patient_addition, knowledge_addition)
        # 保存生成的报告到数据库
        psg.report = report
        report_html = markdown.markdown(report, extensions=['extra', 'markdown.extensions.tables'])
        await psg.save()
        return JSONResponse({
            "status": "success",
            "uid": uid,
            "report": report_html,  # html
        })

    except Exception as e:
        return JSONResponse({
            "status": "error",
            "uid": uid,
            "report": "网络卡顿或系统繁忙，请稍后重试！"
        })
