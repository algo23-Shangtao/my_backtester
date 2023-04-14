import logging
from logging import Logger
import os

from abc import ABC
from pathlib import Path
from datetime import datetime
from queue import Empty, Queue
from threading import Thread

from typing import Any, Type, Dict, List, Optional

from event import Event, EventEngine
from app import BaseApp
from event import (EVENT_TICK, EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, 
                   EVENT_ACCOUNT, EVENT_CONTRACT, EVENT_LOG, EVENT_QUOTE)
from gateway import BaseGateway
from object import (CancelRequest, LogData, OrderRequest, QuoteData, 
                    QuoteRequest, SubscribeRequest, HistoryRequest, 
                    OrderData, BarData, TickData, TradeData, PositionData, 
                    AccountData, ContractData, Exchange)
from setting import SETTING
from utils_function import get_folder_path, TRADER_DIR
from converter import OffsetConverter

class BaseEngine(ABC):
    '''
    function engine抽象类
    封装main_engine和event_engine
    封装处理event的回调函数, 并注册回调函数
    '''
    def __init__(self, main_engine: "MainEngine", event_engine: EventEngine, engine_name: str) -> None:
        self.main_engine: MainEngine = main_engine
        self.event_engine: EventEngine = event_engine
        self.engine_name: str = engine_name
    def close(self) -> None:
        pass

