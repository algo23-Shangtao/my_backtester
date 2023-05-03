'''
全局设置
'''
from logging import CRITICAL
from typing import Dict, Any
from tzlocal import get_localzone_name


SETTING: Dict[str, Any] = {
    # log
    "log.active": True,
    "log.level": CRITICAL,
    "log.console": True,
    "log.file": True,

    # database
    "database.timezone": get_localzone_name(),
    "database.host": "121.37.81.170", # 数据库地址
    "database.port": 8848, # 数据库端口
    "database.user": "admin", # 用户名
    "database.password": "123456", # 密码

}