'''
定义cta策略中使用的constant和object
'''

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict

from constant import Direction, Offset, Interval

APP_NAME = "CtaStrategy"
STOPORDER_PREFIX = "STOP"

class StopOrderStatus(Enum):
    '''
    Stop Order: 止损单, 价格达到某设定值时, 转化为委托(订单)(?)
    '''
    WAITING = "等待中"
    CANCELLED = "已撤销"
    TRIGGERED = "已触发"

class EngineType(Enum):
    LIVE = "实盘"
    BACKTESTING = "回测"

class BacktestingMode(Enum):
    BAR = 1
    TICK = 2

@dataclass
class StopOrder:
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

EVENT_CTA_LOG = "eCtaLog"
EVENT_CTA_STRATEGY = "eCtaStrategy"
EVENT_CTA_STOPORDER = "eCtaStopOrder"

INTERVAL_DELTA_MAP: Dict[Interval, timedelta] = {
    Interval.TICK: timedelta(microseconds=1),
    Interval.MINUTE: timedelta(minutes=1),
    Interval.DAILY: timedelta(days=1),
}
