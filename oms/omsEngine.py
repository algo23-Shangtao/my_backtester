from abc import ABC
from pathlib import Path
from datetime import datetime

from typing import Any, Type, Dict, List

from core.event import Event, EventEngine
from core.event import (EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, 
                   EVENT_ACCOUNT, EVENT_CONTRACT, EVENT_LOG, EVENT_QUOTE)
from core.engine import BaseEngine
from gw.gateway import BaseGateway
from datastructure.constant import Direction, Offset, OrderType
from datastructure.object import (CancelRequest, LogData, OrderRequest, QuoteData, 
                    QuoteRequest, SubscribeRequest, HistoryRequest, 
                    OrderData, BarData, TickData, SignalData, TradeData, PositionData, 
                    AccountData, ContractData, Exchange)


class OmsEngine(BaseEngine):
    '''
    订单管理系统Oms
    封装了eventEngine
    封装了各种数据Dict以及OffsetConverter
    回调函数: 利用各种数据Dict和OffsetConverter实现处理各种event的逻辑
    查询函数: 查询封装的各种数据Dict
    '''
    def __init__(self, event_engine: EventEngine) -> None:
        super(OmsEngine, self).__init__(event_engine, "oms")
        
        self.ticks: Dict[str, TickData] = {} # {vt_symbol: tick} # 记录最新的tick
        self.orders: Dict[str, OrderData] = {} # {vt_orderid: order} # 记录所有订单
        self.trades: Dict[str, TradeData] = {} # {vt_tradeid: trade} # 记录所有成交
        self.positions: Dict[str, PositionData] = {} # {vt_positionid: position}
        self.accounts: Dict[str, AccountData] = {} # {vt_accountid: account} # 
        self.contracts: Dict[str, ContractData] = {} # {vt_symbol: contract}
        self.quotes: Dict[str, QuoteData] = {} # {vt_quoteid: quote}
        self.active_orders: Dict[str, OrderData] = {} # {vt_orderid: order}
        self.active_quotes: Dict[str, QuoteData] = {} # {vt_quoteid: quote}

        # self.add_function()
        self.register_event()
    


    # 注册回调函数
    def register_event(self) -> None:
        """注册回调函数"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        self.event_engine.register(EVENT_POSITION, self.process_position_event)
        self.event_engine.register(EVENT_ACCOUNT, self.process_account_event)
        self.event_engine.register(EVENT_CONTRACT, self.process_contract_event)
        self.event_engine.register(EVENT_QUOTE, self.process_quote_event)

    # 各种事件处理逻辑(回调函数实现)
    def process_tick_event(self, event: Event) -> None:
        """获取Tick Event中的TickData, 存入ticks, 仅存最新的时间"""
        tick: TickData = event.data
        self.ticks[tick.vt_symbol] = tick
    
    def process_signal_event(self, event: Event) -> None:
        '''获取Signal Event中的SignalData, 存入signals, 并根据信号产生下单请求'''
        signal: SignalData = event.data
        vt_symbol: str = signal.vt_symbol
        symbol: str = signal.symbol
        exchange: Exchange = signal.exchange
        datetime: datetime = signal.datetime
        direction: Direction = signal.direction
        strength: float = signal.strength


        
        order_type: OrderType = OrderType.LIMIT
        volume: float = strength * 10
        price: float = self.ticks[vt_symbol].last_price
        offset: Offset = Offset.CLOSE
        order_request: OrderRequest = OrderRequest(symbol, exchange, direction, order_type, volume, price, offset)



    def process_order_event(self, event: Event) -> None:
        """
        获取Order Event中的OrderData, 存入orders;
        检查订单状态, 维护所有的active订单(active_orders), 存入或踢出;
        调用该gateway的converter, 完成委托(下单)后具体的仓位处理逻辑
        """
        order: OrderData = event.data
        self.orders[order.vt_orderid] = order

        # If order is active, then update data in dict.
        if order.is_active():
            self.active_orders[order.vt_orderid] = order
        # Otherwise, pop inactive order from in dict
        elif order.vt_orderid in self.active_orders:
            self.active_orders.pop(order.vt_orderid)


    def process_trade_event(self, event: Event) -> None:
        """
        获得Trade Event中的TradeData, 存入trades;
        调用该gateway的converter, 完成成交后具体的仓位处理逻辑
        """
        trade: TradeData = event.data
        self.trades[trade.vt_tradeid] = trade
