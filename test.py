from db.database import get_database
from datastructure.constant import Exchange, Interval
from datetime import datetime
import numpy as np
from core.backtesting_engine import BacktestingEngine
from strategy.strategy import DoubleMaStrategy



backtesting = BacktestingEngine()
backtesting.set_parameters('rb2305.SHFE', Interval('tick'), datetime(2023,1,3), datetime(2023,1,5),rate=0.001, slippage=0.01, size=10, pricetick=1, capital=100000, risk_free=0.05)
backtesting.add_strategy(DoubleMaStrategy, None)
backtesting.load_data()
backtesting.run_backtesting()
result_daily_df = backtesting.calculate_result()
backtesting.calculate_statistics(result_daily_df)