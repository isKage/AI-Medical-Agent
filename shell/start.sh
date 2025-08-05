#!/bin/bash

cd /root/AIMGD || exit
source /envs/aimgd/bin/activate

nohup /envs/aimgd/bin/gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --daemon \
  -b 0.0.0.0:8000 \
  -c /root/AIMGD/gunicorn.py \
  main:app > logs/gunicorn_start.log 2>&1 &

echo "✅ FastAPI 项目已启动。查看日志：/root/AIMGD/logs/gunicorn_start.log"
echo "click URL: http://106.14.29.201/"
