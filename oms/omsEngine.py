from abc import ABC
from pathlib import Path
from datetime import datetime, date
import pandas as pd
from typing import Any, Type, Dict, List, Optional
from collections import defaultdict

from core.event import Event, EventEngine
from core.event import EVENT_TICK, EVENT_STRATEGY, EVENT_ORDER, EVENT_TRADE, EVENT_REQUEST, EVENT_LOG
from core.engine import BaseEngine
from datastructure.constant import Direction, Offset, OrderType, Status, PosDate
from datastructure.object import (CancelRequest, LogData, OrderRequest, 
                                  HistoryRequest, OrderData, TickData, SignalData, 
                                  TradeData, PositionData, AccountData, ContractData, Exchange)


class OmsEngine(BaseEngine):
    '''
    '''
    def __init__(self, event_engine: EventEngine, contract) -> None:
        super(OmsEngine, self).__init__(event_engine, "oms")
        # 内部信息
        self.contract: ContractData = contract
        self.ticks: List[TickData] = []        # 记录最新的tick
        self.active_orders: Dict[str, OrderData] = {} # {orderid: order}
        self.orders: Dict[str, OrderData] = {} # {orderid: order} # 记录所有订单
        self.trades: Dict[str, TradeData] = {} # {tradeid: trade} # 记录所有成交

        self.positions: Dict[str, PositionData] = {} # {positionid: position}
        self.account: AccountData = AccountData()
        self.register_event()
        
    # 注册回调函数
    def register_event(self) -> None:
        """注册回调函数"""
        self.event_engine.register(EVENT_TICK, self.process_tick_event)
        self.event_engine.register(EVENT_STRATEGY, self.process_signal_event)
        self.event_engine.register(EVENT_ORDER, self.process_order_event)
        self.event_engine.register(EVENT_TRADE, self.process_trade_event)
        

    
    def process_tick_event(self, event: Event) -> None:
        self.output('处理行情更新')
        tick: TickData = event.data
        self.ticks.append(tick)

    def process_signal_event(self, event: Event) -> None:
        self.output('处理信号更新')
        signal: SignalData = event.data
        symbol = self.contract.symbol
        exchange = self.contract.exchange
        direction = signal.direction
        datetime = signal.datetime
        price = 10000
        
        long_pos: PositionData = self.positions.get(f"{self.contract.symbol}.{Direction.LONG}", None)
        short_pos: PositionData = self.positions.get(f"{self.contract.symbol}.{Direction.SHORT}", None)

        if signal.direction == Direction.LONG: # 多仓信号 - 反手开仓
            if short_pos:   # 平空仓
                req: OrderRequest = OrderRequest(symbol, 
                                                 exchange, 
                                                 direction,
                                                 datetime,
                                                 short_pos.all_volume,
                                                 price,
                                                 Offset.CLOSE)
                self.on_order_request(req)
                self.output('发生平空仓请求')
            if not long_pos:    # 开多仓
                req: OrderRequest = OrderRequest(symbol,
                                                 exchange,
                                                 direction,
                                                 datetime,
                                                 1,
                                                 price,
                                                 Offset.OPEN)
                self.on_order_request(req)
                self.output('发送开多仓请求')
        
        if signal.direction == Direction.SHORT: # 空仓信号 - 反手空仓
            if long_pos:    # 平多仓
                req: OrderRequest = OrderRequest(symbol, 
                                                 exchange, 
                                                 direction,
                                                 datetime, 
                                                 long_pos.all_volume,
                                                 price,
                                                 Offset.CLOSE)
                self.on_order_request(req)
                self.output('发生平多仓请求')
            if not short_pos:   # 开空仓
                req: OrderRequest = OrderRequest(symbol,
                                                 exchange,
                                                 direction,
                                                 datetime,
                                                 1,
                                                 price,
                                                 Offset.OPEN)
                self.on_order_request(req)
                self.output('发生开空仓请求')
    
    def process_order_event(self, event: Event) -> None:
        self.output('处理订单更新')
        order: OrderData = event.data
        if order.is_active():
            self.active_orders[order.orderid] = order
            self.orders[order.orderid] = order
        else:
            self.active_orders.pop(order.orderid)
        
    def process_trade_event(self, event: Event) -> None:
        self.output('处理成交更新')
        trade: TradeData = event.data
        
        if trade.offset == Offset.CLOSE:
            direction = Direction.LONG if trade.direction == Direction.SHORT else Direction.SHORT
            positionid: str = f"{trade.symbol}.{direction}"
            self.positions[positionid].all_volume -= trade.fill_volume
            if self.positions[positionid].all_volume <= 0:
                self.positions.pop(positionid)
        if trade.offset == Offset.OPEN:
            direction = trade.direction
            positionid: str = f"{trade.symbol}.{trade.direction}"
            pos: PositionData = self.positions.get(positionid)
            if pos:
                pos.all_volume += trade.fill_volume
            else:
                self.positions[positionid] = PositionData(trade.symbol, trade.exchange, trade.direction, trade.fill_volume)
    

    
    
    def output(self, msg) -> None:
        print(f"{datetime.now()} omsEngine: {msg}")
        
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
    
    def on_order_request(self, order_req: OrderRequest) -> None:
        '''
        发送订单请求
        '''
        self.on_event(EVENT_REQUEST, order_req)

    def on_log(self, log: LogData) -> None:
        """
        向event_engine的事件队列中放入日志记录事件(Log event)
        """
        self.on_event(EVENT_LOG, log)



































    def update_daily_close(self, price: float) -> None:
        '''更新盯市盈亏'''
        d: date = self.datetime.date()
        daily_result: Optional[DailyResult] = self.daily_results.get(d, None)
        if daily_result:
            daily_result.close_price = price
            # daily_result.pre_close在后面更新
        else:
            self.daily_results[d] = DailyResult(d, price)






    def calculate_result(self) -> pd.DataFrame:
        """"""
        self.output("开始计算逐日盯市盈亏")

        if not self.trades:
            self.output("成交记录为空，无法计算")
            return

        # Add trade data into daily reuslt.
        for trade in self.trades.values():
            d: date = trade.datetime.date()
            daily_result: DailyResult = self.daily_results[d]
            daily_result.add_trade(trade)

        # Calculate daily result by iteration.
        pre_close = 0
        start_pos = 0

        for daily_result in self.daily_results.values():
            daily_result.calculate_pnl(
                pre_close,
                start_pos,
                self.size,
                self.rate,
                self.slippage
            )
            pre_close = daily_result.close_price
            start_pos = daily_result.end_pos

        # Generate dataframe
        results: defaultdict = defaultdict(list)

        for daily_result in self.daily_results.values():
            for key, value in daily_result.__dict__.items():
                results[key].append(value)

        self.daily_df = pd.DataFrame.from_dict(results).set_index("date")

        self.output("逐日盯市盈亏计算完成")
        return self.daily_df

