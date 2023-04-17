'''Cta策略模板'''
from abc import ABC, abstractmethod
from copy import copy
from typing import Any, Callable, List

from datastructure.constant import Interval, Direction, Offset, EngineType
from datastructure.object import BarData, TickData, OrderData, TradeData, OrderRequest
from oms.omsEngine import OmsEngine

# from core.backtesting_engine import BacktestingEngine

class CtaTemplate(ABC):
    '''
    Cta策略模板
    '''
    author: str = ""
    parameters: List[str] = [] # 参数名
    variables: List[str] = [] # 变量名

    def __init__(
            self, 
            oms_engine: Any, 
            strategy_name: str, 
            vt_symbol: str, 
            setting: dict) -> None:
        self.oms_engine: OmsEngine = oms_engine
        self.strategy_name: str = strategy_name
        self.vt_symbol: str = vt_symbol

        self.inited: bool = False
        self.trading: bool = False
        self.pos: int = 0                           # 由该策略产生的仓位 

        #### 在干吗?
        self.variables = copy(self.variables)
        self.variables.insert(0, "inited")
        self.variables.insert(1, "trading")
        self.variables.insert(2, "pos")


    #### TODO 用于策略初始化参数
    def load_bar(
            self,
            days: int,
            interval: Interval.MINUTE,
            callback: Callable = None,
            use_database: bool = False
    ) -> None:
        '''加载历史bar数据用来初始化策略参数'''
        # 将策略的初始化函数传入回测引擎(cta_engine)中, 默认为on_bar
        if not callback:
            callback: Callable = self.on_bar
        bars: List[BarData] = self.cta_engine.load_bar(
            self.vt_symbol,
            days,
            interval,
            callback, # on_bar
            use_database
        )
        #### TODO 并没有返回bars
        for bar in bars:
            callback(bar)

    def load_tick(self, days: int) -> None:
        '''加载历史tick数据来初始化策略参数'''
        # 将策略的初始化函数传入回测引擎(cta_engine)中, 默认为on_tick
        ticks: List[TickData] = self.cta_engine.load_tick(self.vt_symbol, days, self.on_tick)
        for tick in ticks:
            self.on_tick(tick)
    ####


    # 回调函数们
    @abstractmethod
    def on_init(self) -> None:
        '''
        回调函数: 策略初始化
        '''
        pass

    @abstractmethod
    def on_start(self) -> None:
        """
        回调函数: 开始执行策略
        """
        pass

    @abstractmethod
    def on_stop(self) -> None:
        """
        回调函数: 停止执行
        """
        pass

    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """
        回调函数: 处理新的TickData
        """
        pass

    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """
        回调函数: 处理新的BarData
        """
        pass

    @abstractmethod
    def on_trade(self, trade: TradeData) -> None:
        """
        回调函数: 处理新的TradeData
        """
        pass

    @abstractmethod
    def on_order(self, order: OrderData) -> None:
        """
        回调函数: 处理新的OrderData
        """
        pass
    
    # 快捷下单指令
    def buy(self, 
            price: float, 
            volume: float, 
            stop: bool = False, 
            lock: bool = False, 
            net: bool = False) -> list:
        '''
        下达买开委托
        '''
        return self.send_order(Direction.LONG, Offset.OPEN, price, volume, stop, lock, net)
    
    def sell(self, 
            price: float, 
            volume: float, 
            stop: bool = False, 
            lock: bool = False, 
            net: bool = False) -> list:
        '''
        下达卖平委托
        '''
        return self.send_order(Direction.SHORT, Offset.CLOSE, price, volume, stop, lock, net)
    
    def short(self, 
            price: float, 
            volume: float, 
            stop: bool = False, 
            lock: bool = False, 
            net: bool = False) -> list:
        '''
        下达卖开委托
        '''
        return self.send_order(Direction.SHORT, Offset.OPEN, price, volume, stop, lock, net)

    def cover(self, 
            price: float, 
            volume: float, 
            stop: bool = False, 
            lock: bool = False, 
            net: bool = False) -> list:
        '''
        下达买平委托
        '''
        return self.send_order(Direction.LONG, Offset.CLOSE, price, volume, stop, lock, net)
    
    def send_order(self, 
                   direction: Direction, 
                   offset: Offset, 
                   price: float, 
                   volume: float, 
                   stop: bool = False,
                   lock: bool = False,
                   net: bool = False) -> list:
        '''
        调用cta_engine, 执行下单指令
        '''
        ####TODO self.trading干嘛用的
        req: OrderRequest = self.oms_engine.generate_order_request(self, direction, offset, price, volume)
        
    def cancel_order(self, vt_orderid: str) -> None:
        '''
        调用cta_engine, 执行撤单指令
        '''
        if self.trading:
            self.cta_engine.cancel_order(self, vt_orderid)
    
    def cancel_all(self) -> None:
        '''
        调用cta_engine, 撤销所有由该策略发出的单
        '''
        if self.trading:
            self.cta_engine.cancel_all(self)

    def write_log(self, msg: str) -> None:
        '''
        调用cta_engine, 输出日志
        '''
        self.cta_engine.write_log(msg, self)

    
    # 以下为查询函数
    @classmethod
    def get_class_parameters(cls) -> dict:
        '''
        获得该策略类默认的所有参数值
        '''
        class_parameters: dict = {}
        for name in cls.parameters:
            class_parameters[name] = getattr(cls, name)
        return class_parameters
    
    def get_parameters(self) -> dict:
        '''
        获得该策略类当前的所有参数值
        '''
        strategy_parameters: dict = {}
        for name in self.parameters:
            strategy_parameters[name] = getattr(self, name)
        return strategy_parameters

    def get_variables(self) -> dict:
        '''
        获得该策略类当前的所有变量值
        '''
        strategy_variables: dict = {}
        for name in self.variables:
            strategy_variables[name] = getattr(self, name)
        return strategy_variables
    
    def get_data(self) -> dict:
        '''
        获得该策略所有信息
        '''
        strategy_data: dict = {
            "strategy_name": self.strategy_name,
            "vt_symbol": self.vt_symbol,
            "class_name": self.__class__.__name__,
            "author": self.author,
            "parameters": self.get_parameters(),
            "variables": self.get_variables()
        }
        return strategy_data
    
    def get_engine_type(self) -> EngineType:
        """
        Return whether the cta_engine is backtesting or live trading.
        """
        return self.cta_engine.get_engine_type()

    def get_pricetick(self) -> float:
        """
        Return pricetick data of trading contract.
        """
        return self.cta_engine.get_pricetick(self)

    def get_size(self) -> int:
        """
        Return size data of trading contract.
        """
        return self.cta_engine.get_size(self)



