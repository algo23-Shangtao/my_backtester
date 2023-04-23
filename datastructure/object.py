'''
数据结构
'''
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from logging import INFO

from .constant import *
from .definition import  ACTIVE_STATUSES

class BaseData:
    gateway_name: str = ""

@dataclass
class TickData(BaseData):
    '''
    Level1 Tick data (snap shot)
    https://maimai.cn/article/detail?fid=1756736735&efid=u70pvigmHhoosM5GRS9x3g
    '''
    symbol: str
    exchange: Exchange
    datetime: datetime
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    last_price: float = 0
    highest_price: float = 0
    lowest_price: float = 0
    bid_price_1: float = 0
    ask_price_1: float = 0
    bid_volume_1: float = 0
    ask_volume_1: float = 0


@dataclass
class BarData(BaseData):
    """
    Bar data
    """

    symbol: str
    exchange: Exchange
    datetime: datetime

    interval: Interval = None
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    close_price: float = 0


@dataclass
class SignalData(BaseData):
    '''
    策略产生的信号信息
    '''
    datetime: datetime
    direction: Direction
    strength: float = 1

    


@dataclass
class OrderData(BaseData):
    """
    某委托(order)的最新状态
    """

    symbol: str
    exchange: Exchange
    orderid: str

    datetime: datetime
    type: OrderType = OrderType.LIMIT
    direction: Direction = None
    offset: Offset = Offset.NONE
    order_price: float = 0
    order_volume: float = 0
    traded: float = 0
    status: Status = Status.SUBMITTING
    reference: str = "" # ?
    gateway_name: str = ""


    def is_active(self) -> bool:
        """
        Check if the order is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from order.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.orderid, symbol=self.symbol, exchange=self.exchange
        )
        return req

@dataclass
class TradeData(BaseData):
    """
    成交(trade, fill of order)信息
    One order can have several trade fills.
    """

    symbol: str
    exchange: Exchange
    orderid: str
    tradeid: str
    datetime: datetime

    direction: Direction = None
    offset: Offset = Offset.NONE
    fill_price: float = 0
    fill_volume: float = 0
    
    gateway_name: str = ''


# @dataclass
# class PositionRecordData(BaseData):
#     ''''''
#     datetime: datetime
#     volume: float               # 该仓持仓量
#     price: float                # 该仓成交价
#     pnl: float                  # 该仓持仓盈亏
#     pos_date: PosDate           # 该仓为今仓or昨仓


@dataclass
class PositionData(BaseData):
    """
    每只标的的仓位信息
    """

    symbol: str
    exchange: Exchange
    direction: Direction
    all_volume: float = 0       # 总持仓
    # all_pnl: float = 0          # 持仓盈亏
    # yd_volume: float = 0        # 昨仓
    # td_volume: float = 0        # 今仓
    # available: float = 0        # 可平量
    # average_price: float = 0    # 持仓均价
    # occupying_margin: float = 0 # 占用保证金
    gateway_name: str = ''
    
    # record_list: List[PositionRecordData] = field(default_factory=list)  # 历史持仓记录
    
    def __post_init__(self) -> None:
        self.positionid: str = f"{self.symbol}.{str(self.direction)}"




@dataclass
class AccountData(BaseData):
    """
    账户信息: 当前余额、冻结金额、可用金额
    """
    stable_equity: float = 0       # 静态权益
    trade_pnl: float = 0            # 平仓盈亏
    hold_pnl: float = 0             # 持仓盈亏
    float_pnl: float = 0           # 浮动盈亏
    dynamic_equity: float = 0      # 动态权益
    ocupying_margin: float = 0     # 占用保证金
    frozen_margin: float = 0       # 冻结保证金
    frozen_commission: float = 0    # 冻结手续费
    commission: float = 0          # 手续费(用来记录最近一次委托的手续费)
    balance: float = 0             # 可用资金
    



@dataclass
class LogData(BaseData):
    """
    日志信息
    """

    msg: str
    level: int = INFO

    def __post_init__(self) -> None:
        """"""
        self.time: datetime = datetime.now()

@dataclass
class ContractData(BaseData):
    """
    每个合约的详细信息
    平仓手续费: https://zhuanlan.zhihu.com/p/424461900
    """

    symbol: str
    exchange: Exchange
    size: float                 # 合约乘数
    pricetick: float            # 最小变动价格
    margin_rate: float          # 保证金率
    commission_rate: float      # 手续费率


@dataclass
class SubscribeRequest:
    """
    向交易接口(gateway)发送订阅行情信息的请求(subscribe request)
    """

    symbol: str
    exchange: Exchange



@dataclass
class OrderRequest:
    """
    向交易接口(gateway)发送委托的请求(order request)
    http://www.khqihuo.com/qhdy/443.html
    """

    symbol: str
    exchange: Exchange
    direction: Direction
    datetime: datetime
    volume: float
    price: float
    offset: Offset
    type: OrderType = OrderType.LIMIT
    # reference: str = ""

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        order: OrderData = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=orderid,
            datetime=self.datetime,
            type=self.type,
            direction=self.direction,
            offset=self.offset,
            order_price=self.price,
            order_volume=self.volume,
            gateway_name=gateway_name,
        )
        return order


@dataclass
class CancelRequest:
    """
    向交易接口(gateway)发送撤销现有订单请求(cancel request)
    """

    orderid: str
    symbol: str
    exchange: Exchange


@dataclass
class HistoryRequest: # ?
    """
    向交易接口(gateway)发送查询历史数据请求(history request)
    """

    symbol: str
    exchange: Exchange
    start: datetime
    end: datetime = None
    interval: Interval = None

