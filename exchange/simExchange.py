from typing import Any, Dict, List, Optional, Callable
from copy import copy
from datetime import datetime, timedelta

from core.event import Event, EventEngine
from core.event import EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_LOG

from datastructure.object import (TickData, OrderData, TradeData, PositionData, AccountData, 
                    ContractData, LogData, OrderRequest, CancelRequest, 
                    SubscribeRequest, HistoryRequest, Exchange, BarData)
from datastructure.constant import Interval, Status, OrderType, Direction
from datastructure.definition import INTERVAL_DELTA_MAP
from gw.gateway import BaseGateway
from db.database import get_database, BaseDatabase



class SimExchange:
    '''模拟交易所: 产生行情更新, 撮合交易'''
    def __init__(self, event_engine: EventEngine, start: datetime, end: datetime) -> None:
        
        self.gateway: BaseGateway = BaseGateway(event_engine, 'backtest')
        # 回测时间
        self.start: datetime = start
        self.end: datetime = end
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

        self._tick_generator = self._generate_new_tick()
        self.register_event()
        
    # 订阅合约
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

        
    def _generate_new_tick(self) -> TickData:
        for tick in self.history_data:
            yield(tick)

    def publish_md(self) -> TickData:
        try:
            tick: TickData = next(self._tick_generator)
        except StopIteration:
            self.output('历史数据回放完成')
        else:
            self.tick = tick
            self.datetime = tick.datetime
            self.gateway.on_tick(tick)
        return self.tick
        
    
    def register_event(self) -> None:
        self.gateway.event_engine.register(EVENT_TICK, self.process_tick_event)
    
    
    #### TODO 改用gateway
    def process_order_request(self, event: Event) -> None:
        '''接收订单, 订单状态为submitting'''
        order_req: OrderRequest = event.data
        self.limit_order_count += 1
        order: OrderData = order_req.create_order_data(self.limit_order_count, self.gateway.gateway_name) # status=submitting
        self.active_limit_orders[order.orderid] = order
        self.limit_orders[order.orderid] = order
        submitting_order: OrderData = copy(order)
        self.gateway.on_order(submitting_order)

    def process_tick_event(self, event: Event) -> None:
        self.cross_limit_order()

      
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

        # 遍历所有active委托  @TODO 价格优先时间优先
        for order in list(self.active_limit_orders.values()):
            # 接收提交中委托, 执行策略on order回调
            if order.status == Status.SUBMITTING:
                order.status = Status.NOTTRADED
                ntraded_order: OrderData = copy(order)
                self.gateway.on_order(ntraded_order)
            # 尝试撮合该委托
            long_cross: bool = (
                order.direction == Direction.LONG
                and order.order_price >= long_cross_price
                and long_cross_price > 0
            )
            short_cross: bool = {
                order.direction == Direction.SHORT
                and order.order_price <= short_cross_price
                and short_cross_price > 0
            }
            # 这个订单成交不了, 下一个
            if not long_cross and not short_cross:
                continue
            # 可以成交, 委托状态变为全部成交(这种适用于一次只下一手的情况)
            order.traded = order.order_volume
            order.status = Status.ALLTRADED
            alltraded_order = copy(order)
            self.gateway.on_order(alltraded_order)
            if order.orderid in self.active_limit_orders:
                self.active_limit_orders.pop(order.orderid)
            
            # 产生成交事件
            self.trade_count += 1
            if long_cross:
                trade_price = min(order.order_price, long_best_price)
                # pos_change = order.volume
            else:
                trade_price = max(order.order_price, short_best_price)
                # pos_change = -order.volume
            
            trade: TradeData = TradeData(
                symbol=order.symbol,
                exchange= order.exchange,
                orderid=order.orderid,
                tradeid=str(self.trade_count),
                direction=order.direction,
                offset=order.offset,
                fill_price=trade_price,
                fill_volume=order.traded,
                datetime=self.datetime,
                gateway_name=self.gateway.gateway_name
            )
            self.trades[trade.tradeid] = trade
            trade = copy(trade)
            self.gateway.on_trade(trade)
            
    


    
    
    def output(self, msg) -> None:
        print(f"{datetime.now()} simExchange: {msg}" )