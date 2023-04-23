from core.event import EventEngine, Event
from exchange.simExchange import SimExchange
from datetime import datetime
from datastructure.definition import EVENT_TICK
from datastructure.constant import Exchange
from datastructure.object import TickData, ContractData
from core.backtest import BacktestEngine

symbol = 'rb2305'
exchange = Exchange('SHFE')
size = 10
pricetick = 1
margin_rate = 0.19
commission_rate = 0.00005
contract = ContractData(symbol, exchange, size, pricetick, margin_rate, commission_rate)
start_date = datetime(2023,1,3,9,0,0)
end_date = datetime(2023,1,3,9,0,5)
slippage = 0

event_engine = EventEngine()
backtest = BacktestEngine(event_engine, start_date, end_date, contract, slippage)

backtest.run_backtest()