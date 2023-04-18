'''
工具函数
'''


from decimal import Decimal

def round_to(value: float, target: float) -> float:
    '''
    将价格平滑到最小变动幅度(price tick)
    '''
    # Decimal: 精确的浮点运算
    value: Decimal = Decimal(str(value))
    target: Decimal = Decimal(str(target))
    rounded: float = float(int(round(value / target)) * target)
    return rounded





        
