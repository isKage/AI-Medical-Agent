import os
import pathlib

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from tortoise.exceptions import DoesNotExist
from fastapi.templating import Jinja2Templates

from models import PIM, CDG, PSG, Admin

api_history = APIRouter()
templates_path = os.path.join(pathlib.Path(__file__).parent.parent, "templates")
templates = Jinja2Templates(directory=templates_path)


@api_history.get("/")
async def searchHistory(uid: str):
    """根据 uid 查找患者"""
    uid = uid.strip().upper()
    try:
        psg = await PSG.get(uid=uid)
    except DoesNotExist:
        return RedirectResponse(url=f"/")
    else:
        return RedirectResponse(url=f"/report/{uid}")


@api_history.get("/all")
async def showHTML(request: Request):
    """admin 管理员查找所有记录 (页面)"""
    if "admin" not in request.session:
        return RedirectResponse(url="/admin/login")

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request
        }
    )


@api_history.post("/all")
async def getAllHistory():
    """admin 管理员查找所有记录"""
    pims = await PIM.all().order_by("-created_at")
    uids = [pim.uid for pim in pims]

    # 所有 PSG/CDG
    psg_list = await PSG.filter(uid__in=uids)
    cdg_list = await CDG.filter(uid__in=uids)

    # 构建 uid -> psg/cdg 映射字典
    psg_dict = {psg.uid: psg for psg in psg_list if psg.report and psg.report.strip()}
    cdg_dict = {cdg.uid: cdg for cdg in cdg_list if cdg.soap and cdg.soap.strip()}

    all_data = []
    for pim in pims:
        uid = pim.uid
        time_str = pim.created_at.strftime("%Y-%m-%d %H:%M:%S")

        all_data.append({
            "uid": uid,
            "psg": uid in psg_dict,
            "cdg": uid in cdg_dict,
            "time": time_str
        })

    return JSONResponse({
        "data": all_data
    })
