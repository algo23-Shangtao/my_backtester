'''
用枚举(enum.Enum)定义一些术语
'''
from enum import Enum

class Direction(Enum):
    '''
    订单、成交、持仓的方向
    '''
    LONG = "多"
    SHORT = "空"
    # NET = "净"

class Offset(Enum):
    '''
    订单、成交的Offset
    '''
    OPEN = "开"
    CLOSE = "平"
    CLOSETODAY = "平今"
    CLOSEYESTERDAY = "平昨"
    NONE = "" # 用于初始化

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

class Product(Enum):
    '''
    标的品种
    '''
    FUTURES = "期货"

class OrderType(Enum):
    '''
    订单种类
    '''
    LIMIT = "限价"
    MARKET = "市价"
    STOP = "停止"

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

    # Special Function
    LOCAL = "LOCAL"         # For local generated data

class Interval(Enum):
    '''
    时间颗粒度
    '''
    MINUTE = "1m"
    DAILY = 'd'
    TICK = "tick"

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