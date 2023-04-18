'''
tqsdk数据处理脚本
'''

from typing import Tuple, List, Dict
import pandas as pd
from datetime import datetime
import os

from datastructure.object import TickData
from datastructure.constant import Exchange




class history_tickdata_processor: ##待完善
    '''
    输入存放历史数据csv的文件夹地址, 每个csv文件生成回测框架通用数据类型(TickData)的列表
    '''
    def __init__(self, product_folder_path="/home/tushetou/futures_history_data"):
        self.product_folder_path: str = product_folder_path
        self.daily_folder_paths: List[str] = [self.product_folder_path + '/' + daily for daily in os.listdir(self.product_folder_path)]
        self.all_csv_paths: Dict[str: List[str]] = self.get_all_csv_paths()
    
    def get_all_csv_paths(self):
        d: Dict = {}
        for daily_folder_path in self.daily_folder_paths:
            csv_paths: List[str] = [daily_folder_path + '/' + csv for csv in os.listdir(daily_folder_path)]
            d[daily_folder_path] = csv_paths
        return d



    # 给定标的, 返回交易时间段
    @staticmethod
    def get_trading_time (asset: str) -> Tuple:
        ###refer to : http://qhsxf.com/%E6%9C%9F%E8%B4%A7%E4%BA%A4%E6%98%93%E6%97%B6%E9%97%B4.html
        CZCE_NIGHT1 = ['fg', 'sa', 'ma', 'sr', 'ta', 'rm', 'oi', 'cf', 'cf', 'cy', 'pf', 'zc']
        CZCE_NIGHT2 = ['sm', 'sf', 'wh', 'jr', 'lr', 'pm', 'ri', 'rs', 'pk', 'ur', 'cj', 'ap']
        DCE_NIGHT1 = ['i', 'j', 'jm', 'a', 'b', 'ma', 'p', 'y', 'c', 'cs', 'pp', 'v', 'eb', 'eg', 'pg', 'rr', 'i']
        DCE_NIGHT2 = ['bb', 'fb' 'Ih', 'jd']
        SHFE_NIGHT1 = ['cu', 'pb', 'al', 'zn', 'sn', 'ni', 'ss']
        SHFE_NIGHT2 = ['fu', 'ru', 'bu', 'sp', 'rb', 'hc']
        SHFE_NIGHT3 = ['au', 'ag']
        SHFE_NIGHT4 = ['wr']
        GFEX_NIGHT = ['si']
        INE_NIGHT1 = ['sc']
        INE_NIGHT2 = ['bc']
        INE_NIGHT3 = ['lu', 'nr']
        CFFEX_DAY1  = ['if', 'ih', 'ic', 'im']
        CFFEX_DAY2 = ['t', 'tf', 'ts']
        if asset in CZCE_NIGHT1 or asset in DCE_NIGHT1 or asset in SHFE_NIGHT2 or asset in INE_NIGHT3: 
            return ("21:00:00.500000000", "23:00:00.000000000", "09:00:00.500000000", "10:15:00.000000000", "10:30:00.500000000", "11:30:00.000000000", "13:30:00.500000000","15:00:00.000000000")
        if asset in SHFE_NIGHT1 or asset in INE_NIGHT2:
            return ("21:00:00.500000000", "01:00:00.000000000", "09:00:00.500000000", "10:15:00.000000000", "10:30:00.500000000", "11:30:00.000000000", "13:30:00.500000000","15:00:00.000000000")
        if asset in SHFE_NIGHT3 or asset in INE_NIGHT1:
            return ("21:00:00.500000000", "02:30:00.000000000", "09:00:00.500000000", "10:15:00.000000000", "10:30:00.500000000", "11:30:00.000000000", "13:30:00.500000000","15:00:00.000000000")
        if asset in CZCE_NIGHT2 or asset in DCE_NIGHT2 or asset in SHFE_NIGHT4 or asset in GFEX_NIGHT:
            return ("99:99:99.000000000", "99:99:99.500000000", "09:00:00.500000000", "10:15:00.000000000", "10:30:00.500000000", "11:30:00.000000000", "13:30:00.500000000", "15:00:00.000000000")
        # 暂时不支持中金所
        # if asset in CFFEX_DAY1:
        #     return ("00:00:00.000000000", "00:00:00.500000000", "09:30:00.500000000", "11:30:00.000000000", "13:00:00.500000000", "15:00:00.000000000")
        # if asset in CFFEX_DAY2:
        #     return ("00:00:00.000000000", "00:00:00.500000000", "09:15:00.500000000", "11:30:00.000000000", "13:00:00.500000000", "15:15:00.000000000")
        # 其他不支持的品种
        else:
            return ("99:99:99.000000000","99:99:99.000000000","99:99:99.000000000","99:99:99.000000000","99:99:99.000000000","99:99:99.000000000","99:99:99.000000000","99:99:99.000000000")
    
    # 剔除非交易时间段数据
    @classmethod
    def split_no_trading_time_df(cls, df: pd.DataFrame, asset: str) -> pd.DataFrame:
        dp = cls()
        (s0, e0, s1, e1, s2, e2, s3, e3)= dp.get_trading_time(asset)
        hms = df['datetime'].apply(lambda x: float('nan') if pd.isna(x) else x[11:])# hms:时分秒
        if s0 <= e0:
            df = df.loc[((hms >= s0)&(hms <=e0))|((hms >= s1)&(hms <=e1))|((hms >= s2)&(hms <=e2))|((hms >= s3)&(hms <=e3))]
        else:
            df = df.loc[((hms >= s0)&(hms <='23:59:59.500000000'))|((hms >= '00:00:00.000000000')&(hms <=e0))|((hms >= s1)&(hms <=e1))|((hms >= s2)&(hms <=e2))|((hms >= s3)&(hms <=e3))]
        return df

    # dropna数据, 加入exchange, symbol字段, 剔除非交易时间段数据, 删除datetime_nano, column名字更新
    @classmethod
    def tqsdk_data_process(cls, csv_path: str) -> pd.DataFrame:
        '''
        输入单个csv文件路径
        输出清洗后改csv文件的dataframe
        '''
        dp = cls()
        df = pd.read_csv(csv_path)
        exchange_str, symbol_str,  = df.columns[2].split('.')[:2]
        df.drop(['datetime_nano'], axis=1, inplace=True)
        df.dropna(inplace=True)
        # 检查数据是否有多余字段, 删除额外信息
        if len(df.columns) > 11:
            prefix = f"{exchange_str}.{symbol_str}." 
            df = df.loc[:, ['datetime', prefix + 'last_price', prefix + 'highest', prefix + 'lowest', prefix + 'volume', prefix + 'amount', prefix + 'open_interest', 
                            prefix + 'bid_price1', prefix + 'bid_volume1', prefix + 'ask_price1', prefix + 'ask_volume1']]

        df.columns = ['datetime', 'last_price', 'highest_price', 'lowest_price', 'volume', 'turnover', 'open_interest', 'bid_price_1', 'bid_volume_1', 'ask_price_1', 'ask_volume_1']
        df['datetime'] = df['datetime'].apply(lambda x: x[:-3])
        df['symbol'] = symbol_str
        df['exchange'] = exchange_str
        symbol_type = ''.join([chr for chr in symbol_str if chr.isalpha() ])
        symbol_type = symbol_type.lower()
        df = dp.split_no_trading_time_df(df, symbol_type)
        df['datetime'] = df['datetime'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f")) # 时间格式由字符串转换为datetime
        return df
    
    @staticmethod
    def df2data(df: pd.DataFrame) -> List[TickData]:
        '''
        输入清洗后单个csv文件的dataframe
        输出该文件的list of tickdata
        '''
        TickData_list: list[TickData] = []
        for index, row in df.iterrows():
            data: TickData = TickData(
                symbol=row['symbol'],
                exchange=Exchange(row['exchange']),
                datetime=row['datetime'],
                volume=row['volume'],
                turnover=row["turnover"],
                open_interest=row['open_interest'],
                last_price=row['last_price'],
                highest_price=row['highest_price'],
                lowest_price=row['lowest_price'],
                bid_price_1=row['bid_price_1'],
                bid_volume_1=row['bid_volume_1'],
                ask_price_1=row['ask_price_1'],
                ask_volume_1=row['ask_volume_1']
            )
            TickData_list.append(data)
        return TickData_list
