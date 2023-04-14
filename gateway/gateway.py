from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from copy import copy

from event import Event, EventEngine
from event import (EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, 
                   EVENT_ACCOUNT, EVENT_CONTRACT, EVENT_LOG, EVENT_QUOTE)

from object import (TickData, OrderData, TradeData, PositionData, AccountData, 
                    ContractData, LogData, QuoteData, OrderRequest, CancelRequest, 
                    SubscribeRequest, HistoryRequest, QuoteRequest, Exchange, BarData)


class BaseGateway(ABC):
    '''
    连接不同交易系统的交易接口(Gateway)
    # How to implement a gateway:
    ---
    ## Basics
    A gateway should satisfies:
    * this class should be thread-safe:
        * all methods should be thread-safe
        * no mutable shared properties between objects.
    * all methods should be non-blocked
    * satisfies all requirements written in docstring for every method and callbacks.
    * automatically reconnect if connection lost.
    ---
    ## methods must implements:
    all @abstractmethod
    ---
    ## callbacks must response manually:
    * on_tick
    * on_trade
    * on_order
    * on_position
    * on_account
    * on_contract
    All the XxxData passed to callback should be constant, which means that
        the object should not be modified after passing to on_xxxx.
    So if you use a cache to store reference of data, use copy.copy to create a new object
    before passing that data into on_xxxx
    '''

    # default name for gateway
    default_name: str = ""

    # fields required in setting dict for connect function
    default_setting: Dict[str, Any] = {}

    # exchange supported in the gateway
    exchanges: List[Exchange] = []

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        self.event_engine: EventEngine = event_engine
        self.gateway_name: str = gateway_name

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
        self.on_event(EVENT_TICK + tick.vt_symbol, tick) # 为什么要再put一次?

    def on_trade(self, trade: TradeData) -> None:
        '''
        向event_engine的事件队列中放入成交事件(Trade event)
        Trade event of a specific vt_symbol is also pushed --- 防止重名?
        '''
    
    def on_order(self, order: OrderData) -> None:
        '''
        向event_engine的事件队列中放入下单事件(Order event)
        Order event of a specific vt_orderid is also pushed --- 防止重名?
        '''
        self.on_event(EVENT_ORDER, order)
        self.on_event(EVENT_ORDER + order.vt_orderid, order)

    def on_position(self, position: PositionData) -> None:
        '''
        向event_engine的事件队列中放入仓位更新事件(Position event)
        Position event of a specific vt_symbol is also pushed --- 防止重名?        
        '''
        self.on_event(EVENT_POSITION, position)
        self.on_event(EVENT_POSITION + position.vt_symbol, position)

    def on_account(self, account: AccountData) -> None:
        """
        向event_engine的事件队列中放入账户更新事件(Account event)
        Account event of a specific vt_accountid is also pushed.
        """
        self.on_event(EVENT_ACCOUNT, account)
        self.on_event(EVENT_ACCOUNT + account.vt_accountid, account)

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


    ## 下面是啥?
    def on_quote(self, quote: QuoteData) -> None:
        """
        Quote event push.
        Quote event of a specific vt_symbol is also pushed.
        """
        self.on_event(EVENT_QUOTE, quote)
        self.on_event(EVENT_QUOTE + quote.vt_symbol, quote)

    def on_contract(self, contract: ContractData) -> None:
        """
        Contract event push.
        """
        self.on_event(EVENT_CONTRACT, contract)

    @abstractmethod
    def connect(self, setting: dict) -> None:
        """
        Start gateway connection.
        to implement this method, you must:
        * connect to server if necessary
        * log connected if all necessary connection is established
        * do the following query and response corresponding on_xxxx and write_log
            * contracts : on_contract
            * account asset : on_account
            * account holding: on_position
            * orders of account: on_order
            * trades of account: on_trade
        * if any of query above is failed,  write log.
        future plan:
        response callback/change status instead of write_log
        """
        pass

    @abstractmethod
    def close(self) -> None:
        '''
        关闭与交易接口的连接
        '''
        pass

    @abstractmethod
    def subscribe(self, req: SubscribeRequest) -> None:
        '''
        订阅行情数据
        '''
        pass
    
    @abstractmethod
    def send_order(self, req: OrderRequest) -> str:
        '''
        Send a new order to server.
        implementation should finish the tasks blow:
        * create an OrderData from req using OrderRequest.create_order_data
        * assign a unique(gateway instance scope) id to OrderData.orderid
        * send request to server
            * if request is sent, OrderData.status should be set to Status.SUBMITTING
            * if request is failed to sent, OrderData.status should be set to Status.REJECTED
        * response on_order:
        * return vt_orderid
        :return str vt_orderid for created OrderData
        '''
        pass

    @abstractmethod
    def cancel_order(self, req: CancelRequest) -> None:
        '''
        取消现有的订单(order)
        send request to server
        '''
        pass

    @abstractmethod
    def send_quote(self, req: QuoteRequest) -> str:
        """
        Send a new two-sided quote to server.
        implementation should finish the tasks blow:
        * create an QuoteData from req using QuoteRequest.create_quote_data
        * assign a unique(gateway instance scope) id to QuoteData.quoteid
        * send request to server
            * if request is sent, QuoteData.status should be set to Status.SUBMITTING
            * if request is failed to sent, QuoteData.status should be set to Status.REJECTED
        * response on_quote:
        * return vt_quoteid
        :return str vt_quoteid for created QuoteData
        """
        pass

    @abstractmethod
    def cancel_quote(self, req: CancelRequest) -> None:
        '''
        取消现有的报价(quote)
        send request to server
        '''
        pass

    @abstractmethod
    def query_account(self) -> None:
        '''
        查询账户
        '''
        pass

    @abstractmethod
    def query_position(self) -> None:
        '''
        查询持仓
        '''
        pass

    @abstractmethod
    def query_history(self, req: HistoryRequest) -> None:
        '''
        查询历史数据
        '''
        pass

    @abstractmethod
    def get_default_setting(self) -> Dict[str, Any]:
        '''
        返回默认设置
        '''
        pass


