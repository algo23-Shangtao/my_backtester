from core.event import EventEngine, Event
from exchange.simExchange import SimExchange
from datetime import datetime
from datastructure.definition import EVENT_TICK
from datastructure.constant import Exchange
from datastructure.object import TickData, ContractData
from core.backtest import BacktestEngine


contract = ContractData('rb2305', Exchange('SHFE'), 10, 1, 0.19, 0.00005)


event_engine = EventEngine()
backtest = BacktestEngine(event_engine, datetime(2023,1,3),datetime(2023,1,4), contract, 0.01)

backtest.run_backtest()