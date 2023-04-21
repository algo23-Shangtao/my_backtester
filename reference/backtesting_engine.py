'''
Cta回测引擎
'''
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Callable, List, Dict, Optional, Type, TYPE_CHECKING
from functools import lru_cache
import traceback

import numpy as np
from pandas import DataFrame, Series
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from datastructure.constant import (Direction, Offset, Exchange,
                                  Interval, Status)
from db.database import get_database
from datastructure.object import OrderData, TradeData, BarData, TickData
from utils.utils_function import round_to
from datastructure.definition import INTERVAL_DELTA_MAP

if TYPE_CHECKING:
    from reference.template import CtaTemplate

class BacktestingEngine:
    '''
    事件驱动型回测类
    '''
    
    gateway_name: str = "BACKTESTING"

    def __init__(self) -> None:
        '''构造函数--但backtesting engine并没有真正初始化'''
        ''''''
        # 目标合约 # set_parameters
        self.vt_symbol: str = ""
        self.symbol: str = ""               # 单合约择时策略(?)
        self.exchange: Exchange = None
        # 固定参数设置 # set_parameters
        self.start: datetime = None
        self.end: datetime = None
        self.rate: float = 0                # commission rate(turnover)
        self.slippage: float = 0            # 成交价滑点
        self.size: float = 1                # 合约乘数
        self.pricetick: float = 0           # 价格最小变动
        self.capital: int = 1_000_000
        self.risk_free: float = 0
        self.annual_days: int = 240
        self.interval: Interval = Interval('tick')      # 时间颗粒度(bar: "1m", "d"; tick: "tick")
        # 执行的策略类 # add_strategy
        self.strategy_class: Type["CtaTemplate"] = None
        self.strategy: "CtaTemplate" = None
        # 用部分历史数据来初始化策略的参数#### TODO
        self.days: int = 0             # 用前10天数据初始化参数(for example)
        self.callback: Callable = None # strategy.on_bar
        # 历史数据集 # load_data
        self.history_data: list = []
        '''OmsEngine'''
        # 记录最新行情更新事件market event
        self.tick: TickData
        self.bar: BarData
        self.datetime: datetime = None
        # 记录order & trade
        self.limit_order_count: int = 0
        self.limit_orders: Dict[str, OrderData] = {}
        self.active_limit_orders: Dict[str, OrderData] = {}
        self.trade_count: int = 0
        self.trades: Dict[str, TradeData] = {}
        # 记录logs
        self.logs: list = []
        # 记录每日盯市盈亏
        self.daily_results: Dict[date, DailyResult] = {}
        # 
        self.daily_df: DataFrame = None

    ####TODO 回测的even loop和真实交易的even loop不太一样:
    # 真实交易: 
    # 1.交易所撮合订单产生行情更新 -> 策略根据最新行情产生信号 -> portfolio根据信号产生订单
    # 2.交易所撮合订单产生成交信息 -> portfolio根据成交改变仓位信息
    # 3.行情更新、产生订单、接收成交 -> 计算仓位和pnl
    # 回测:
    # 1.模拟交易所产生行情更新(历史数据) -> 策略根据最新行情产生信号 -> portfolio根据信号产生(模拟)订单
    # 2.模拟交易所产生行情更新(历史数据) -> 模拟交易所根据最新行情撮合(模拟)订单 -> portfolio根据成交改变仓位信息
    # 3.行情更新、产生订单、接收成交 -> 计算仓位和pnl

    # 1. 设置回测的默认参数
    def set_parameters(
        self,
        vt_symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
        rate: float,
        slippage: float,
        size: float,
        pricetick: float,
        capital: int,
        risk_free: float,
        annual_days: int = 240,
        ) -> None:
        '''设置目标合约 & 固定参数'''
        # 设置目标合约
        self.vt_symbol = vt_symbol
        symbol, exchange_str = self.vt_symbol.split('.')
        self.symbol = symbol
        self.exchange = Exchange(exchange_str)
        # 设置固定参数
        self.start = start
        self.end = end
        self.rate = rate
        self.slippage = slippage
        self.size = size
        self.pricetick = pricetick
        self.capital = capital
        self.risk_free = risk_free
        self.annual_days = annual_days
        self.interval = interval
    
    # 2. 添加回测的策略
    def add_strategy(self, strategy_class: Type["CtaTemplate"], setting: dict) -> None:
        '''设置执行的策略类, 并实例化'''
        self.strategy_class = strategy_class
        self.strategy = self.strategy_class(self, strategy_class.__name__, self.vt_symbol, setting)    
    
    # 3. 加载回测所用历史数据
    def load_data(self) -> None:
        '''加载历史数据, 有进度条'''
        self.output("开始加载历史数据")
        # 防止捣乱
        if self.start >= self.end:
            self.output("开始日期需要小于结束日期!")
            return
        # 清除原先存的历史数据
        self.history_data.clear()
        # 分10批读取历史数据, 并构建进度条(progress bar)
        total_days: int = (self.end - self.start).days
        progress_days: int = max(total_days / 10, 1) # 每次至少加载1天数据, 或者加载总天数的1/10
        progress_delta: timedelta = timedelta(days=progress_days)
        interval_delta: timedelta = INTERVAL_DELTA_MAP[self.interval] # 防止重复读取最后一个数据
        # 每次至少加载1天数据, 或者加载总天数的1/10
        start: datetime = self.start
        end: datetime = start + progress_delta
        progress = 0
        while start < self.end:
            end: datetime = min(end, self.end)
            data: List[TickData] = load_tick_data(self.symbol, self.exchange, start, end)
            
            self.history_data.extend(data)
            progress += progress_days / total_days
            progress = min(progress, 1)
            progress_bar: str = "#" * int(progress * 10)
            self.output(f"加载进度: {progress_bar}[{progress:.0%}]")
            start = end + interval_delta # 植树问题
            end += progress_delta
        self.output(f"历史数据加载完成, 数据量{len(self.history_data)}")


    #### TODO 配合strategy(template)食用--用于初始化策略
    def load_bar(
        self,
        vt_symbol: str,
        days: int,          # 10
        interval: Interval, # Interval.MINUTE
        callback: Callable, # strategy.on_bar
        use_database: bool
    ) -> List[BarData]:
        """"""
        self.days = days
        self.callback = callback # strategy.on_bar
        return []

    def load_tick(self, vt_symbol: str, days: int, callback: Callable) -> List[TickData]:
        """"""
        self.days = days
        self.callback = callback
        return []

    # 4. 执行回测
    def run_backtesting(self) -> None:
        '''
        执行回测main函数
        '''
        # 4.1 设置self.days和self.callback, 利用前self.days的历史数据初始化策略参数(计算MA?)
        self.strategy.on_init() # 此处传入self.days & self.callback(load_bar & load_tick)
        day_count: int = 0
        ix: int = 0
        # 4.2 遍历前self.days天的历史数据, 对于每天的数据, 调用callback, 用于初始化策略
        
        # 用第一个历史数据的时间戳初始化当前时间戳(self.datetime)
        if not self.datetime:
            self.datetime = self.history_data[0].datetime
        for ix, data in enumerate(self.history_data):
            # 每加载完一天, day_count++
            if data.datetime.day != self.datetime.day:
                day_count += 1
                if day_count >= self.days:
                    break
                self.datetime = data.datetime
                try:
                    self.callback(data)
                except Exception:
                    self.output("初始化策略时出现异常, 停止回测")
                    self.output(traceback.format_exc())
                    return
                
        self.strategy.inited = True
        self.output('策略初始化完成')
        self.strategy.on_start()
        self.strategy.trading = True
        self.output("开始回放历史数据")
        backtesting_data: list = self.history_data[ix:]
        if len(backtesting_data) <= 1:
            self.output("历史数据不足, 停止回测")
            return

        # 4.3 用剩余数据执行回测
        func = self.new_tick
        

        # 构建进度条, 分批进行回测
        total_size: int = len(backtesting_data)
        batch_size: int = max(int(total_size / 10), 1) # 每次至少回测1条数据, 或者回测总数据量的1/10
        for ix, i in enumerate(range(0, total_size, batch_size)):
            # 每次至少回测1天数据, 或者回测总天数的1/10
            batch_data: list = backtesting_data[i: i + batch_size]
            
            # 模拟交易所产生行情更新!!!!
            for data in batch_data:
                try:
                    # func--new_tick或new_bar, 执行回测even loop
                    func(data)
                except Exception:
                    self.output("运行回测时触发异常, 停止回测")
                    self.output(traceback.format_exc())
                    return
            progress = min(ix / 10, 1)
            progress_bar: str = "*" *(ix)
            self.output(f"回测进度: {progress_bar}[{progress:.0%}]")
        self.strategy.on_stop()
        self.output("回测结束")

    
    def new_tick(self, tick: TickData) -> None:
        '''
        传入最新的TickData
        根据最新的TickData撮合交易
        执行策略on tick回调
        '''
        # 记录最新行情更新
        self.tick = tick
        self.datetime = tick.datetime
        # 模拟交易所撮合订单
        self.cross_limit_order()
        # 策略根据最新行情产生信号
        self.strategy.on_tick(tick)
        # 行情更新, 计算仓位和pnl
        self.update_daily_close(tick.last_price)


    def cross_limit_order(self) -> None:
        '''
        根据最新的行情信息, 得到可以成交的价格
        遍历所有active委托: 1.接收提交中委托, 执行策略on order回调 2.尝试撮合该委托 TODO 有bug--没有考虑部分成交
        若成交, 则产生成交信息TradeData, 执行策略on trade回调

        '''
        # 由最新行情数据得到成交价
        long_cross_price = self.tick.ask_price_1 # 可成交的买价的下限-卖1价
        short_cross_price = self.tick.bid_price_1 # 可成交的卖价的上限-买1价
        long_best_price = long_cross_price # 真实成交买价
        short_best_price = short_cross_price # 真实成交卖价

        # 遍历所有active委托
        for order in list(self.active_limit_orders.values()):
            # 接收提交中委托, 执行策略on order回调
            if order.status == Status.SUBMITTING:
                order.status = Status.NOTTRADED
                self.strategy.on_order(order)
            # 尝试撮合该委托
            long_cross: bool = (
                order.direction == Direction.LONG
                and order.price >= long_cross_price
                and long_cross_price > 0
            )
            short_cross: bool = {
                order.direction == Direction.SHORT
                and order.price <= short_cross_price
                and short_cross_price > 0
            }
            # 这个订单成交不了, 下一个
            if not long_cross and not short_cross:
                continue
            # 可以成交, 委托状态变为全部成交, 执行策略on order回调 ----vnpy bug?(这种适用于一次只下一手的情况)
            
            #### TODO 
            order.traded = order.volume
            order.status = Status.ALLTRADED
            self.strategy.on_order(order)

            if order.vt_orderid in self.active_limit_orders:
                self.active_limit_orders.pop(order.vt_orderid)
            
            # 产生成交事件, 执行策略on trade回调
            self.trade_count += 1
            if long_cross:
                trade_price = min(order.price, long_best_price)
                pos_change = order.volume
            else:
                trade_price = max(order.price, short_best_price)
                pos_change = -order.volume
            
            trade: TradeData = TradeData(
                symbol=order.symbol,
                exchange= order.exchange,
                orderid=order.orderid,
                tradeid=str(self.trade_count),
                direction=order.direction,
                offset=order.offset,
                price=trade_price,
                volume=order.volume,
                datetime=self.datetime,
                gateway_name=self.gateway_name
            )

            self.strategy.pos += pos_change
            self.strategy.on_trade(trade)
            self.trades[trade.vt_tradeid] = trade
        

    def update_daily_close(self, price: float) -> None:
        '''更新盯市盈亏'''
        d: date = self.datetime.date()
        daily_result: Optional[DailyResult] = self.daily_results.get(d, None)
        if daily_result:
            daily_result.close_price = price
            # daily_result.pre_close在后面更新
        else:
            self.daily_results[d] = DailyResult(d, price)

    
    def send_order(self,
                   strategy: "CtaTemplate",
                   direction: Direction,
                   offset: Offset,
                   price: float,
                   volume: float,
                   stop: bool,
                   lock: bool,
                   net: bool) -> list:
        price: float = round_to(price, self.pricetick)
        vt_orderid: str = self.send_limit_order(direction, offset, price, volume)
        return [vt_orderid]

    
    def send_limit_order(self, direction: Direction, offset: Offset, price: float, volume: float) -> str:
        self.limit_order_count += 1
        order: OrderData = OrderData(
            gateway_name=self.gateway_name,
            symbol=self.symbol,
            exchange=self.exchange,
            orderid=str(self.limit_order_count),
            direction=direction,
            offset=offset,
            price=price,
            volume=volume,
            datetime=self.datetime
        )
        self.active_limit_orders[order.vt_orderid] = order
        self.limit_orders[order.vt_orderid] = order
        
        return order.vt_orderid
    
    def cancel_order(self, strategy: "CtaTemplate", vt_orderid: str) -> None:
        """
        Cancel order by vt_orderid.
        """
        self.cancel_limit_order(strategy, vt_orderid)


    def cancel_limit_order(self, strategy: "CtaTemplate", vt_orderid: str) -> None:
        """"""
        if vt_orderid not in self.active_limit_orders:
            return
        order: OrderData = self.active_limit_orders.pop(vt_orderid)

        order.status = Status.CANCELLED
        self.strategy.on_order(order)

    def cancel_all(self, strategy: "CtaTemplate") -> None:
        """
        Cancel all orders, both limit and stop.
        """
        vt_orderids: list = list(self.active_limit_orders.keys())
        for vt_orderid in vt_orderids:
            self.cancel_limit_order(strategy, vt_orderid)



    def calculate_result(self) -> DataFrame:
        """"""
        self.output("开始计算逐日盯市盈亏")

        if not self.trades:
            self.output("成交记录为空，无法计算")
            return

        # Add trade data into daily reuslt.
        for trade in self.trades.values():
            d: date = trade.datetime.date()
            daily_result: DailyResult = self.daily_results[d]
            daily_result.add_trade(trade)

        # Calculate daily result by iteration.
        pre_close = 0
        start_pos = 0

        for daily_result in self.daily_results.values():
            daily_result.calculate_pnl(
                pre_close,
                start_pos,
                self.size,
                self.rate,
                self.slippage
            )
            pre_close = daily_result.close_price
            start_pos = daily_result.end_pos

        # Generate dataframe
        results: defaultdict = defaultdict(list)

        for daily_result in self.daily_results.values():
            for key, value in daily_result.__dict__.items():
                results[key].append(value)

        self.daily_df = DataFrame.from_dict(results).set_index("date")

        self.output("逐日盯市盈亏计算完成")
        return self.daily_df

    def calculate_statistics(self, df: DataFrame = None, output=True) -> dict:
        """"""
        self.output("开始计算策略统计指标")

        # Check DataFrame input exterior
        if df is None:
            df: DataFrame = self.daily_df

        # Init all statistics default value
        start_date: str = ""
        end_date: str = ""
        total_days: int = 0
        profit_days: int = 0
        loss_days: int = 0
        end_balance: float = 0
        max_drawdown: float = 0
        max_ddpercent: float = 0
        max_drawdown_duration: int = 0
        total_net_pnl: float = 0
        daily_net_pnl: float = 0
        total_commission: float = 0
        daily_commission: float = 0
        total_slippage: float = 0
        daily_slippage: float = 0
        total_turnover: float = 0
        daily_turnover: float = 0
        total_trade_count: int = 0
        daily_trade_count: int = 0
        total_return: float = 0
        annual_return: float = 0
        daily_return: float = 0
        return_std: float = 0
        sharpe_ratio: float = 0
        return_drawdown_ratio: float = 0

        # Check if balance is always positive
        positive_balance: bool = False

        if df is not None:
            # Calculate balance related time series data
            df["balance"] = df["net_pnl"].cumsum() + self.capital

            # When balance falls below 0, set daily return to 0
            pre_balance: Series = df["balance"].shift(1)
            pre_balance.iloc[0] = self.capital
            x = df["balance"] / pre_balance
            x[x <= 0] = np.nan
            df["return"] = np.log(x).fillna(0)

            df["highlevel"] = (
                df["balance"].rolling(
                    min_periods=1, window=len(df), center=False).max()
            )
            df["drawdown"] = df["balance"] - df["highlevel"]
            df["ddpercent"] = df["drawdown"] / df["highlevel"] * 100

            # All balance value needs to be positive
            positive_balance = (df["balance"] > 0).all()
            if not positive_balance:
                self.output("回测中出现爆仓(资金小于等于0), 无法计算策略统计指标")

        # Calculate statistics value
        if positive_balance:
            # Calculate statistics value
            start_date = df.index[0]
            end_date = df.index[-1]

            total_days: int = len(df)
            profit_days: int = len(df[df["net_pnl"] > 0])
            loss_days: int = len(df[df["net_pnl"] < 0])

            end_balance = df["balance"].iloc[-1]
            max_drawdown = df["drawdown"].min()
            max_ddpercent = df["ddpercent"].min()
            max_drawdown_end = df["drawdown"].idxmin()

            if isinstance(max_drawdown_end, date):
                max_drawdown_start = df["balance"][:max_drawdown_end].idxmax()
                max_drawdown_duration: int = (max_drawdown_end - max_drawdown_start).days
            else:
                max_drawdown_duration: int = 0

            total_net_pnl: float = df["net_pnl"].sum()
            daily_net_pnl: float = total_net_pnl / total_days

            total_commission: float = df["commission"].sum()
            daily_commission: float = total_commission / total_days

            total_slippage: float = df["slippage"].sum()
            daily_slippage: float = total_slippage / total_days

            total_turnover: float = df["turnover"].sum()
            daily_turnover: float = total_turnover / total_days

            total_trade_count: int = df["trade_count"].sum()
            daily_trade_count: int = total_trade_count / total_days

            total_return: float = (end_balance / self.capital - 1) * 100
            annual_return: float = total_return / total_days * self.annual_days
            daily_return: float = df["return"].mean() * 100
            return_std: float = df["return"].std() * 100

            if return_std:
                daily_risk_free: float = self.risk_free / np.sqrt(self.annual_days)
                sharpe_ratio: float = (daily_return - daily_risk_free) / return_std * np.sqrt(self.annual_days)
            else:
                sharpe_ratio: float = 0

            if max_ddpercent:
                return_drawdown_ratio: float = -total_return / max_ddpercent
            else:
                return_drawdown_ratio = 0

        # Output
        if output:
            self.output("-" * 30)
            self.output(f"首个交易日：\t{start_date}")
            self.output(f"最后交易日：\t{end_date}")

            self.output(f"总交易日：\t{total_days}")
            self.output(f"盈利交易日：\t{profit_days}")
            self.output(f"亏损交易日：\t{loss_days}")

            self.output(f"起始资金：\t{self.capital:,.2f}")
            self.output(f"结束资金：\t{end_balance:,.2f}")

            self.output(f"总收益率：\t{total_return:,.2f}%")
            self.output(f"年化收益：\t{annual_return:,.2f}%")
            self.output(f"最大回撤: \t{max_drawdown:,.2f}")
            self.output(f"百分比最大回撤: {max_ddpercent:,.2f}%")
            self.output(f"最长回撤天数: \t{max_drawdown_duration}")

            self.output(f"总盈亏：\t{total_net_pnl:,.2f}")
            self.output(f"总手续费：\t{total_commission:,.2f}")
            self.output(f"总滑点：\t{total_slippage:,.2f}")
            self.output(f"总成交金额：\t{total_turnover:,.2f}")
            self.output(f"总成交笔数：\t{total_trade_count}")

            self.output(f"日均盈亏：\t{daily_net_pnl:,.2f}")
            self.output(f"日均手续费：\t{daily_commission:,.2f}")
            self.output(f"日均滑点：\t{daily_slippage:,.2f}")
            self.output(f"日均成交金额：\t{daily_turnover:,.2f}")
            self.output(f"日均成交笔数：\t{daily_trade_count}")

            self.output(f"日均收益率：\t{daily_return:,.2f}%")
            self.output(f"收益标准差：\t{return_std:,.2f}%")
            self.output(f"Sharpe Ratio：\t{sharpe_ratio:,.2f}")
            self.output(f"收益回撤比：\t{return_drawdown_ratio:,.2f}")

        statistics: dict = {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "profit_days": profit_days,
            "loss_days": loss_days,
            "capital": self.capital,
            "end_balance": end_balance,
            "max_drawdown": max_drawdown,
            "max_ddpercent": max_ddpercent,
            "max_drawdown_duration": max_drawdown_duration,
            "total_net_pnl": total_net_pnl,
            "daily_net_pnl": daily_net_pnl,
            "total_commission": total_commission,
            "daily_commission": daily_commission,
            "total_slippage": total_slippage,
            "daily_slippage": daily_slippage,
            "total_turnover": total_turnover,
            "daily_turnover": daily_turnover,
            "total_trade_count": total_trade_count,
            "daily_trade_count": daily_trade_count,
            "total_return": total_return,
            "annual_return": annual_return,
            "daily_return": daily_return,
            "return_std": return_std,
            "sharpe_ratio": sharpe_ratio,
            "return_drawdown_ratio": return_drawdown_ratio,
        }

        # Filter potential error infinite value
        for key, value in statistics.items():
            if value in (np.inf, -np.inf):
                value = 0
            statistics[key] = np.nan_to_num(value)

        self.output("策略统计指标计算完成")
        return statistics

    def show_chart(self, df: DataFrame = None) -> None:
        """"""
        # Check DataFrame input exterior
        if df is None:
            df: DataFrame = self.daily_df

        # Check for init DataFrame
        if df is None:
            return

        fig = make_subplots(
            rows=4,
            cols=1,
            subplot_titles=["Balance", "Drawdown", "Daily Pnl", "Pnl Distribution"],
            vertical_spacing=0.06
        )

        balance_line = go.Scatter(
            x=df.index,
            y=df["balance"],
            mode="lines",
            name="Balance"
        )

        drawdown_scatter = go.Scatter(
            x=df.index,
            y=df["drawdown"],
            fillcolor="red",
            fill='tozeroy',
            mode="lines",
            name="Drawdown"
        )
        pnl_bar = go.Bar(y=df["net_pnl"], name="Daily Pnl")
        pnl_histogram = go.Histogram(x=df["net_pnl"], nbinsx=100, name="Days")

        fig.add_trace(balance_line, row=1, col=1)
        fig.add_trace(drawdown_scatter, row=2, col=1)
        fig.add_trace(pnl_bar, row=3, col=1)
        fig.add_trace(pnl_histogram, row=4, col=1)

        fig.update_layout(height=1000, width=1000)
        fig.show()
    
    
    
    def write_log(self, msg: str, strategy: "CtaTemplate" = None) -> None:
        """
        Write log message.
        """
        msg: str = f"{self.datetime}\t{msg}"
        self.logs.append(msg)

    def send_email(self, msg: str, strategy: "CtaTemplate" = None) -> None:
        """
        Send email to default receiver.
        """
        pass

    def sync_strategy_data(self, strategy: "CtaTemplate") -> None:
        """
        Sync strategy data into json file.
        """
        pass


    def get_pricetick(self, strategy: "CtaTemplate") -> float:
        """
        Return contract pricetick data.
        """
        return self.pricetick

    def get_size(self, strategy: "CtaTemplate") -> int:
        """
        Return contract size data.
        """
        return self.size

    def put_strategy_event(self, strategy: "CtaTemplate") -> None:
        """
        Put an event to update strategy status.
        """
        pass

    def get_all_trades(self) -> list:
        """
        Return all trade data of current backtesting result.
        """
        return list(self.trades.values())

    def get_all_orders(self) -> list:
        """
        Return all limit order data of current backtesting result.
        """
        return list(self.limit_orders.values())

    def get_all_daily_results(self) -> list:
        """
        Return all daily result data.
        """
        return list(self.daily_results.values())
    
    
    def output(self, msg) -> None:
        '''打印信息'''
        print(f"{datetime.now()}\t{msg}")
    



    def clear_data(self) -> None:
        '''
        清空backtesting engine中的缓存数据
        '''
        self.strategy: CtaTemplate = None
        self.tick: TickData = None
        self.bar: BarData = None
        self.datetime: datetime = None

        self.limit_order_count: int = 0
        self.limit_orders: Dict[str, OrderData] = {}
        self.active_limit_orders: Dict[str, OrderData] = {}
        
        self.trade_count: int = 0
        self.trades: Dict[str, TradeData] = {}

        self.logs: list = []

        self.daily_results: Dict[date, DailyResult] = {}



