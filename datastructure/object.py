'''
数据结构
'''
from dataclasses import dataclass
from datetime import datetime
from logging import INFO

from .constant import *
from .definition import  ACTIVE_STATUSES

@dataclass
class TickData:
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
class BarData:
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
class SignalData:
    '''
    策略产生的信号信息
    '''
    symbol: str
    exchange: Exchange
    datetime: datetime
    direction: Direction
    strength: float
    


@dataclass
class OrderData:
    """
    某委托(order)的最新状态
    """

    symbol: str
    exchange: Exchange
    orderid: str

    type: OrderType = OrderType.LIMIT
    direction: Direction = None
    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    traded: float = 0
    status: Status = Status.SUBMITTING
    datetime: datetime
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
class TradeData:
    """
    成交(trade, fill of order)信息
    One order can have several trade fills.
    """

    symbol: str
    exchange: Exchange
    orderid: str
    tradeid: str
    direction: Direction = None

    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    datetime: datetime = None
    gateway_name: str = ''


@dataclass
class PositionData:
    """
    每只标的的仓位信息
    """

    symbol: str
    exchange: Exchange
    direction: Direction

    volume: float = 0
    frozen: float = 0
    price: float = 0
    pnl: float = 0
    gateway_name: str = ''


@dataclass
class AccountData:
    """
    账户信息: 当前余额、冻结金额、可用金额
    """

    accountid: str
    balance: float = 0
    frozen: float = 0
    gateway_name: str = ''



@dataclass
class LogData:
    """
    日志信息
    """

    msg: str
    level: int = INFO

    def __post_init__(self) -> None:
        """"""
        self.time: datetime = datetime.now()

@dataclass
class ContractData:
    """
    每个合约的详细信息
    """

    symbol: str
    exchange: Exchange
    size: float
    pricetick: float
    min_volume: float = 1           # minimum trading volume of the contract


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
    type: OrderType
    volume: float
    price: float = 0
    offset: Offset = Offset.NONE
    # reference: str = ""

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        order: OrderData = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=orderid,
            type=self.type,
            direction=self.direction,
            offset=self.offset,
            price=self.price,
            volume=self.volume,
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

