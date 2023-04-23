from .template import StrategyTemplate
from core.event import EventEngine, Event
from datastructure.constant import Direction
from datastructure.object import TickData, BarData, OrderData, TradeData, SignalData

from datetime import datetime




class BuyAndHoldStrategy(StrategyTemplate):
    def __init__(self, event_engine: EventEngine) -> None:
        super().__init__(event_engine)
    
    
    def on_init(self) -> None:
        '''callback when strategy is inited'''
        self.inited = True
        self.output('策略初始化完成')

    
    def on_start(self) -> None:
        '''callback when strategy is started'''
        self.started = True
        self.output('策略开始')
    
    def on_stop(self) -> None:
        '''callback when strategy is stopped'''
        self.started = False
        self.output('策略停止')
    
    def on_tick(self, event: Event) -> None:
        '''callback of new tick data update'''
        
        self.output('策略接收最新tick')
        
        tick: TickData = event.data

        if (tick.datetime >= datetime(2023,1,3,9,0,0)) & (tick.datetime < datetime(2023,1,3,9,0,3)):
            signal: SignalData = SignalData(tick.datetime, Direction.LONG)
            self.on_signal(signal)
            self.output('策略产生多信号')
        if tick.datetime >= datetime(2023,1,3,9,0,3):
            signal: SignalData = SignalData(tick.datetime, Direction.SHORT)
            self.on_signal(signal)
            self.output('策略产生空信号')
    
    def on_bar(self, event: Event) -> None:
        '''callback of new bar data update'''
        pass
    
    def on_order(self, event: Event):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, event: Event):
        """
        Callback of new trade data update.
        """
        pass