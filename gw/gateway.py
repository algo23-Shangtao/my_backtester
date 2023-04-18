
from typing import Any


from core.event import Event, EventEngine
from core.event import EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_LOG

from datastructure.object import TickData, OrderData, TradeData, LogData


class BaseGateway:
    '''
    连接不同交易系统的交易接口(Gateway)
    '''

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        self.event_engine: EventEngine = event_engine
        self.gateway_name: str = gateway_name


    # 以下为向事件队列中放入各种事件
    def on_event(self, type: str, data: Any = None) -> None:
        '''
        向event_engine的事件队列中放入事件
        '''
        event: Event = Event(type, data)
        self.event_engine.put(event)
    
    def on_tick(self, tick: TickData) -> None:
        '''
        行情更新
        '''
        self.on_event(EVENT_TICK, tick)
        

    def on_trade(self, trade: TradeData) -> None:
        '''
        成交更新
        '''
        self.on_event(EVENT_TRADE, trade)
        
    
    def on_order(self, order: OrderData) -> None:
        '''
        订单状态更新
        '''
        self.on_event(EVENT_ORDER, order)
        

    def on_log(self, log: LogData) -> None:
        """
        向event_engine的事件队列中放入日志记录事件(Log event)
        """
        self.on_event(EVENT_LOG, log)

    def write_log(self, msg: str) -> None:
        """
        Write a log event from gateway.
        """
        log: LogData = LogData(msg=msg, gateway_name=self.gateway_name)
        self.on_log(log)    
