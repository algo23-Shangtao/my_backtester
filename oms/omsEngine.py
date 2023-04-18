from abc import ABC
from pathlib import Path
from datetime import datetime

from typing import Any, Type, Dict, List

from core.event import Event, EventEngine
from core.event import EVENT_TICK, EVENT_STRATEGY, EVENT_ORDER, EVENT_TRADE, EVENT_REQUEST
from core.engine import BaseEngine
from gw.gateway import BaseGateway
from datastructure.constant import Direction, Offset, OrderType, Status, PosDate
from datastructure.object import (CancelRequest, LogData, OrderRequest, 
                                  HistoryRequest, OrderData, TickData, SignalData, 
                                  TradeData, PositionData, AccountData, ContractData, Exchange)


class OmsEngine(BaseEngine):
    '''
    '''
    def __init__(self, event_engine: EventEngine) -> None:
        super(OmsEngine, self).__init__(event_engine, "oms")
        # 内部信息
        self.contracts: Dict[str, ContractData] = {} # {symbol: contract} # 记录合约信息
        self.ticks: Dict[str, TickData] = {} # {symbol: tick} # 记录最新的tick
        self.active_orders: Dict[str, OrderData] = {}
        self.orders: Dict[str, OrderData] = {} # {orderid: order} # 记录所有订单
        self.trades: Dict[str, TradeData] = {} # {tradeid: trade} # 记录所有成交

        self.positions: Dict[str, PositionData] = {} # {positionid: position}
        self.account: AccountData = AccountData(accountid='backtestAccount', margin=10000)
        # 与simExchange互动
        self.order_reqs: List[OrderRequest] = []
        self.register_event()
        
    # 注册回调函数
    def register_event(self) -> None:
        """注册回调函数"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_STRATEGY, self.process_signal_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        

    # 各种事件处理逻辑(回调函数实现)
    def process_tick_event(self, event: Event) -> None:
        """获取Tick Event中的TickData, 存入ticks, 仅存最新的时间, 根据最新行情更新账户信息"""
        tick: TickData = event.data
        # 更新最新行情信息
        self.tick_update_ticks(tick)
        # 更新持仓盈亏
        self.tick_update_positions(tick)
        # 更新动态权益和可用资金
        self.tick_update_account(tick)
            
    def tick_update_ticks(self, tick: TickData) -> None:
        symbol: str = tick.symbol
        self.ticks[symbol] = tick

    def tick_update_positions(self, tick: TickData) -> None:
        # 获得行情中有用字段
        symbol: str = tick.symbol
        last_price: float = tick.last_price
        # 获得目标合约的多空仓位
        long_posid: str = f"{symbol}.1"
        short_posid: str = f"{symbol}.-1"
        long_pos: PositionData = self.positions.get(long_posid, None)
        short_pos: PositionData = self.positions.get(short_posid, None)
        # 更新多空仓位
        if long_pos:
            # 遍历每一笔历史仓位, 计算该仓的持仓盈亏
            all_pnl = 0
            for record in long_pos.record_list:
                record.pnl = (last_price - record.price) * record.volume
                all_pnl += record.pnl
            # 更新持仓盈亏
            long_pos.all_pnl = all_pnl
        
        if short_pos:
            all_pnl = 0
            for record in short_pos.record_list:
                record.pnl = -(last_price - record.price) * record.volume
                all_pnl += record.pnl
            # 更新持仓盈亏
            short_pos.all_pnl = all_pnl

    def tick_update_account(self, tick: TickData) -> None:
        # 遍历所有持仓, 更新账户中持仓盈亏
        acc = self.account
        hold_pnl: float = 0
        float_pnl: float = 0
        for pos in self.positions.values():
            hold_pnl += pos.all_pnl
            # 计算浮动盈亏
            for record in pos.record_list:
                if record.pos_date == PosDate.TODAY:
                    float_pnl += record.pnl
        acc.hold_pnl = hold_pnl
        acc.float_pnl = float_pnl

        acc.dynamic_equity = acc.stable_equity + acc.trade_pnl + acc.hold_pnl
        acc.balance = acc.dynamic_equity - acc.ocupying_margin - acc.frozen_margin - acc.frozen_commission



    def process_signal_event(self, event: Event) -> None:
        '''获取Signal Event中的SignalData, 存入signals, 并根据信号产生下单请求'''
    


    def process_order_event(self, event: Event) -> None:
        """
        获取Order Event中的OrderData, 更新订单状态;
        检查订单状态, 维护所有的active订单(active_orders), 存入或踢出;
        """
        order: OrderData = event.data
        self.order_update_orders(order)
        self.order_update_positions(order)
        self.order_update_account(order)
    
    def order_update_orders(self, order: OrderData) -> None:
        # 更新所有委托单
        self.orders[order.orderid] = order
        # 更新未成交单(挂单)
        if order.is_active():
            self.active_orders[order.orderid] = order
        elif order.orderid in self.active_orders:
            self.active_orders.pop(order.orderid)
    
    def order_update_positions(self, order: OrderData) -> None:
        # 根据订单状态更新持仓信息
        symbol: str = order.symbol
        direction: Direction = order.direction
        offset: Offset = order.offset
        status: Status = order.status
        order_volume: float = order.order_volume

        if status == Status.NOTTRADED and offset == Offset.CLOSE: # 平仓--可平量变化
            if direction == Direction.LONG: # 平空仓
                short_posid: str = f"{symbol}.-1"
                short_pos: PositionData = self.positions[short_posid]
                short_pos.available -= order_volume
            if direction == Direction.SHORT: # 平多仓
                long_posid: str = f"{symbol}.1"
                long_pos: PositionData = self.positions[long_posid]
                long_pos.available
        
    def order_update_account(self, order: OrderData) -> None:
        # 根据订单状态更新账户资金
        symbol: str = order.symbol
        direction: Direction = order.direction
        offset: Offset = order.offset
        status: Status = order.status
        order_volume: float = order.order_volume        
        order_price: float = order.order_price
        acc:AccountData = self.account
        contract: ContractData = self.contracts[symbol]
        margin_rate: float = contract.margin_rate
        commission_rate: float = contract.commission_rate
        size: float = contract.size
        if status == Status.NOTTRADED:
            acc.frozen_margin: float = order_price * order_volume * size * margin_rate
            acc.frozen_commission: float = order_price * order_volume * size * commission_rate
            

        






    # 手续费计算: https://zhuanlan.zhihu.com/p/424461900
    def process_trade_event(self, event: Event) -> None:
        """
        获得Trade Event中的TradeData, 存入trades;
        根据成交信息更新仓位信息, 账户信息
        """
        trade: TradeData = event.data
        self.trades[trade.tradeid] = trade
        
        symbol: str = trade.symbol
        exchange: Exchange = trade.exchange
        direction: Direction = trade.direction
        volume: float = trade.volume
        price: float = trade.price
        offset: Offset = trade.offset
        pos: PositionData = self.positions.get(symbol)
        
        if not pos: # 新增持仓
            new_pos: PositionData = PositionData(symbol, exchange, direction, volume, 0, price, 0)
            
        else: # 原有持仓
            last_pos: PositionData = self.positions[symbol]
            if offset == Offset.OPEN:
                new_pos: PositionData = PositionData(symbol, exchange, last_pos.direction, last_pos.volume + volume, last_pos.frozen, )

        

        self.positions[symbol] = new_pos

            

    
    
    
    
    
    def output(self, msg) -> None:
        print(f"{datetime.now()} omsEngine: {msg}")
        



# balance: 10000, frozen: 0
# open order req(10元 1手) -> exchange: order_event -> balance: 10000, frozen: 10
# trade (10yuan, 1shou) -> 