import asyncio
import bcrypt
from models import Admin
from tortoise import Tortoise

from settings import TORTOISE_ORM

credentials = TORTOISE_ORM['connections']['default']['credentials']
user = credentials['user']
pwd = credentials['password']
database = credentials['database']
port = credentials['port']
host = credentials['host']


async def run():
    await Tortoise.init(
        db_url=f'mysql://{user}:{pwd}@{host}:{port}/{database}',
        modules={'models': ['models']}
    )
    await Tortoise.generate_schemas()

    name = input("请输入管理员用户名: ")
    password = input("请输入密码: ")
    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    await Admin.create(name=name, password=hashed_pw)
    print("管理员创建成功")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run())
