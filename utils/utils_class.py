from typing import Callable, Optional, List, Union
from datastructure.constant import Interval
from datastructure.object import BarData, TickData
from datastructure.definition import INTERVAL_DELTA_MAP
import numpy as np
import talib

class BarGenerator:
    '''
    1. tick data -> 1 min bar data
    '''
    #### TODO window ? on_window_bar ?
    def __init__(
            self,
            on_bar: Callable,
            
            # window: int = 0,
            # on_window_bar: Callable = None,

            interval: Interval = Interval.MINUTE
    ) -> None:
        self.bar: BarData = None
        self.on_bar: Callable = on_bar
        self.bars: List[BarData] = []

        self.interval: Interval = interval
        self.interval_count: int = 0

        # self.hour_bar: BarData = None

        # self.window: int = window
        # self.window_bar: BarData = None
        # self.on_window_bar: Callable = on_window_bar

        self.last_tick: TickData = None

    def update_tick(self, tick: TickData) -> None:
        '''
        不断输入TickData, 产生BarData并存入bars中, 对每个产生的BarData调用传入的callback
        '''
        new_minute: bool = False

        # 防止脏数据
        if not tick.last_price: 
            return # 剔除最新价为0
        if self.last_tick and tick.datetime < self.last_tick.datetime: # 如果self.last_tick为None, 也会继续往下执行, 不会return
            return # 剔除时间戳逆序
        
        # 针对第一个tick -> 初始化并不存在的last_tick
        if self.last_tick == None:
            self.last_tick = TickData(
                gateway_name=tick.gateway_name,
                symbol=tick.symbol,
                exchange=tick.exchange,
                datetime=tick.datetime - INTERVAL_DELTA_MAP[Interval.TICK],
                volume=0,
                turnover=0,
                open_interest=0,
                last_price=tick.last_price,
                highest_price=tick.last_price,
                lowest_price=tick.last_price
            )
        # 是否产生新分钟bar
        if not self.bar:
            new_minute = True
        # 以下vnpy源码有bug--不符合左开右闭原则
        # elif(
        #     (self.bar.datetime.minute != tick.datetime.minute) # 新分钟
        #     or (self.bar.datetime.hour != tick.datetime.hour)  # 新小时
        # ):
        elif(
            (self.bar.datetime.minute != tick.datetime.minute)
            and (tick.datetime.microsecond != 0)
        ):
            self.bar.datetime = self.bar.datetime.replace(second=0, microsecond=0) # 上一个bar生成完毕!
            self.on_bar(self.bar) # 上一个bar, 执行传入的callback
            self.bars.append(self.bar) # 储存合成的bar
            new_minute = True
        # 需要产生新分钟bar
        if new_minute:
            # volume, turnover
            self.bar = BarData(
                gateway_name=tick.gateway_name,
                symbol=tick.symbol,
                exchange=tick.exchange,
                datetime=tick.datetime, # 需要self.bar.datetime.replace
                interval=Interval.MINUTE,
                open_price=self.last_tick.last_price, # 最新价在此!
                high_price=tick.last_price, # 初始化
                low_price=tick.last_price,  # 初始化
                close_price=tick.last_price, # 初始化
                open_interest=tick.open_interest # 初始化
            )
        
        # 如果tick最新价突破原bar最高价, 则用tick最新价更新bar最高价
        self.bar.high_price = max(self.bar.high_price, tick.last_price)
        # 如果tick最高价突破原tick最高价, 则改用tick最高价更新bar最高价
        if tick.highest_price > self.last_tick.highest_price:
            self.bar.high_price = max(self.bar.high_price, tick.highest_price)
        # 最低价更新逻辑同理
        self.bar.low_price = min(self.bar.low_price, tick.last_price)
        if tick.lowest_price < self.last_tick.lowest_price:
            self.bar.low_price = min(self.bar.low_price, tick.lowest_price)
        # 更新收盘价, 持仓量, 时间戳
        self.bar.close_price = tick.last_price
        self.bar.open_interest = tick.open_interest
        # self.bar.datetime = tick.datetime # 需要self.bar.datetime.replace
        
        if self.last_tick:
            volume_change: float = tick.volume - self.last_tick.volume
            self.bar.volume += max(volume_change, 0) # 应该不会出现吧
            turnover_change: float = tick.turnover - self.last_tick.turnover
            self.bar.turnover += max(turnover_change, 0)
        
        self.last_tick = tick

    def generate(self) -> Optional[BarData]:
        '''
        立即产生bar data, 并执行callback
        '''
        bar: BarData = self.bar
        if self.bar:
            bar.datetime = bar.datetime.replace(second=0, microsecond=0)
            self.on_bar(bar)
        self.bar = None
        return bar
            
        
