'''
全局设置
'''
from logging import CRITICAL
from typing import Dict, Any
from tzlocal import get_localzone_name

# from .utility import load_json

SETTING: Dict[str, Any] = {
    # log
    "log.active": True,
    "log.level": CRITICAL,
    "log.console": True,
    "log.file": True,
    # datafeed
    "datafeed.name": "tqsdk",
    "datafeed.username": "",
    "datafeed.password": "",
    # database
    "database.timezone": get_localzone_name(),
    "database.name": "dolphindb", # 数据库名
    "database.database": "database.db", # 数据库实例
    "database.host": "localhost", # 数据库地址
    "database.port": 8848, # 数据库端口
    "database.user": "admin", # 用户名
    "database.password": "123456", # 密码

}