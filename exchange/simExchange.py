from typing import Any, Dict, List, Optional, Callable
from copy import copy
from datetime import datetime, timedelta

from core.event import Event, EventEngine
from core.event import (EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, 
                   EVENT_ACCOUNT, EVENT_CONTRACT, EVENT_LOG, EVENT_QUOTE)

from datastructure.object import (TickData, OrderData, TradeData, PositionData, AccountData, 
                    ContractData, LogData, QuoteData, OrderRequest, CancelRequest, 
                    SubscribeRequest, HistoryRequest, QuoteRequest, Exchange, BarData)
from datastructure.constant import EngineType, Interval, Status, OrderType, Direction
from datastructure.definition import INTERVAL_DELTA_MAP
from gw.gateway import BaseGateway
from gw.to_backtest import BacktestGateway
from db.database import get_database, BaseDatabase



class SimExchange:
    '''模拟交易所: 产生行情更新, 撮合交易'''
    def __init__(self, gateway: BacktestGateway) -> None:
        
        self.gateway: BacktestGateway = gateway
        # 回测时间
        self.start: datetime = None
        self.end: datetime = None
        # 回测时间内所有行情数据
        self.history_data: List[TickData] = []
        # 所有订单
        self.limit_order_count: int = 0
        self.limit_orders: Dict[str, OrderData] = {}
        self.active_limit_orders: Dict[str, OrderData] = {}
        # 所有成交
        self.trade_count: int = 0
        self.trades: Dict[str, TradeData] = {}
        # 最新行情数据
        self.tick: TickData = None
        self.datetime: datetime = None
        # 合约数据
        self.symbol_contract_map: Dict[str, ContractData] = {}

    def subscribe(self) -> None:
        symbol = self.gateway.subscribe_contract.symbol
        exchange = self.gateway.subscribe_contract.exchange
        self.load_history_data(symbol, exchange)
        

    def load_history_data(self, symbol, exchange) -> None:

        self.output('根据订阅合约, 加载历史行情中')
        self.history_data.clear()
        db: BaseDatabase = get_database()
        total_days: int = (self.end - self.start).days
        batch_days: int = max(total_days / 10, 1)
        batch_size: timedelta = timedelta(days=batch_days)
        interval_delta: timedelta = INTERVAL_DELTA_MAP[Interval.TICK]
        start: datetime = self.start
        end: datetime = self.start + batch_size
        progress: int = 0
        while start < self.end:
            progress += batch_days / total_days
            ticks: List[TickData] = db.load_tick_data(symbol, exchange, start, end)
            self.history_data.extend(ticks)
            progress_bar: str = '#' * int(progress * 10)
            self.output(f"历史行情加载进度:{progress_bar}({progress:.0%})")
            start = end + interval_delta
            end = start + batch_size
        self.output('历史行情加载完成')

        
    
    def publish_md(self) -> None:
        for tick in self.history_data:
            tick_event: Event = Event(EVENT_TICK, tick)
            self.gateway.on_tick(tick_event)
            self.tick = tick
            self.datetime = tick.datetime
            yield(tick)
        
    def send_limit_order(self) -> None:
        #### TODO 缺少检查资金是否足够下单的逻辑-reject
        req: OrderRequest = self.gateway.order_req
        self.limit_order_count += 1
        orderid = str(self.limit_order_count)
        order: OrderData = req.create_order_data(orderid, self.gateway.gateway_name)
        if order.type != OrderType.LIMIT:
            return
        if order.status == Status.SUBMITTING:
            self.limit_orders[order.vt_orderid] = order
            self.active_limit_orders[order.vt_orderid] = order
            submitted_order = copy(order)
            self.gateway.on_order(submitted_order)
            

    def cancel_limit_order(self) -> None:
        req: CancelRequest = self.gateway.cancel_req
        cancel_vt_orderid = f"{self.gateway.gateway_name}.{req.orderid}"
        if cancel_vt_orderid not in self.limit_orders:
            self.output('不存在此订单, 取消订单失败')
            return
        order: OrderData = self.limit_orders[cancel_vt_orderid]
        if order.status != Status.CANCELLED:
            order.status = Status.CANCELLED
        if cancel_vt_orderid in self.active_limit_orders:
            self.active_limit_orders.pop(cancel_vt_orderid)
        cancelled_order: OrderData = copy(order)
        self.gateway.on_order(cancelled_order)

            
    def cross_limit_order(self) -> None:
        '''
        根据最新的行情信息, 得到可以成交的价格
        遍历所有active委托: 1.接收提交中委托, 执行策略on order回调 2.尝试撮合该委托 TODO 有bug--没有考虑部分成交
        若成交, 则产生成交信息TradeData, 执行策略on trade回调

        '''
        # 由最新行情数据得到成交价
        long_cross_price = self.tick.ask_price_1 # 可成交的买价的下限-卖1价
        short_cross_price = self.tick.bid_price_1 # 可成交的卖价的上限-买1价
        long_best_price = long_cross_price # 真实成交买价
        short_best_price = short_cross_price # 真实成交卖价

        # 遍历所有active委托  @TODO 没有做到价格优先
        for order in list(self.active_limit_orders.values()):
            # 接收提交中委托, 执行策略on order回调
            if order.status == Status.SUBMITTING:
                order.status = Status.NOTTRADED
                ntraded_order: OrderData = copy(order)
                self.gateway.on_order(ntraded_order)
            # 尝试撮合该委托
            long_cross: bool = (
                order.direction == Direction.LONG
                and order.price >= long_cross_price
                and long_cross_price > 0
            )
            short_cross: bool = {
                order.direction == Direction.SHORT
                and order.price <= short_cross_price
                and short_cross_price > 0
            }
            # 这个订单成交不了, 下一个
            if not long_cross and not short_cross:
                continue
            # 可以成交, 委托状态变为全部成交(这种适用于一次只下一手的情况)
            order.traded = order.volume
            order.status = Status.ALLTRADED
            alltraded_order = copy(order)
            self.gateway.on_order(alltraded_order)
            if order.vt_orderid in self.active_limit_orders:
                self.active_limit_orders.pop(order.vt_orderid)
            
            # 产生成交事件, 执行策略on trade回调
            self.trade_count += 1
            if long_cross:
                trade_price = min(order.price, long_best_price)
                # pos_change = order.volume
            else:
                trade_price = max(order.price, short_best_price)
                # pos_change = -order.volume
            
            trade: TradeData = TradeData(
                symbol=order.symbol,
                exchange= order.exchange,
                orderid=order.orderid,
                tradeid=str(self.trade_count),
                direction=order.direction,
                offset=order.offset,
                price=trade_price,
                volume=order.volume,
                datetime=self.datetime,
                gateway_name=self.gateway.gateway_name
            )
            self.trades[trade.vt_tradeid] = trade
            trade = copy(trade)
            self.gateway.on_trade(trade)
            
    


    
    
    def output(self, msg) -> None:
        print(f"{datetime.now()} simExchange: {msg}" )