# 缓存(?)999个BarData, 减少IO次数
@lru_cache(maxsize=999)
def load_bar_data(symbol: str, exchange: Exchange, interval: Interval, start: datetime, end: datetime) -> List[BarData]:
    '''从数据库加载bar数据'''
    return get_database().load_bar_data(symbol, exchange, interval, start, end)
    

# 缓存(?)999个TickData, 减少IO次数
@lru_cache(maxsize=999)
def load_tick_data(symbol: str, exchange: Exchange, start: datetime, end: datetime) -> List[TickData]:
    '''从数据库加载tick数据'''
    return get_database().load_tick_data(symbol, exchange, start, end)


class DailyResult:
    """
    https://zhuanlan.zhihu.com/p/267211216
    """

    def __init__(self, date: date, close_price: float) -> None:
        """"""
        self.date: date = date
        self.close_price: float = close_price   # 当日结算价
        self.pre_close: float = 0               # 昨日结算价

        self.trades: List[TradeData] = []
        self.trade_count: int = 0

        self.start_pos = 0                      # 
        self.end_pos = 0                        # 

        self.turnover: float = 0
        self.commission: float = 0
        self.slippage: float = 0

        self.trading_pnl: float = 0             # 
        self.holding_pnl: float = 0             # 
        self.total_pnl: float = 0
        self.net_pnl: float = 0

    def add_trade(self, trade: TradeData) -> None:
        """"""
        self.trades.append(trade)

    def calculate_pnl(
        self,
        pre_close: float,
        start_pos: float,
        size: int,
        rate: float,
        slippage: float
    ) -> None:
        """"""
        # If no pre_close provided on the first day,
        # use value 1 to avoid zero division error
        if pre_close:
            self.pre_close = pre_close
        else:
            self.pre_close = 1

        # Holding pnl is the pnl from holding position at day start
        self.start_pos = start_pos
        self.end_pos = start_pos

        self.holding_pnl = self.start_pos * (self.close_price - self.pre_close) * size

        # Trading pnl is the pnl from new trade during the day
        self.trade_count = len(self.trades)

        for trade in self.trades:
            if trade.direction == Direction.LONG:
                pos_change = trade.fill_volume
            else:
                pos_change = -trade.fill_volume

            self.end_pos += pos_change

            turnover: float = trade.fill_volume * size * trade.fill_price # 成交价 × 成交手数 × 合约乘数
            self.trading_pnl += pos_change * (self.close_price - trade.fill_price) * size
            
            self.slippage += trade.fill_volume * size * slippage  # 

            self.turnover += turnover
            self.commission += turnover * rate                            # 成交价 × 成交手数 × 合约乘数 × 手续费率

        # Net pnl takes account of commission and slippage cost
        self.total_pnl = self.trading_pnl + self.holding_pnl
        self.net_pnl = self.total_pnl - self.commission - self.slippage

