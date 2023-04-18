'''
用枚举(enum.Enum)定义一些术语
'''
from enum import Enum

class Direction(Enum):
    '''
    订单、成交、持仓的方向
    '''
    LONG = 1
    SHORT = -1
    # NET = "净"

class Offset(Enum):
    '''
    订单、成交的Offset
    '''
    OPEN = "开"
    CLOSE = "平"
    NONE = "" # 用于初始化

class PosDate(Enum):
    '''
    昨仓or今仓
    '''
    YESTERDAY = 'y'
    TODAY = 't'

class Status(Enum):
    '''
    订单状态
    http://www.khqihuo.com/qhdy/443.html
    '''
    SUBMITTING = "提交中"
    NOTTRADED = "未成交"
    PARTTRADED = "部分成交"
    ALLTRADED = "全部成交"
    CANCELLED = "已撤销"
    REJECTED = "拒单"


class OrderType(Enum):
    '''
    订单种类
    '''
    LIMIT = "限价"
    MARKET = "市价"

class Exchange(Enum):
    '''
    交易所
    '''
    CFFEX = "CFFEX"         # China Financial Futures Exchange
    SHFE = "SHFE"           # Shanghai Futures Exchange
    CZCE = "CZCE"           # Zhengzhou Commodity Exchange
    DCE = "DCE"             # Dalian Commodity Exchange
    INE = "INE"             # Shanghai International Energy Exchange
    GFEX = "GFEX"           # Guangzhou Futures Exchange


class Interval(Enum):
    '''
    时间颗粒度
    '''
    MINUTE = "1m"
    DAILY = 'd'
    TICK = "tick"

