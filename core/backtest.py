from typing import Type, Callable, Dict
from datetime import datetime

from core.engine import BaseEngine
from core.event import EventEngine
from datastructure.object import TickData, SignalData, BarData, OrderData, TradeData, ContractData, SubscribeRequest
from datastructure.constant import Exchange
from reference.strategy import CtaTemplate, DoubleMaStrategy
from oms.omsEngine import OmsEngine
from gw.gateway import BaseGateway
from exchange.simExchange import SimExchange


class BacktestEngine(BaseEngine):
    '''回测核心'''

    def __init__(self, event_engine: EventEngine) -> None:
        ''''''
        super().__init__(event_engine, 'backtest_engine')

        # 回测系统组件
        
        self.gateway: BaseGateway = BaseGateway(self.event_engine)
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
        

from core.event import EventEngine, Event
from gw.gateway import BaseGateway
from exchange.simExchange import SimExchange
from datetime import datetime
from datastructure.definition import EVENT_TICK
from datastructure.constant import Exchange
from datastructure.object import TickData

event_engine = EventEngine()
sim_exchange = SimExchange(event_engine, datetime(2023,1,3), datetime(2023,1,4))

def print_tick(event: Event) -> None:
    tick: TickData = event.data
    print(tick.last_price)

event_engine.register(EVENT_TICK, print_tick)
sim_exchange.load_history_data('rb2305', Exchange("SHFE"))
while True:
    sim_exchange.publish_md()
    event_engine.start()
    

        

