



# Event
EVENT_TICK = "eTick"
EVENT_STRATEGY = "eStrategy"
EVENT_ORDER = "eOrder"
EVENT_TRADE = "eTrade"
EVENT_QUOTE = "eQuote"
EVENT_POSITION = "ePosition"
EVENT_ACCOUNT = "eAccount"
EVENT_CONTRACT = "eContract"
EVENT_LOG = "eLog"
# EVENT_TIMER = "eTimer"



# Order
from constant import Status
ACTIVE_STATUSES = set([Status.SUBMITTING, Status.NOTTRADED, Status.PARTTRADED])
STOPORDER_PREFIX = "STOP"


# Interval timedelta map
from constant import Interval
from datetime import datetime, timedelta
from typing import Dict
INTERVAL_DELTA_MAP: Dict[Interval, timedelta] = {
    Interval.TICK: timedelta(microseconds=1),
    Interval.MINUTE: timedelta(minutes=1),
    Interval.DAILY: timedelta(days=1),
}