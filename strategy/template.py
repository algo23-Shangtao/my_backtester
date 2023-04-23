from abc import abstractmethod

from datetime import datetime
from core.engine import BaseEngine
from core.event import Event, EventEngine
from datastructure.object import TickData, BarData, OrderData, TradeData, SignalData
from datastructure.constant import Direction
from datastructure.definition import EVENT_STRATEGY, EVENT_TICK, EVENT_ORDER, EVENT_TRADE


class StrategyTemplate(BaseEngine):
    def __init__(self, event_engine: EventEngine) -> None:
        super().__init__(event_engine, 'strategy')
        self.inited = False
        self.started = False
        self.register_event()
    
    def on_signal(self, signal: SignalData) -> None:
        signal_event: Event = Event(EVENT_STRATEGY, signal)
        self.event_engine.put(signal_event)
        
    
    def output(self, msg) -> None:
        print(f"{datetime.now()} strategy: {msg}")
    
    def register_event(self) -> None:
        self.event_engine.register(EVENT_TICK, self.on_tick)
        self.event_engine.register(EVENT_ORDER, self.on_order)
        self.event_engine.register(EVENT_TRADE, self.on_trade)

    @abstractmethod
    def on_init(self) -> None:
        '''callback when strategy is inited'''
        pass

    
    @abstractmethod
    def on_start(self) -> None:
        '''callback when strategy is started'''
        pass
    
    @abstractmethod
    def on_stop(self) -> None:
        '''callback when strategy is stopped'''
        pass
    
    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        '''callback of new tick data update'''
        pass
    
    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        '''callback of new bar data update'''
        pass
    
    @abstractmethod
    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    @abstractmethod
    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        pass

    

