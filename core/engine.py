import logging
from logging import Logger

from abc import ABC
from pathlib import Path
from datetime import datetime


from event import Event, EventEngine
from event import EVENT_LOG
from gw.gateway import BaseGateway
from datastructure.object import LogData
from datastructure.setting import SETTING
from utils.utils_function import get_folder_path


class BaseEngine(ABC):
    '''
    function engine抽象类
    封装main_engine和event_engine
    封装处理event的回调函数, 并注册回调函数
    '''
    def __init__(self, event_engine: EventEngine, engine_name: str) -> None:
        self.event_engine: EventEngine = event_engine
        self.engine_name: str = engine_name
    def close(self) -> None:
        pass



class LogEngine(BaseEngine):
    '''
    根据全局设置中日志设置, 封装一个Logger实例
    回调函数: 用Logger处理logEvent--输出日志
    '''
    def __init__(self,event_engine: EventEngine) -> None:
        super(LogEngine, self).__init__(event_engine)
        # super(self).__init__(main_engine, event_engine)
        if not SETTING['log_active']:
            return
        self.level: int = SETTING['log.level']
        self.logger: Logger = logging.getLogger("tushetou")
        self.logger.setLevel(self.level)
        self.formatter: logging.Formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        self.add_null_handler()
        if SETTING["log.console"]:
            self.add_console_handler()
        if SETTING["log.file"]:
            self.add_file_handler()
        self.register_event()


    def add_null_handler(self) -> None:
        """
        Add null handler for logger.
        """
        null_handler: logging.NullHandler = logging.NullHandler()
        self.logger.addHandler(null_handler)

    def add_console_handler(self) -> None:
        """
        Add console output of log.
        """
        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def add_file_handler(self) -> None:
        """
        Add file output of log.
        """
        today_date: str = datetime.now().strftime("%Y%m%d")
        filename: str = f"vt_{today_date}.log"
        log_path: Path = get_folder_path("log")
        file_path: Path = log_path.joinpath(filename)

        file_handler: logging.FileHandler = logging.FileHandler(
            file_path, mode="a", encoding="utf8"
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def register_event(self) -> None:
        '''注册回调函数到eventEngine'''
        self.event_engine.register(EVENT_LOG, self.process_log_event)
    
    def process_log_event(self, event: Event) -> None:
        '''处理logEvent的回调函数'''
        log: LogData = event.data
        self.logger.log(log.level, log.msg)