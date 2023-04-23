from collections import defaultdict
from queue import Queue, Empty
from typing import Any, Callable, List
'''
事件类型
'''
from datastructure.definition import (
    EVENT_TICK,
    EVENT_STRATEGY,
    EVENT_ORDER,
    EVENT_TRADE,
    EVENT_REQUEST,
    EVENT_LOG
)

class Event:
    '''
    事件类
    '''
    def __init__(self, type: str, data: Any = None) -> None:
        self.type = type
        self.data = data

# 定义一个函数句柄用于注释---接收一个事件，实现相应处理该事件的逻辑
HandlerType: callable = Callable[[Event], None]

class EventEngine:
    '''
    1.事件处理引擎, 注册回调函数 & 产生并处理事件
    (2.产生timer event用于记时(interval, 默认为1秒))
    '''
    def __init__(self) -> None:
        self._queue: Queue = Queue()
        self._active: bool = False # 是否启动引擎
        self._handlers: defaultdict = defaultdict(list) # dict[event_type, handler_list]
        self._general_handlers: List = []

    def _run(self) -> None:
        '''
        从事件队列中取出事件, 并处理
        '''
        while self._active:
            try: 
                event: Event = self._queue.get(block=True, timeout=1)
                self._process(event)
            except Empty:
                # print("事件队列为空")
                self._active = False

    def _process(self, event: Event) -> None:
        '''
        1.根据注册的回调函数处理不同事件类型
        2.执行不同事件类型通用的回调函数
        '''
        if event.type in self._handlers:
            [handler(event) for handler in self._handlers[event.type]]
        if self._general_handlers:
            [handler(event) for handler in self._general_handlers]
    

    def start(self) -> None:
        '''
        开启事件引擎---处理事件
        '''
        self._active = True
        self._run()

    def stop(self) -> None:
        '''
        停止事件引擎
        '''
        self._active = False

    def put(self, event: Event) -> None:
        '''
        将事件放入事件队列
        '''
        self._queue.put(event)
    
    def register(self, type: str, handler: HandlerType) -> None:
        '''
        注册处理某事件的回调函数
        '''
        handler_list: List = self._handlers[type]
        if handler not in handler_list:
            handler_list.append(handler)

    def register_general(self, handler: HandlerType) -> None:
        '''
        注册通用回调函数
        '''
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)

    def unregister(self, type: str, handler: HandlerType) -> None:
        '''
        取消注册处理某事件的回调函数
        '''
        handler_list = self._handlers[type]
        if handler in handler_list:
            handler_list.remove(handler)
        if not handler_list:
            self._handlers.pop(type)
    
    def unregister_general(self, handler: HandlerType) -> None:
        '''
        取消注册通用回调函数
        '''
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)