####TODO 这个是啥
class LocalOrderManager:
    '''
    Management tool to support use local order id for trading. --- 本地orderid ? 系统orderid ?
    '''

    def __init__(self, gateway: BaseGateway, order_prefix: str = "") -> None:

        self.gateway: BaseGateway = gateway

        # for generating local orderid
        self.order_prefix: str = order_prefix
        self.order_count: int = 0
        self.orders: Dict[str, OrderData] = {} # local_orderid(order.orderid): order

        # Map between local and system orderid
        self.local_sys_orderid_map: Dict[str, str] = {}
        self.sys_local_orderid_map: Dict[str, str] = {}

        # Push order data buf
        self.push_data_buf: Dict[str, Dict] = {} # sys_orderid: data

        # Callback for processing push order data
        self.push_data_callback: Callable = None

        # Cancel request buf
        self.cancel_request_buf: Dict[str, CancelRequest] = {} # local_orderid: req

        # Hook cancel order function ???????????????????????????????????????????????????
        self._cancel_order: Callable = gateway.cancel_order
        gateway.cancel_order = self.cancel_order # ?????????????????????????????????????

    def new_local_orderid(self) -> str:
        '''
        产生一个新的local orderid
        '''
        self.order_count += 1
        local_orderid: str = self.order_prefix + str(self.order_count).rjust(8, "0")
        return local_orderid
    
    def get_sys_orderid(self, local_orderid: str) -> str:
        '''
        用local_orderid得到sys_orderid
        '''
        sys_orderid: str = self.local_sys_orderid_map.get(local_orderid, "")
        return sys_orderid


    def get_local_orderid(self, sys_orderid: str) -> str:
        '''
        用sys_orderid得到local_orderid
        若不存在对应local_orderid, 则产生一个
        更新orderid map
        '''
        local_orderid: str = self.sys_local_orderid_map.get(sys_orderid, "")
        if not local_orderid:
            local_orderid = self.new_local_orderid()
            self.update_orderid_map(local_orderid, sys_orderid)
        
        return local_orderid
    
    def update_orderid_map(self, local_orderid: str, sys_orderid: str) -> None:
        '''
        更新orderid map
        '''
        self.sys_local_orderid_map[sys_orderid] = local_orderid
        self.local_sys_orderid_map[local_orderid] = sys_orderid

        self.check_cancel_request(local_orderid)
        self.check_push_data(sys_orderid)
    
    def check_cancel_request(self, local_orderid: str) -> None:

        if local_orderid not in self.cancel_request_buf:
            return 
        req: CancelRequest = self.cancel_request_buf.pop(local_orderid)
        self.gateway.cancel_order(req)
    
    def check_push_data(self, sys_orderid: str) -> None:
        '''
        check if any order push data waiting
        '''
        if sys_orderid not in self.push_data_buf:
            return
        data: dict = self.push_data_buf.pop(sys_orderid)
        if self.push_data_callback:
            self.push_data_callback(data)
        
    def add_push_data(self, sys_orderid: str, data: dict) -> None:
        '''
        add push data into buf
        '''
        self.push_data_buf[sys_orderid] = data
    
    def get_order_with_sys_orderid(self, sys_orderid: str) -> Optional[OrderData]:
        local_orderid: str = self.sys_local_orderid_map.get(sys_orderid, None)
        if not local_orderid:
            return None
        else:
            return self.get_order_with_local_orderid(local_orderid)
    
    def get_order_with_local_orderid(self, local_orderid: str) -> OrderData:
        order: OrderData = self.orders[local_orderid]
        return copy(order)
    
    def on_order(self, order: OrderData) -> None:
        '''
        keep an order buf before pushing it to gateway
        '''
        self.orders[order.orderid] = copy(order) # 为什么不是vt.orderid
        self.gateway.on_order(order)
    
    def cancel_order(self, req: CancelRequest) -> None:
        sys_orderid: str = self.get_sys_orderid(req.orderid)
        if not sys_orderid:
            self.cancel_request_buf[req.orderid] = req
            return


