from typing import Dict, List
from datetime import datetime

import numpy as np
import pandas as pd
import dolphindb as ddb
import dolphindb.settings as keys

from datastructure.constant import Exchange, Interval
from datastructure.object import BarData, TickData
from datastructure.setting import SETTING
from .database import BaseDatabase, BarOverview, TickOverview


from utils.data_process import history_tickdata_processor


from .dolphindb_script import CREATE_TICK_DATABASE_SCRIPT, CREATE_TICK_TABLE_SCRIPT, CREATE_TICKOVERVIEW_TABLE_SCRIPT



class Database(BaseDatabase):
    '''
    dolphindb数据库
    '''
    def __init__(self) -> None:
        '''
        构造函数
        '''
        self.user: str = SETTING["database.user"]
        self.password: str = SETTING["database.password"]
        self.host: str = SETTING["database.host"]
        self.port: str = SETTING["database.port"]
        self.db_paths: Dict[str, str] = {"tick_db": "dfs://tick_db", "bar_db": "dfs://bar_db"}
        self.tb_names: Dict[str, str] = {"tick_tb": "tick", "bar_tb": "bar", "tickoverview_tb": "tickoverview", "bar_overview_tb": "baroverview"} # 见dolpindb_script
        # 连接数据库(需提前开启db server)
        self.session = ddb.session()
        self.session.connect(self.host, self.port, self.user, self.password)

        # 初始化数据库和数据表
        self.init_db()
    
    def __del__(self) -> None:
        '''
        析构函数
        '''
        if not self.session.isClosed():
            self.session.close()

    def init_db(self):
        self.init_tick_db()
        self.init_bar_db()
    
    def init_tick_db(self):
        db_path: str = self.db_paths["tick_db"]
        # 创建tick数据库&数据表, 按日分区， 预设数据从20100101到20301230
        if not self.session.existsDatabase(db_path):
            self.session.run(CREATE_TICK_DATABASE_SCRIPT)
            self.session.run(CREATE_TICK_TABLE_SCRIPT)
            self.session.run(CREATE_TICKOVERVIEW_TABLE_SCRIPT)
            print('db inited')
    
    def init_bar_db(self):
        pass
    
    
    def save_bar_data(self, bars: List[BarData], stream: bool = False) -> bool:
        '''
        保存bar数据到db
        '''
        pass


    def save_tick_data(self, ticks: List[TickData], stream: bool = False) -> bool:
        '''
        保存(一个csv文件中的)tick数据到db
        # TODO: 用TSDB, 重复写入处理(keepDuplicate)
        '''
        import warnings # 屏蔽userwarning
        warnings.filterwarnings("ignore")

        db_path: str = self.db_paths['tick_db']
        tb_name: str = self.tb_names['tick_tb']
        data: List[Dict] = []
        
        # 写入tick分布式数据库中
        for tick in ticks:
            # dt = np.datetime64(convert_tz(tick.datetime)) # 为什么要convert_tz
            # dt = convert_tz(tick.datetime)
            # dt = np.datetime64(tick.datetime)
            dt = tick.datetime
            d: dict = {
            'symbol': tick.symbol,
            'exchange': tick.exchange.value,
            'datetime': dt,
            'volume': tick.volume,
            'turnover': tick.turnover,
            'open_interest': tick.open_interest,
            'last_price': tick.last_price,
            'highest_price': tick.highest_price,
            'lowest_price': tick.lowest_price,
            'bid_price_1': tick.bid_price_1,
            'ask_price_1': tick.ask_price_1,
            'bid_volume_1': tick.bid_volume_1,
            'ask_volume_1': tick.ask_volume_1
            }
            data.append(d)
        df: pd.DataFrame = pd.DataFrame.from_records(data)
        # 剔除空dataframe
        if df.empty:
            return False
        
        upsert = ddb.tableUpsert(dbPath=db_path, tableName=tb_name, ddbSession=self.session, keyColNames=['symbol', 'exchange', 'datetime'])
        upsert.upsert(df)

        # 读取主键信息
        tick: TickData = ticks[0]
        symbol: str = tick.symbol
        exchange: Exchange = tick.exchange
        # 计算已有tick数据的汇总
        overview_tb_name = self.tb_names['tickoverview_tb']
        overview_table = self.session.loadTable(tableName=overview_tb_name, dbPath=db_path)
        overview = pd.DataFrame(
            overview_table.select('*').where(f'symbol="{symbol}"').where(f'exchange="{exchange.value}"').toDF()
        )
        if overview.empty: # 首次存入数据
            start: datetime = ticks[0].datetime # np.datetime64(ticks[0].datetime)
            end: datetime = ticks[-1].datetime # np.datetime64(ticks[-1].datetime)
            count: int = len(ticks)
        elif stream: # 记录行情数据---待完善
            start: datetime = overview['start'][0]
            end: datetime = ticks[-1].datetime
            count: int = overview['count'][0] + len(ticks)
        else: # 补充已有数据
            start: datetime = min(overview['start'][0], ticks[0].datetime)
            end: datetime = max(overview['end'][0], ticks[-1].datetime)
            tick_tb = self.session.loadTable(tableName=tb_name, dbPath=db_path)
            df_count: pd.DataFrame = tick_tb.select('count(*)').where(f'symbol="{symbol}"').where(f'exchange="{exchange.value}"').toDF()
            count: int = df_count['count'][0]
            # 删除原汇总数据
            overview_table.delete().where(f"symbol=`{symbol}").where(f"exchange=`{exchange.value}").execute()
            # print("delete")
        # 更新tick汇总数据
        data: List[Dict] = []
        dt = np.datetime64(datetime.now()) # 数据上传时间 --- 用于分区
        d: Dict = {
            "symbol": symbol,
            "exchange": exchange.value,
            "count": count,
            "start": start,
            "end": end,
            "datetime": dt
        }
        data.append(d)
        df: pd.DataFrame = pd.DataFrame.from_records(data)
        upsert = ddb.tableUpsert(dbPath=db_path, tableName=overview_tb_name, ddbSession=self.session, keyColNames=['symbol', 'exchange', 'datetime'])
        upsert.upsert(df)
        
        return True

    
    def load_bar_data(self, symbol: str, exchange: Exchange, interval: Interval, start: datetime, end: datetime) -> List[BarData]:
        '''
        从db读取bar数据
        '''
        pass
    
    
    def load_tick_data(self, symbol: str, exchange: Exchange, start: datetime = datetime(2010,1,1), end: datetime = datetime(2030,1,1)) -> List[TickData]:
        '''
        从db读取tick数据, 不输入开始结束日期则读取全部数据
        '''
        db_path: str = self.db_paths['tick_db']
        tb_name: str = self.tb_names['tick_tb']
        # 读取数据df
        table = self.session.loadTable(tableName=tb_name, dbPath=db_path)
        whole_df: pd.DataFrame = table.select('*').where(f'symbol="{symbol}"').where(f'exchange="{exchange.value}"').toDF()
        df:pd.DataFrame = whole_df.loc[(whole_df['datetime'] >= start) & (whole_df['datetime'] <= end),:]
        if df.empty:
            return []
        df.set_index("datetime", inplace=True)
        # df = df.tz_localize(DB_TZ.key)
        df.reset_index(inplace=True)
        # 转换为TickData格式
        # 使用df2data
        TickData_list: list[TickData] = history_tickdata_processor.df2data(df)
        return TickData_list
        
    
    def delete_bar_data(self, symbol: str, exchange: Exchange, interval: Interval) -> int:
        '''
        删除所有时间段指定数据
        '''
        pass

    
    def delete_tick_data(self, symbol: str, exchange: Exchange) -> int:
        '''
        删除所有时间指定数据
        '''
        db_path: str = self.db_paths['tick_db']
        tb_name: str = self.tb_names['tick_tb']
        # 统计数据量
        table = self.session.loadTable(tableName=tb_name, dbPath=db_path)
        df: pd.DataFrame = table.select('count(*)').where(f'symbol="{symbol}"').where(f'exchange="{exchange.value}"').toDF()
        count: int = df['count'][0]
        # 删除tick数据
        table.delete().where(f'symbol="{symbol}"').where(f'exchange="{exchange.value}"').execute()
        # 删除tickoverview数据
        tb_name: str = self.tb_names['tickoverview_tb']
        table = self.session.loadTable(tableName=tb_name, dbPath=db_path)
        table.delete().where(f'symbol="{symbol}"').where(f'exchange="{exchange.value}"').execute()

        return count
    
    def get_bar_overview(self) -> List[BarOverview]:
        '''
        查看数据库中支持的bar数据(哪些合约)
        '''
        pass

    
    def get_tick_overview(self) -> List[TickOverview]:
        '''
        查看数据库中支持的tick数据(哪些合约)
        '''
        tb_name: str = self.tb_names['tickoverview_tb']
        db_path: str = self.db_paths['tick_db']
        overview_table = self.session.loadTable(tableName=tb_name, dbPath=db_path)
        overview_df: pd.DataFrame = overview_table.toDF()
        list_of_tickoverview: List[TickOverview] = []
        for index, row in overview_df.iterrows():
            overview: TickOverview = TickOverview(
                symbol=row['symbol'],
                exchange=Exchange(row['exchange']),
                count=row['count'],
                start=row['start'],
                end = row['end']
            )
            list_of_tickoverview.append(overview)
        return list_of_tickoverview
        

    def _save_all_history_tickdata(self) -> bool:
        '''
        写入文件夹中历史数据---只可写入一次!
        #TODO: 都什么年代, 还在写两层for循环(甚至3层)? userwarning处理
        '''
        data_processor = history_tickdata_processor()
        for key in data_processor.all_csv_paths.keys():
        # 遍历存放全合约每日数据的日数据文件夹
            daily_csv_paths = data_processor.all_csv_paths[key]
            # 遍历该日所有合约的数据
            for csv_path in daily_csv_paths:
                daily_df = data_processor.tqsdk_data_process(csv_path)
                list_of_tickdata = data_processor.df2data(daily_df)
                self.save_tick_data(list_of_tickdata)
        


        

