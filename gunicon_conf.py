import os
from multiprocessing import cpu_count

# 是否守护
daemon = True

# 绑定
bind = '0.0.0.0:8000'

# pid 文件地址
pidfile = 'gunicorn.pid'

# 项目地址
chdir = '.'

# Worker Options
workers = cpu_count()  # 异步, 若同步则使用 2 * CPU + 1
worker_class = "uvicorn.workers.UvicornWorker"  # 使用 uvicorn 异步
threads = 2  # 指定每个工作者的线程数

# Logging Options
loglevel = 'debug'  # 错误日志的日志级别
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'
# 设置访问日志和错误信息日志路径
log_dir = "./logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
accesslog = "./logs/gunicorn_access.log"
errorlog = "./logs/gunicorn_error.log"