class DailyResult:
    """
    https://zhuanlan.zhihu.com/p/267211216
    """

    def __init__(self, date: date, close_price: float) -> None:
        """"""
        self.date: date = date
        self.close_price: float = close_price   # 当日结算价
        self.pre_close: float = 0               # 昨日结算价

        self.trades: List[TradeData] = []
        self.trade_count: int = 0

        self.start_pos = 0                      # 老仓？
        self.end_pos = 0                        # 

        self.turnover: float = 0
        self.commission: float = 0
        self.slippage: float = 0

        self.trading_pnl: float = 0             # 
        self.holding_pnl: float = 0             # 
        self.total_pnl: float = 0
        self.net_pnl: float = 0

    def add_trade(self, trade: TradeData) -> None:
        """"""
        self.trades.append(trade)

    def calculate_pnl(
        self,
        pre_close: float,
        start_pos: float,
        size: int,
        rate: float,
        slippage: float
    ) -> None:
        """"""
        # If no pre_close provided on the first day,
        # use value 1 to avoid zero division error
        if pre_close:
            self.pre_close = pre_close
        else:
            self.pre_close = 1

        # Holding pnl is the pnl from holding position at day start
        self.start_pos = start_pos
        self.end_pos = start_pos

        self.holding_pnl = self.start_pos * (self.close_price - self.pre_close) * size

        # Trading pnl is the pnl from new trade during the day
        self.trade_count = len(self.trades)

        for trade in self.trades:
            if trade.direction == Direction.LONG:
                pos_change = trade.fill_volume
            else:
                pos_change = -trade.fill_volume

            self.end_pos += pos_change

            turnover: float = trade.fill_volume * size * trade.fill_price # 成交价 × 成交手数 × 合约乘数
            self.trading_pnl += pos_change * (self.close_price - trade.fill_price) * size # ？
            
            self.slippage += trade.fill_volume * size * slippage  # 

            self.turnover += turnover
            self.commission += turnover * rate                            # 成交价 × 成交手数 × 合约乘数 × 手续费率

        # Net pnl takes account of commission and slippage cost
        self.total_pnl = self.trading_pnl + self.holding_pnl
        self.net_pnl = self.total_pnl - self.commission - self.slippage
