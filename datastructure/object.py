'''
数据结构
'''
from dataclasses import dataclass
from datetime import datetime
from logging import INFO

from constant import *
from definition import  ACTIVE_STATUSES
@dataclass
class BaseData:
    '''
    Data对象的父类
    '''
    gateway_name: str
    # extra: dict = field(default=None, init=False)

@dataclass
class TickData(BaseData):
    '''
    Level1 Tick data (snap shot)
    https://maimai.cn/article/detail?fid=1756736735&efid=u70pvigmHhoosM5GRS9x3g
    '''
    symbol: str
    exchange: Exchange
    datetime: datetime

    # name: str = ""
    volume: float = 0
    turnover: float = 0
    open_interest: float = 0
    last_price: float = 0
    # last_volume: float = 0
    # limit_up: float = 0
    # limit_down: float = 0

    highest_price: float = 0
    lowest_price: float = 0
    # average_price: float = 0
    # open_price: float = 0 # ?
    # high_price: float = 0 # ? 
    # low_price: float = 0 # ?
    # pre_close: float = 0 # ?

    bid_price_1: float = 0
    # bid_price_2: float = 0
    # bid_price_3: float = 0
    # bid_price_4: float = 0
    # bid_price_5: float = 0

    ask_price_1: float = 0
    # ask_price_2: float = 0
    # ask_price_3: float = 0
    # ask_price_4: float = 0
    # ask_price_5: float = 0

    bid_volume_1: float = 0
    # bid_volume_2: float = 0
    # bid_volume_3: float = 0
    # bid_volume_4: float = 0
    # bid_volume_5: float = 0

    ask_volume_1: float = 0
    # ask_volume_2: float = 0
    # ask_volume_3: float = 0
    # ask_volume_4: float = 0
    # ask_volume_5: float = 0

    # localtime: datetime = None # ?

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

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

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class OrderData(BaseData):
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
    datetime: datetime = None
    reference: str = "" # ?

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_orderid: str = f"{self.gateway_name}.{self.orderid}"

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
class StopOrder(BaseData):
    vt_symbol: str
    direction: Direction
    offset: Offset
    price: float
    volume: float
    stop_orderid: str
    # strategy_name: str
    datetime: datetime
    lock: bool = False
    net: bool = False
    # vt_orderids: list = field(default_factory=list)
    status: StopOrderStatus = StopOrderStatus.WAITING

@dataclass
class QuoteData(BaseData): # ? order是普通投资者用的委托指令，quote则是做市商才会用到的双边报价指令，一般忽略即可
    """
    Quote data contains information for tracking lastest status
    of a specific quote.
    """

    symbol: str
    exchange: Exchange
    quoteid: str

    bid_price: float = 0.0
    bid_volume: int = 0
    ask_price: float = 0.0
    ask_volume: int = 0
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    status: Status = Status.SUBMITTING
    datetime: datetime = None
    reference: str = "" # ?

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_quoteid: str = f"{self.gateway_name}.{self.quoteid}"

    def is_active(self) -> bool:
        """
        Check if the quote is active.
        """
        return self.status in ACTIVE_STATUSES

    def create_cancel_request(self) -> "CancelRequest":
        """
        Create cancel request object from quote.
        """
        req: CancelRequest = CancelRequest(
            orderid=self.quoteid, symbol=self.symbol, exchange=self.exchange
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
    direction: Direction = None

    offset: Offset = Offset.NONE
    price: float = 0
    volume: float = 0
    datetime: datetime = None

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_orderid: str = f"{self.gateway_name}.{self.orderid}"
        self.vt_tradeid: str = f"{self.gateway_name}.{self.tradeid}"

@dataclass
class PositionData(BaseData):
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
    yd_volume: float = 0

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"
        self.vt_positionid: str = f"{self.gateway_name}.{self.vt_symbol}.{self.direction.value}"

@dataclass
class AccountData(BaseData):
    """
    账户信息: 当前余额、冻结金额、可用金额
    """

    accountid: str

    balance: float = 0
    frozen: float = 0

    def __post_init__(self) -> None:
        """"""
        self.available: float = self.balance - self.frozen
        self.vt_accountid: str = f"{self.gateway_name}.{self.accountid}"

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
    """

    symbol: str
    exchange: Exchange
    name: str
    product: Product
    size: float
    pricetick: float

    min_volume: float = 1           # minimum trading volume of the contract
    stop_supported: bool = False    # whether server supports stop order
    net_position: bool = False      # whether gateway uses net position volume
    history_data: bool = False      # whether gateway provides bar history data

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

@dataclass
class SubscribeRequest:
    """
    向交易接口(gateway)发送订阅行情信息的请求(subscribe request)
    """

    symbol: str
    exchange: Exchange

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


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
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_order_data(self, orderid: str, gateway_name: str) -> OrderData:
        """
        order request -> order
        """
        order: OrderData = OrderData(
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=orderid,
            type=self.type,
            direction=self.direction,
            offset=self.offset,
            price=self.price,
            volume=self.volume,
            reference=self.reference,
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

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


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

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"


@dataclass
class QuoteRequest: # ?
    """
    Request sending to specific gateway for creating a new quote.
    """

    symbol: str
    exchange: Exchange
    bid_price: float
    bid_volume: int
    ask_price: float
    ask_volume: int
    bid_offset: Offset = Offset.NONE
    ask_offset: Offset = Offset.NONE
    reference: str = ""

    def __post_init__(self) -> None:
        """"""
        self.vt_symbol: str = f"{self.symbol}.{self.exchange.value}"

    def create_quote_data(self, quoteid: str, gateway_name: str) -> QuoteData:
        """
        Create quote data from request.
        """
        quote: QuoteData = QuoteData(
            symbol=self.symbol,
            exchange=self.exchange,
            quoteid=quoteid,
            bid_price=self.bid_price,
            bid_volume=self.bid_volume,
            ask_price=self.ask_price,
            ask_volume=self.ask_volume,
            bid_offset=self.bid_offset,
            ask_offset=self.ask_offset,
            reference=self.reference,
            gateway_name=gateway_name,
        )
        return quote
