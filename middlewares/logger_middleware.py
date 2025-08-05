import os
import logging
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from logging.handlers import RotatingFileHandler
import pytz
import sys

# 确保 logs 目录存在
os.makedirs("logs", exist_ok=True)

# 设置 logger
logger = logging.getLogger("aimgd")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

# 文件 handler
file_handler = RotatingFileHandler("logs/aimgd.log", maxBytes=1 * 1024 * 1024, backupCount=5, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 控制台 handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 设置时区
tz = pytz.timezone("Asia/Shanghai")


# 中间件函数
async def logMiddleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        now = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        logger.error(f"{request.url.path}: {repr(e)}")
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
