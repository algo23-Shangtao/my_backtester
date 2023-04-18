'''
数据库相关数据类型、父类和get_database()函数用于创建实例
'''
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from dataclasses import dataclass

from datastructure.constant import Interval, Exchange
from datastructure.object import BarData, TickData, ContractData
from datastructure.setting import SETTING



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

    # @abstractmethod
    # def save_instrument_info(self, infos: List[ContractData]) -> bool:
    #     '''
    #     将合约信息存入数据库
    #     '''
    #     pass
    
    # @abstractmethod
    # def load_instrument_info(self, symbol: str, exchange: Exchange) -> ContractData:
    #     '''
    #     查看指定合约信息
    #     '''
    #     pass

database: BaseDatabase = None

def get_database() -> BaseDatabase:
    '''
    创建或返回database, 确保只有一个
    '''
    
    global database
    if database:
        return database
    
    try:
        from .to_dolphindb import Database
    except ModuleNotFoundError:
        print("不支持此数据库")
        return None
    
    database = Database()
    return database