class ArrayManager:
    '''
    1. time series container of bar data
    2. calculate technical indicator value
    '''
    def __init__(self, size: int = 100) -> None:
        """Constructor"""
        self.count: int = 0
        self.size: int = size
        self.inited: bool = False

        self.open_array: np.ndarray = np.zeros(size)
        self.high_array: np.ndarray = np.zeros(size)
        self.low_array: np.ndarray = np.zeros(size)
        self.close_array: np.ndarray = np.zeros(size)
        self.volume_array: np.ndarray = np.zeros(size)
        self.turnover_array: np.ndarray = np.zeros(size)
        self.open_interest_array: np.ndarray = np.zeros(size)
    
    def update_bar(self, bar: BarData) -> None:
        """
        Update new bar data into array manager.
        """
        self.count += 1

        # 优先级: not > and > or
        if not self.inited and self.count >= self.size: # 已经装满(size)
            self.inited = True
        # 将最新bar更新到array中
        # 左移一位
        self.open_array[:-1] = self.open_array[1:]
        self.high_array[:-1] = self.high_array[1:]
        self.low_array[:-1] = self.low_array[1:]
        self.close_array[:-1] = self.close_array[1:]
        self.volume_array[:-1] = self.volume_array[1:]
        self.turnover_array[:-1] = self.turnover_array[1:]
        self.open_interest_array[:-1] = self.open_interest_array[1:]
        # 最后一位放入最新bar
        self.open_array[-1] = bar.open_price
        self.high_array[-1] = bar.high_price
        self.low_array[-1] = bar.low_price
        self.close_array[-1] = bar.close_price
        self.volume_array[-1] = bar.volume
        self.turnover_array[-1] = bar.turnover
        self.open_interest_array[-1] = bar.open_interest
    
    def sma(self, n: int, array: bool = False) -> Union[float, np.ndarray]:
        """
        Simple moving average.
        """
        result: np.ndarray = talib.SMA(self.close, n)
        if array:
            return result
        return result[-1]

    def ema(self, n: int, array: bool = False) -> Union[float, np.ndarray]:
        """
        Exponential moving average.
        """
        result: np.ndarray = talib.EMA(self.close, n)
        if array:
            return result
        return result[-1]
    
    @property
    def open(self) -> np.ndarray:
        """
        Get open price time series.
        """
        return self.open_array

    @property
    def high(self) -> np.ndarray:
        """
        Get high price time series.
        """
        return self.high_array

    @property
    def low(self) -> np.ndarray:
        """
        Get low price time series.
        """
        return self.low_array

    @property
    def close(self) -> np.ndarray:
        """
        Get close price time series.
        """
        return self.close_array

    @property
    def volume(self) -> np.ndarray:
        """
        Get trading volume time series.
        """
        return self.volume_array

    @property
    def turnover(self) -> np.ndarray:
        """
        Get trading turnover time series.
        """
        return self.turnover_array

    @property
    def open_interest(self) -> np.ndarray:
        """
        Get trading volume time series.
        """
        return self.open_interest_array



