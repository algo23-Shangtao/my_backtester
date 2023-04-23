from abc import ABC, abstractmethod



from .event import EventEngine


class BaseEngine(ABC):
    '''
    function engine抽象类
    封装main_engine和event_engine
    封装处理event的回调函数, 并注册回调函数
    '''
    def __init__(self, event_engine: EventEngine, engine_name: str) -> None:
        self.event_engine: EventEngine = event_engine
        self.engine_name: str = engine_name
    

