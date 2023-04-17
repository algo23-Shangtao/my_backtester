# Event
EVENT_TICK = "eTick"
EVENT_STRATEGY = "eStrategy"
EVENT_ORDER = "eOrder"
EVENT_TRADE = "eTrade"
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
