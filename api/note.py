import asyncio
import os
import pathlib
import markdown

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from tortoise.exceptions import DoesNotExist
from fastapi.templating import Jinja2Templates

from models import PIM, CDG
from .utils import AIGenerator, PIMService, EntropyCalculator

api_note = APIRouter()
templates_path = os.path.join(pathlib.Path(__file__).parent.parent, "templates")
templates = Jinja2Templates(directory=templates_path)


@api_note.get('/')
async def redirectToNew():
    """重定向至 /chat/new"""
    return RedirectResponse(url="/chat/new")


@api_note.get('/{uid}')
async def showHTML(request: Request, uid: str):
    """获取 uid 患者的临床记录"""
    if "admin" not in request.session:
        return RedirectResponse(url="/admin/login")
    try:
        cdg = await CDG.get(uid=uid)
    except DoesNotExist:
        return RedirectResponse(url=f'/chat/{uid}')

    initial = cdg.initial
    if initial is None or len(initial.strip()) == 0:
        return RedirectResponse(url=f'/chat/{uid}')

    initial_html = markdown.markdown(initial, extensions=['extra'])
    return templates.TemplateResponse(
        "note.html",
        {
            "request": request,
            "uid": uid,
            "initial": initial_html,
            "note": ""
        }
    )


@api_note.put('/{uid}')
async def getNote(uid: str):
    """获取 uid 患者的 SOAP 病历"""
    try:
        cdg = await CDG.get(uid=uid)
    except DoesNotExist:
        return JSONResponse({
            "status": "redirect",
            "redirect_url": f"/chat/{uid}"
        })

    note_html = markdown.markdown(cdg.soap, extensions=['extra', 'markdown.extensions.tables'])

    return JSONResponse({
        "status": "success",
        "uid": uid,
        "note": note_html
    })


@api_note.post('/{uid}')
async def generateSOAP(uid: str):
    """生成 uid 患者的 SOAP 临床记录"""
    try:
        pim = await PIM.get(uid=uid)
        cdg = await CDG.get(uid=uid)
    except DoesNotExist:
        return JSONResponse({
            "status": "redirect",
            "redirect_url": f"/chat/{uid}"
        })

    disease_prob_dict = pim.diseases[-1]
    disease_prob_dict = PIMService.top_k_items(disease_prob_dict, 5)
    disease_opt = cdg.disease_opt
    initial_note = cdg.initial
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
    disease_name_list = list(disease_prob_dict.keys())
    knowledge_addition_list = await PIMService.knowledge_query(disease_name_list)

    table_str = await PIMService.tableStr(disease_name_list, symptoms_)

    note = await AIGenerator.cdg02GenerateSOAP(disease_prob_dict, disease_opt, initial_note, qa_messages, symptoms, patient_addition,
                                               knowledge_addition_list, table_str)
    note_html = markdown.markdown(note, extensions=['extra', 'markdown.extensions.tables'])

    # 数据库保存
    cdg.soap = note
    await cdg.save()

    return JSONResponse({
        "status": "success",
        "uid": uid,
        "note": note_html
    })
