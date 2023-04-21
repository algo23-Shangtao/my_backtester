
from datetime import datetime
from core.engine import BaseEngine
from core.event import Event
from datastructure.object import TickData, BarData, OrderData, TradeData, SignalData
from datastructure.constant import Direction
from datastructure.definition import EVENT_STRATEGY
from utils.utils_class import BarGenerator, ArrayManager

class DoubleMaStrategy(BaseEngine):
    
    parameters = ["fast_window", "slow_window"]
    variables = ["fast_ma0", "fast_ma1", "slow_ma0", "slow_ma1"]

    fast_window = 10
    slow_window = 20
    fast_ma0 = 0.0
    fast_ma1 = 0.0
    slow_ma0 = 0.0
    slow_ma1 = 0.0

    def __init__(self, event_engine):
        super().__init__(engine_name='strategy', event_engine=event_engine)

        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
    
    def on_init(self) -> None:
        '''callback when strategy is inited'''
        self.output("策略初始化")
        self.load_tick(1)
    
    def on_start(self) -> None:
        '''callback when strategy is started'''
        self.output("策略启动")
    
    def on_stop(self) -> None:
        '''callback when strategy is stopped'''
        self.output("策略停止")
    
    def on_tick(self, tick: TickData) -> None:
        '''callback of new tick data update'''
        self.bg.update_tick(tick)
    
    def on_bar(self, bar: BarData) -> None:
        '''callback of new bar data update'''
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return
        
        fast_ma = am.sma(self.fast_window, array=True)
        self.fast_ma0 = fast_ma[-1]
        self.fast_ma1 = fast_ma[-2]
        slow_ma = am.sma(self.slow_window, array=True)
        self.slow_ma0 = slow_ma[-1]
        self.slow_ma1 = slow_ma[-2]

        cross_over = self.fast_ma0 > self.slow_ma0 and self.fast_ma1 < self.slow_ma1
        cross_below = self.fast_ma0 < self.slow_ma0 and self.fast_ma1 > self.slow_ma1

        if cross_over:
            signal: SignalData = SignalData(bar.datetime, Direction.LONG)
        elif cross_below:
            signal: SignalData = SignalData(bar.datetime, Direction.SHORT)
        
        self.on_signal(signal)


    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        pass

    
    def on_signal(self, signal: SignalData) -> None:
        signal_event: Event = Event(EVENT_STRATEGY, signal)
        self.event_engine.put(signal_event)
        
    def output(self, msg) -> None:
        print(f"{datetime.now()} strategy: {msg}")
            
    