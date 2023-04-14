'''
数据库相关数据类型、父类和get_database()函数用于创建实例
'''
from abc import ABC, abstractmethod
from datetime import datetime
from types import ModuleType
from typing import List
from dataclasses import dataclass
from importlib import import_module

from datastructure.constant import Interval, Exchange
from datastructure.object import BarData, TickData
from datastructure.setting import SETTING

from zoneinfo import ZoneInfo

#TODO: 没有考虑时区管理
DB_TZ = ZoneInfo(SETTING["database.timezone"])

def convert_tz(dt: datetime) -> datetime:
    '''
    将输入时间转为当前(db?)所在时区
    '''
    dt: datetime = dt.astimezone(DB_TZ)
    return dt.replace(tzinfo=None)

@dataclass
class BarOverview:
    '''
    db中bar数据的基本信息
    '''
    symbol: str = ""
    exchange: Exchange = None
    interval: Interval = None
    count: int = 0
    start: datetime = None
    end: datetime = None

@dataclass
class TickOverview:
    '''
    db中tick数据的基本信息
    '''
    symbol: str = ""
    exchange: Exchange = None
    count: int = 0
    start: datetime = None
    end: datetime = None


class BaseDatabase(ABC): # 提供2个合约、日bar 分钟bar tick 
    '''
    数据库抽象类
    '''
    @abstractmethod
    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        '''
        保存bar数据到db
        '''
        pass

    @abstractmethod
    def save_tick_data(self, ticks: List[TickData], strean: bool = False) -> bool:
        '''
        保存tick数据到db
        '''
        pass

    @abstractmethod
    def load_bar_data(self, symbol: str, exchange: Exchange, interval: Interval, start: datetime, end: datetime) -> List[BarData]:
        '''
        从db读取bar数据
        '''
        pass
    
    @abstractmethod
    def load_tick_data(self, symbol: str, exchange: Exchange, start: datetime, end: datetime) -> List[TickData]:
        '''
        从db读取tick数据
        '''
        pass

    @abstractmethod
    def delete_bar_data(self, symbol: str, exchange: Exchange, interval: Interval) -> int:
        '''
        删除所有时间段指定数据
        '''
        pass

    @abstractmethod
    def delete_tick_data(self, symbol: str, exchange: Exchange) -> int:
        '''
        删除所有时间指定数据
        '''
        pass

    @abstractmethod
    def get_bar_overview(self) -> List[BarOverview]:
        '''
        查看数据库中支持的bar数据(哪些合约)
        '''
        pass

    @abstractmethod
    def get_tick_overview(self) -> List[TickOverview]:
        '''
        查看数据库中支持的tick数据(哪些合约)
        '''
        pass

# 创建database全局变量
database: BaseDatabase = None

def get_database() -> BaseDatabase:
    '''
    创建或返回database, 确保只有一个
    '''
    
    global database
    if database:
        return database
    
    db_name: str = SETTING["database.name"]
    module_name = "to_" + db_name
    # try to import database module, 还能这样import ?!
    try:
        module: ModuleType = import_module(module_name)
    except ModuleNotFoundError:
        print("不支持此数据库")
        return None
    
    database = module.Database()
    return database

