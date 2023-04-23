from typing import Type, Callable, Dict
from datetime import datetime, date

from .engine import BaseEngine
from .event import EventEngine, Event
from datastructure.object import TickData, SignalData, BarData, OrderData, TradeData, ContractData, SubscribeRequest
from datastructure.constant import Exchange
from strategy.buy_and_hold_strategy import BuyAndHoldStrategy
from oms.omsEngine import OmsEngine
from exchange.simExchange import SimExchange
from datastructure.definition import EVENT_TICK


####TODO 回测的even loop和真实交易的even loop不太一样:
# 真实交易: 
# 1.交易所撮合订单产生行情更新 -> 策略根据最新行情产生信号 -> portfolio根据信号产生订单
# 2.交易所撮合订单产生成交信息 -> portfolio根据成交改变仓位信息
# 3.行情更新、产生订单、接收成交 -> 计算仓位和pnl
# 回测:
# 1.模拟交易所产生行情更新(历史数据) -> 策略根据最新行情产生信号 -> portfolio根据信号产生(模拟)订单
# 2.模拟交易所产生行情更新(历史数据) -> 模拟交易所根据最新行情撮合(模拟)订单 -> portfolio根据成交改变仓位信息
# 3.行情更新、产生订单、接收成交 -> 计算仓位和pnl

class BacktestEngine(BaseEngine):
    '''回测核心'''

    def __init__(self,
                 event_engine: EventEngine,
                 start: datetime, 
                 end: datetime, 
                 contract: ContractData, 
                 slippage: float = 0,
                 capital: int = 1000000, 
                 risk_free: float = 0, 
                 annual_days: int = 252) -> None:
        ''''''
        super().__init__(event_engine, 'backtest_engine')

        # 回测系统组件
        
        self.sim_exchange = SimExchange(self.event_engine, start, end, contract)
        self.strategy = BuyAndHoldStrategy(self.event_engine)
        self.oms = OmsEngine(self.event_engine, contract)

        # contractdata
        self.contract: ContractData = contract
        
        self.slippage: float = slippage            # 成交价滑点
        # 
        self.capital: int = capital
        # 
        self.risk_free: float = risk_free
        self.annual_days: int = annual_days


    def run_backtest(self) -> None:
        self.sim_exchange.load_small_data('rb2305', Exchange("SHFE"))

        while True:
            tick = self.sim_exchange.publish_md()
            if tick:
                self.event_engine.start()
            else:
                self.event_engine.stop()
                break
        
        print(self.sim_exchange.calculate_results())
        


    




        

        


















# event_engine = EventEngine()
# sim_exchange = SimExchange(event_engine, datetime(2023,1,3), datetime(2023,1,4))

# def print_tick(event: Event) -> None:
#     tick: TickData = event.data
#     print(tick.last_price)

# event_engine.register(EVENT_TICK, print_tick)
# sim_exchange.load_history_data('rb2305', Exchange("SHFE"))
# while True:
#     sim_exchange.publish_md()
#     event_engine.start()
    

        

