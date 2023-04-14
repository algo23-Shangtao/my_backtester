'''
工具函数
'''
import sys
from typing import Tuple, Callable
from pathlib import Path
from decimal import Decimal

from datastructure.constant import Exchange

import json

def extract_vt_symbol(vt_symbol: str) -> Tuple[str, Exchange]:
    symbol, exchange_str = vt_symbol.split('.')
    return symbol, Exchange(exchange_str)


def _get_trader_dir(temp_name: str) -> Tuple[Path, Path]:
    cwd: Path = Path.cwd()
    temp_path: Path = cwd.joinpath(temp_name)

    return cwd, temp_path

TRADER_DIR, TEMP_DIR = _get_trader_dir(".temp")
sys.path.append(str(TRADER_DIR))

def get_file_path(filename: str) -> Path:
    '''
    从temp文件夹中获得文件路径
    '''
    return TEMP_DIR.joinpath(filename)

def get_folder_path(folder_name: str) -> Path:
    '''
    从temp文件夹中获得文件夹路径
    '''
    folder_path: Path = TEMP_DIR.joinpath(folder_name)
    if not folder_path.exists:
        folder_path.mkdir()
    return folder_path

def load_json(filename: str) -> dict:
    '''
    从temp文件夹中读取json文件
    '''
    filepath: Path = get_file_path(filename)

    if filepath.exists():
        with open(filepath, mode='r', encoding='UTF-8') as f:
            data: dict = json.load(f)
        return data
    else:
        save_json(filename, {})
        return {}
    
def save_json(filename: str, data: dict) -> None:
    '''
    将数据以json文件格式保存在temp文件夹中
    '''
    filepath: Path = get_file_path(filename)
    with open(filepath, mode='w+', encoding='UTF-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def round_to(value: float, target: float) -> float:
    '''
    将价格平滑到最小变动幅度(price tick)
    '''
    # Decimal: 精确的浮点运算
    value: Decimal = Decimal(str(value))
    target: Decimal = Decimal(str(target))
    rounded: float = float(int(round(value / target)) * target)
    return rounded

# def virtual(func: Callable) -> Callable: #### 干嘛不用@abstractmethod? 闲的吗?
#     '''
#     自制的virtual关键字, 示意该函数为纯虚函数
#     '''
#     return func



        
