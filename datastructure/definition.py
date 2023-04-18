# Event
EVENT_TICK = "eTick"
EVENT_STRATEGY = "eStrategy"
EVENT_ORDER = "eOrder"
EVENT_TRADE = "eTrade"
EVENT_REQUEST = "eRequest"
EVENT_LOG = "eLog"




# Order
from .constant import Status
ACTIVE_STATUSES = set([Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED])



# Interval timedelta map
from .constant import Interval
from datetime import datetime, timedelta
from typing import Dict
INTERVAL_DELTA_MAP: Dict[Interval, timedelta] = {
    Interval.TICK: timedelta(microseconds=1),
    Interval.MINUTE: timedelta(minutes=1),
    Interval.DAILY: timedelta(days=1),
}

# exchange_str exchange map
from .constant import Exchange
CN_EXCHANGE_MAP: Dict[str, Exchange] = {
    '上期所': Exchange.SHFE,
    '上期能源': Exchange.INE,
    '郑商所': Exchange.CZCE,
    '大商所': Exchange.DCE,
    '中金所': Exchange.CFFEX,
    '广期所': Exchange.GFEX
}