class LogEngine(BaseEngine):
    '''
    根据全局设置中日志设置, 封装一个Logger实例
    回调函数: 用Logger处理logEvent--输出日志
    '''
    def __init__(self, main_engine: "MainEngine", event_engine: EventEngine) -> None:
        super(LogEngine, self).__init__(main_engine, event_engine)
        # super(self).__init__(main_engine, event_engine)
        if not SETTING['log_active']:
            return
        self.level: int = SETTING['log.level']
        self.logger: Logger = logging.getLogger("tushetou")
        self.logger.setLevel(self.level)
        self.formatter: logging.Formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        self.add_null_handler()
        if SETTING["log.console"]:
            self.add_console_handler()
        if SETTING["log.file"]:
            self.add_file_handler()
        self.register_event()


    def add_null_handler(self) -> None:
        """
        Add null handler for logger.
        """
        null_handler: logging.NullHandler = logging.NullHandler()
        self.logger.addHandler(null_handler)

    def add_console_handler(self) -> None:
        """
        Add console output of log.
        """
        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def add_file_handler(self) -> None:
        """
        Add file output of log.
        """
        today_date: str = datetime.now().strftime("%Y%m%d")
        filename: str = f"vt_{today_date}.log"
        log_path: Path = get_folder_path("log")
        file_path: Path = log_path.joinpath(filename)

        file_handler: logging.FileHandler = logging.FileHandler(
            file_path, mode="a", encoding="utf8"
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def register_event(self) -> None:
        '''注册回调函数到eventEngine'''
        self.event_engine.register(EVENT_LOG, self.process_log_event)
    
    def process_log_event(self, event: Event) -> None:
        '''处理logEvent的回调函数'''
        log: LogData = event.data
        self.logger.log(log.level, log.msg)


class OmsEngine(BaseEngine):
    '''
    订单管理系统Oms
    封装了核心mainEngine和eventEngine
    封装了各种数据Dict以及OffsetConverter
    回调函数: 利用各种数据Dict和OffsetConverter实现处理各种event的逻辑
    查询函数: 查询封装的各种数据Dict
    '''
    def __init__(self, main_engine: "MainEngine", event_engine: EventEngine) -> None:
        super(OmsEngine, self).__init__(main_engine, event_engine, "oms")
        
        self.ticks: Dict[str, TickData] = {} # {vt_symbol: tick}
        self.orders: Dict[str, OrderData] = {} # {vt_orderid: order}
        self.trades: Dict[str, TradeData] = {} # {vt_tradeid: trade}
        self.positions: Dict[str, PositionData] = {} # {vt_positionid: position}
        self.accounts: Dict[str, AccountData] = {} # {vt_accountid: account}
        self.contracts: Dict[str, ContractData] = {} # {vt_symbol: contract}
        self.quotes: Dict[str, QuoteData] = {} # {vt_quoteid: quote}
        self.active_orders: Dict[str, OrderData] = {} # {vt_orderid: order}
        self.active_quotes: Dict[str, QuoteData] = {} # {vt_quoteid: quote}
        self.offset_converters: Dict[str, OffsetConverter] = {} # {gateway_name: converter}

        self.add_function()
        self.register_event()
    
    # 在干吗?
    def add_function(self) -> None:
        '''将相关查询函数加入main_engine''' #### 为啥啊?OmsEngine即是main_engine??
        self.main_engine.get_tick = self.get_tick
        self.main_engine.get_order = self.get_order
        self.main_engine.get_trade = self.get_trade
        self.main_engine.get_position = self.get_position
        self.main_engine.get_account = self.get_account
        self.main_engine.get_contract = self.get_contract
        self.main_engine.get_quote = self.get_quote

        self.main_engine.get_all_ticks = self.get_all_ticks
        self.main_engine.get_all_orders = self.get_all_orders
        self.main_engine.get_all_trades = self.get_all_trades
        self.main_engine.get_all_positions = self.get_all_positions
        self.main_engine.get_all_accounts = self.get_all_accounts
        self.main_engine.get_all_contracts = self.get_all_contracts
        self.main_engine.get_all_quotes = self.get_all_quotes
        self.main_engine.get_all_active_orders = self.get_all_active_orders
        self.main_engine.get_all_active_quotes = self.get_all_active_quotes

        self.main_engine.update_order_request = self.update_order_request
        self.main_engine.convert_order_request = self.convert_order_request
        self.main_engine.get_converter = self.get_converter

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

        # Update to offset converter
        converter: OffsetConverter = self.offset_converters.get(order.gateway_name, None)
        if converter:
            converter.update_order(order)

    def process_trade_event(self, event: Event) -> None:
        """
        获得Trade Event中的TradeData, 存入trades;
        调用该gateway的converter, 完成成交后具体的仓位处理逻辑
        """
        trade: TradeData = event.data
        self.trades[trade.vt_tradeid] = trade

        # Update to offset converter
        converter: OffsetConverter = self.offset_converters.get(trade.gateway_name, None)
        if converter:
            converter.update_trade(trade)

    def process_position_event(self, event: Event) -> None:
        """
        获得Position Event中的PositionData, 存入positions
        调用该gateway的converter, 完成仓位变动后具体的仓位处理逻辑
        """
        #### 所以Position Event是什么鬼? 谁产生的?
        position: PositionData = event.data
        self.positions[position.vt_positionid] = position

        # Update to offset converter
        converter: OffsetConverter = self.offset_converters.get(position.gateway_name, None)
        if converter:
            converter.update_position(position)

    def process_account_event(self, event: Event) -> None:
        """
        获得Account Event中的AccountData, 存入accounts
        """
        #### 所以Account Event是什么鬼? 谁产生的?
        account: AccountData = event.data
        self.accounts[account.vt_accountid] = account

    def process_contract_event(self, event: Event) -> None:
        """
        获得Contract Event中的ContractData, 存入contracts
        对于一个新合约(?), 判断是否有其所属交易接口的converter, 没有则创建一个
        """
        #### 所以Contract Event是什么鬼? 谁产生的?
        contract: ContractData = event.data
        self.contracts[contract.vt_symbol] = contract

        # Initialize offset converter for each gateway
        if contract.gateway_name not in self.offset_converters:
            self.offset_converters[contract.gateway_name] = OffsetConverter(self) # 怎么把self(OmsEngine)传进去了?！

    def process_quote_event(self, event: Event) -> None:
        """
        获取Quote Event中的QuoteData, 存入quotes;
        检查订单状态, 维护所有的active订单(active_quotes, 存入或踢出;
        """
        quote: QuoteData = event.data
        self.quotes[quote.vt_quoteid] = quote

        # If quote is active, then update data in dict.
        if quote.is_active():
            self.active_quotes[quote.vt_quoteid] = quote
        # Otherwise, pop inactive quote from in dict
        elif quote.vt_quoteid in self.active_quotes:
            self.active_quotes.pop(quote.vt_quoteid)

    # 数据查询函数
    def get_tick(self, vt_symbol: str) -> Optional[TickData]:
        """
        Get latest market tick data by vt_symbol.
        """
        return self.ticks.get(vt_symbol, None)

    def get_order(self, vt_orderid: str) -> Optional[OrderData]:
        """
        Get latest order data by vt_orderid.
        """
        return self.orders.get(vt_orderid, None)

    def get_trade(self, vt_tradeid: str) -> Optional[TradeData]:
        """
        Get trade data by vt_tradeid.
        """
        return self.trades.get(vt_tradeid, None)

    def get_position(self, vt_positionid: str) -> Optional[PositionData]:
        """
        Get latest position data by vt_positionid.
        """
        return self.positions.get(vt_positionid, None)

    def get_account(self, vt_accountid: str) -> Optional[AccountData]:
        """
        Get latest account data by vt_accountid.
        """
        return self.accounts.get(vt_accountid, None)

    def get_contract(self, vt_symbol: str) -> Optional[ContractData]:
        """
        Get contract data by vt_symbol.
        """
        return self.contracts.get(vt_symbol, None)

    def get_quote(self, vt_quoteid: str) -> Optional[QuoteData]:
        """
        Get latest quote data by vt_orderid.
        """
        return self.quotes.get(vt_quoteid, None)

    def get_all_ticks(self) -> List[TickData]:
        """
        Get all tick data.
        """
        return list(self.ticks.values())

    def get_all_orders(self) -> List[OrderData]:
        """
        Get all order data.
        """
        return list(self.orders.values())

    def get_all_trades(self) -> List[TradeData]:
        """
        Get all trade data.
        """
        return list(self.trades.values())

    def get_all_positions(self) -> List[PositionData]:
        """
        Get all position data.
        """
        return list(self.positions.values())

    def get_all_accounts(self) -> List[AccountData]:
        """
        Get all account data.
        """
        return list(self.accounts.values())

    def get_all_contracts(self) -> List[ContractData]:
        """
        Get all contract data.
        """
        return list(self.contracts.values())

    def get_all_quotes(self) -> List[QuoteData]:
        """
        Get all quote data.
        """
        return list(self.quotes.values())

    def get_all_active_orders(self, vt_symbol: str = "") -> List[OrderData]:
        """
        Get all active orders by vt_symbol.
        If vt_symbol is empty, return all active orders.
        """
        if not vt_symbol:
            return list(self.active_orders.values())
        else:
            active_orders: List[OrderData] = [
                order
                for order in self.active_orders.values()
                if order.vt_symbol == vt_symbol
            ]
            return active_orders

    def get_all_active_quotes(self, vt_symbol: str = "") -> List[QuoteData]:
        """
        Get all active quotes by vt_symbol.
        If vt_symbol is empty, return all active qutoes.
        """
        if not vt_symbol:
            return list(self.active_quotes.values())
        else:
            active_quotes: List[QuoteData] = [
                quote
                for quote in self.active_quotes.values()
                if quote.vt_symbol == vt_symbol
            ]
            return active_quotes

    def update_order_request(self, req: OrderRequest, vt_orderid: str, gateway_name: str) -> None:
        # 不走Event渠道?
        """
        Update order request to offset converter.
        """
        converter: OffsetConverter = self.offset_converters.get(gateway_name, None)
        if converter:
            converter.update_order_request(req, vt_orderid)

    def convert_order_request(
        self,
        req: OrderRequest,
        gateway_name: str,
        lock: bool,
        net: bool = False
    ) -> List[OrderRequest]:
        """
        Convert original order request according to given mode.
        """
        converter: OffsetConverter = self.offset_converters.get(gateway_name, None)
        if not converter:
            return [req]

        reqs: List[OrderRequest] = converter.convert_order_request(req, lock, net)
        return reqs

    def get_converter(self, gateway_name: str) -> OffsetConverter:
        # 没有存在感
        """
        Get offset converter object of specific gateway.
        """
        return self.offset_converters.get(gateway_name, None)

    


class MainEngine:
    '''
    核心
    '''
    def __init__(self, event_engine: EventEngine = None) -> None:
        
        if event_engine:
            self.event_engine: EventEngine = event_engine
        else:
            self.event_engine = EventEngine()
        #### 回调函数注册了吗就start? 事件放进事件队列了吗就start?
        self.event_engine.start()

        self.gateways: Dict[str, BaseGateway] = {}
        self.engines: Dict[str, BaseEngine] = {}
        self.apps: Dict[str, BaseApp] = {}
        self.exchanges: List[Exchange] = []
        # 改变工作路径到指定工作路径
        os.chdir(TRADER_DIR)
        # engine都没初始化就start?
        self.init_engines()
    
    # 以下将engine, gateway, app加入mainEngine, 在其内部创建实例
    def add_engine(self, engine_class: Any) -> BaseEngine:
        engine: BaseEngine = engine_class(self, self.event_engine)
        self.engines[engine.engine_name] = engine
        return engine
    
    def add_gateway(self, gateway_class: Type[BaseGateway], gateway_name: str = "") -> BaseGateway:
        if not gateway_name:
            gateway_name: str = gateway_class.default_name
        gateway: BaseGateway = gateway_class(self.event_engine, gateway_name)
        self.gateways[gateway_name] = gateway
        # 将交易接口支持的交易所加入engine
        for exchange in gateway.exchanges:
            if exchange not in self.exchanges:
                self.exchanges.append(exchange)
        return gateway
    
    def add_app(self, app_class: Type[BaseApp]) -> BaseEngine:
        app: BaseApp = app_class()
        self.apps[app.app_name] = app
        engine: BaseEngine = self.add_engine(app.engine_class)
        return engine
    
    # 初始化就这?
    def init_engines(self) -> None:
        self.add_engine(LogEngine)
        self.add_engine(OmsEngine)
        # self.add_engine(EmailEngine)
    
    # logEvent到底是啥！为什么要以event的形式?
    def write_log(self, msg: str, source: str = "") -> None:
        '''
        将log event放入事件队列
        '''
        log: LogData = LogData(gateway_name=source, msg=msg)
        event: Event = Event(EVENT_LOG, log)
        self.event_engine.put(event)
    
    # 以下为mainEngine内部信息查询接口
    def get_gateway(self, gateway_name: str) -> BaseGateway:
        """
        通过gateway_name返回已添加的gateway实例
        """
        gateway: BaseGateway = self.gateways.get(gateway_name, None)
        if not gateway:
            self.write_log(f"找不到底层接口：{gateway_name}")
        return gateway

    def get_engine(self, engine_name: str) -> "BaseEngine":
        """
        通过engine_name返回已添加的engine实例
        """
        engine: BaseEngine = self.engines.get(engine_name, None)
        if not engine:
            self.write_log(f"找不到引擎：{engine_name}")
        return engine

    def get_default_setting(self, gateway_name: str) -> Optional[Dict[str, Any]]:
        """
        通过gateway_name返回该gateway的默认设置
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            return gateway.get_default_setting()
        return None

    def get_all_gateway_names(self) -> List[str]:
        """
        Get all names of gateway added in main engine.
        """
        return list(self.gateways.keys())

    def get_all_apps(self) -> List[BaseApp]:
        """
        Get all app objects.
        """
        return list(self.apps.values())

    def get_all_exchanges(self) -> List[Exchange]:
        """
        Get all exchanges.
        """
        return self.exchanges

    # 以下为通过mainEngine调用内部交易接口(gateway)的相关功能
    def connect(self, setting: dict, gateway_name: str) -> None:
        """
        Start connection of a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.connect(setting)

    def subscribe(self, req: SubscribeRequest, gateway_name: str) -> None:
        """
        Subscribe tick data update of a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.subscribe(req)

    def send_order(self, req: OrderRequest, gateway_name: str) -> str:
        """
        Send new order request to a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            return gateway.send_order(req)
        else:
            return ""

    def cancel_order(self, req: CancelRequest, gateway_name: str) -> None:
        """
        Send cancel order request to a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.cancel_order(req)

    def send_quote(self, req: QuoteRequest, gateway_name: str) -> str:
        """
        Send new quote request to a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            return gateway.send_quote(req)
        else:
            return ""

    def cancel_quote(self, req: CancelRequest, gateway_name: str) -> None:
        """
        Send cancel quote request to a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            gateway.cancel_quote(req)

    def query_history(self, req: HistoryRequest, gateway_name: str) -> Optional[List[BarData]]:
        """
        Query bar history data from a specific gateway.
        """
        gateway: BaseGateway = self.get_gateway(gateway_name)
        if gateway:
            return gateway.query_history(req)
        else:
            return None

    # 关闭
    def close(self) -> None:
        """
        Make sure every gateway and app is closed properly before
        programme exit.
        """
        # Stop event engine first to prevent new timer event.
        self.event_engine.stop()

        for engine in self.engines.values():
            engine.close()

        for gateway in self.gateways.values():
            gateway.close()

