from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from copy import copy

from core.event import Event, EventEngine
from core.event import (EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, 
                   EVENT_ACCOUNT, EVENT_CONTRACT, EVENT_LOG, EVENT_QUOTE)

from datastructure.object import (TickData, OrderData, TradeData, PositionData, AccountData, 
                    ContractData, LogData, QuoteData, OrderRequest, CancelRequest, 
                    SubscribeRequest, HistoryRequest, QuoteRequest, Exchange, BarData)


class BaseGateway(ABC):
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
        向event_engine的事件队列中放入行情更新事件(Tick event)
        Tick event of a specific vt_symbol is also pushed --- 防止重名?
        '''
        self.on_event(EVENT_TICK, tick)
        # self.on_event(EVENT_TICK + tick.vt_symbol, tick) # 为什么要再put一次?

    def on_trade(self, trade: TradeData) -> None:
        '''
        向event_engine的事件队列中放入成交事件(Trade event)
        Trade event of a specific vt_symbol is also pushed --- 防止重名?
        '''
        self.on_event(EVENT_TRADE, trade)
        # self.on_event(EVENT_TRADE + trade.vt_tradeid, trade)
    
    def on_order(self, order: OrderData) -> None:
        '''
        向event_engine的事件队列中放入下单事件(Order event)
        Order event of a specific vt_orderid is also pushed --- 防止重名?
        '''
        self.on_event(EVENT_ORDER, order)
        # self.on_event(EVENT_ORDER + order.vt_orderid, order)

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
