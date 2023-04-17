from typing import Type, Callable, Dict
from datetime import datetime

from core.engine import BaseEngine
from core.event import EventEngine
from datastructure.object import TickData, SignalData, BarData, OrderData, TradeData, ContractData, SubscribeRequest
from datastructure.constant import Exchange
from strategy.strategy import CtaTemplate, DoubleMaStrategy
from gw.to_backtest import BaseGateway, BacktestGateway
from oms.omsEngine import OmsEngine
from exchange.simExchange import SimExchange


class BacktestEngine(BaseEngine):
    '''回测核心'''

    def __init__(self, event_engine: EventEngine) -> None:
        ''''''
        super().__init__(event_engine, 'backtest_engine')

        # 回测系统组件
        
        self.gateway: BaseGateway = BacktestGateway(self.event_engine)
        self.exchange: SimExchange = SimExchange(self.event_engine, self.gw)
        self.strategy: CtaTemplate = DoubleMaStrategy(self.gw)
        self.oms: OmsEngine = OmsEngine(self.event_engine)
        
        

        # 固定参数设置 # set_parameters
        self.start: datetime = None
        self.end: datetime = None
        self.rate: float = 0                # commission rate(turnover)
        self.slippage: float = 0            # 成交价滑点
        # contractdata
        self.size: float = 1                # 合约乘数
        self.pricetick: float = 0           # 价格最小变动
        self.capital: int = 1_000_000
        # 
        self.risk_free: float = 0
        self.annual_days: int = 252

        # 历史数据集 # load_data
        self.history_data: list = []
        
        # 记录最新行情更新事件market event
        self.tick: TickData
        self.bar: BarData
        self.datetime: datetime = None
        

    def subscribe(self, symbol: str, exchange: Exchange) -> None:
        req: SubscribeRequest = SubscribeRequest(symbol, exchange)
        self.gateway.subscribe(req)
    
    

        

