import json
import os
import pathlib
import bcrypt

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from tortoise.exceptions import DoesNotExist
from fastapi.templating import Jinja2Templates

from models import PIM, CDG, PSG, Admin

api_admin = APIRouter()
templates_path = os.path.join(pathlib.Path(__file__).parent.parent, "templates")
templates = Jinja2Templates(directory=templates_path)


@api_admin.get("/")
async def redirect_admin():
    return RedirectResponse(url="/admin/login")


@api_admin.get("/login")
async def admin(request: Request):
    """管理员登陆页面展示"""
    if "admin" in request.session:
        return RedirectResponse(url="/history/all")

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request
        }
    )


@api_admin.post("/login")
async def login(request: Request, name: str = Form(...), password: str = Form(...)):
    """管理员登陆"""
    # 密码需要加密, 第一个管理员需要脚本加密后手动写入 mysql 数据库
    # 登陆成功后保存管理员信息, 只会会限制: 部分网页只有管理员有权限访问; 部分按钮和链接只有登陆管理员才显示
    try:
        admin = await Admin.get(name=name)
        # 验证密码
        if bcrypt.checkpw(password.encode(), admin.password.encode()):
            request.session["admin"] = admin.name
            return RedirectResponse(url="/history/all", status_code=302)  # 转 POST 为 GET
        else:
            raise ValueError("密码错误")
    except (DoesNotExist, ValueError):
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "error": "用户名或密码错误"
            }
        )


@api_admin.get("/logout")
async def logout(request: Request):
    """管理员退出"""
    request.session.clear()
    return RedirectResponse(url="/")


@api_admin.delete("/{uid}")
async def deleteHistory(uid: str):
    """删除 uid 的历史记录"""
    # 只有管理员有权限删除用户 uid 的历史记录
    try:
        pim = await PIM.filter(uid=uid).delete()
    except DoesNotExist:
        return JSONResponse(
            {
                "status": "error",
                "message": "当前用户不存在"
            },
            status_code=404
        )

    return JSONResponse(
        {
            "status": "success",
            "message": "删除成功"
        },
        status_code=200
    )


@api_admin.get("/detail/{uid}")
async def showDetail(request: Request, uid: str):
    if "admin" not in request.session:
        return RedirectResponse(url="/admin/login")
    try:
        pim = await PIM.get(uid=uid).values("id", "uid", "qa_messages", "diseases", "symptoms", "ieg", "addition", "delta_ieg", "is_related",
                                            "unrelated_count")
        cdg = await CDG.get(uid=uid).values("disease_opt", "disease_opt_dict")
        json_str = json.dumps({"cdg": cdg, "pim": pim}, indent=2, ensure_ascii=False)

        # 简单 HTML 页面，展示 JSON
        html_content = f"""
                <html>
                    <head><title>详情 {uid}</title></head>
                    <body>
                        <pre>{json_str}</pre>
                    </body>
                </html>
                """
        return HTMLResponse(content=html_content)
    except DoesNotExist:
        return HTMLResponse(content="<h2>未找到对应数据</h2>", status_code=404)
