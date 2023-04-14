from copy import copy
from typing import Dict, List, Set, TYPE_CHECKING

from object import ContractData, OrderData, TradeData, PositionData, OrderRequest
from constant import Direction, Offset, Exchange

if TYPE_CHECKING:
    from engine import MainEngine


class PositionHolding:
    '''
    某合约当前的详细仓位信息(PositionHolding)--针对允许同时多空的合约？
        平仓规则: http://www.khqihuo.com/qhdy/760.html
        平仓手续费: https://www.9qihuo.com/qihuoshouxufei
        未成交持仓被冻结: http://www.khqihuo.com/qhdy/1911.html
    '''
    def __init__(self, contract: ContractData) -> None:
        self.vt_symbol: str = contract.vt_symbol
        self.exchange: Exchange = contract.exchange
        self.active_orders: Dict[str, OrderData] = {} # 该合约active订单
        
        # 可平仓数量为持仓数量减去冻结数量,冻结数量为已申报未成交的数量
        self.long_pos: float = 0    # 总持仓
        self.long_yd: float = 0     # 昨持仓
        self.long_td: float = 0     # 今持仓

        self.short_pos: float = 0   
        self.short_yd: float = 0
        self.short_td: float = 0

        self.long_pos_frozen: float = 0    # 总冻结
        self.long_yd_frozen: float = 0     # 昨冻结
        self.long_td_frozen: float = 0     # 今冻结

    def update_position(self, position: PositionData) -> None:
        '''
        根据新的仓位信息(position)更新该合约当前的详细仓位信息(PositionHolding)
        '''
        if position.direction == Direction.LONG:
            self.long_pos = position.volume
            self.long_yd = position.yd_volume
            self.long_td = self.long_pos - self.long_yd
        else:
            self.short_pos = position.volume
            self.short_yd = position.yd_volume
            self.short_td = self.short_pos - self.short_yd
    
    def update_trade(self, trade: TradeData) -> None:
        '''
        根据成交信息(trade)更新该合约当前的详细仓位信息(PositionHolding)---@TODO成交不应该调节冻结数量吗? 为什么直接调整总持仓(或者是可用)
        http://www.khqihuo.com/qhdy/456.html
        '''
        if trade.direction == Direction.LONG:

            if trade.offset == Offset.OPEN:
                self.long_td += trade.volume
            elif trade.offset == Offset.CLOSETODAY: # 上期所、上期能源可以选择平昨或平今
                self.short_td -= trade.volume
            elif trade.offset == Offset.CLOSEYESTERDAY: # 上期所、上期能源可以选择平昨或平今
                self.short_yd -= trade.volume
            #### 以下为vnpy源码
            elif trade.offset == Offset.CLOSE:
                if trade.exchange in [Exchange.SHFE, Exchange.INE]: # 上交所、上期能源可以选择平昨或平今, 默认为平昨
                    self.short_yd -= trade.volume
                    ### ??????????????????????????self.short_yd < 0?
                else:                                               # 其他期货交易所只能先平昨再平今?????????????
                    self.short_td -= trade.volume
                    if self.short_td < 0:
                        self.short_yd += self.short_td
                        self.short_td = 0
            #### 以下为我的想法
            # elif trade.offset == Offset.CLOSE: # 其他交易所只能先平昨再平今
            #     self.short_yd -= trade.volume
            #     if self.short_yd < 0:
            #         self.short_td += self.short_yd
            #         self.short_yd = 0
            #### 如果self.short_td < 0怎么办?(more than total volume)
        else:
            if trade.offset == Offset.OPEN:
                self.short_td += trade.volume
            elif trade.offset == Offset.CLOSETODAY:
                self.long_td -= trade.volume
            elif trade.offset == Offset.CLOSEYESTERDAY:
                self.long_yd -= trade.volume

            #### 以下为vnpy源码
            elif trade.offset == Offset.CLOSE:
                if trade.exchange in [Exchange.SHFE, Exchange.INE]: # 上交所、上期能源先平昨再平今
                    self.long_yd -= trade.volume
                    # ??????????????????????????self.long_yd < 0?
                else:                                               # 其他期货交易所先平今再平昨
                    self.long_td -= trade.volume
                    if self.long_td < 0:
                        self.long_yd += self.short_td
                        self.long_td = 0
            #### 以下为我的想法
            # elif trade.offset == Offset.CLOSE: # 其他交易所只能先平昨再平今
            #     self.long_yd -= trade.volume
            #     if self.long_yd < 0:
            #         self.long_td += self.long_yd
            #         self.long_yd = 0
            #### 如果self.long_td < 0怎么办?(more than total volume)
        
        self.long_pos = self.long_td + self.long_yd
        self.short_pos = self.short_td + self.short_yd

        # update frozen volume to ensure no more than total volume            
        self.sum_pos_frozen()
    
    
    def sum_pos_frozen(self) -> None:
        '''
        什么玩意!!!!@TODO成交不应该调节冻结数量吗? 为什么直接调整总持仓(或者是可用)
        '''
        # frozen volume should be no more than total volume
        self.long_td_frozen = min(self.long_td_frozen, self.long_td) # 这是优先改变可用吗?
        self.long_yd_frozen = min(self.long_yd_frozen, self.long_yd)
        self.short_td_frozen = min(self.short_td_frozen, self.short_td)
        self.short_yd_frozen = min(self.short_yd_frozen, self.short_yd)

        self.long_pos_frozen = self.long_td_frozen + self.long_yd_frozen
        self.short_pos_frozen = self.short_td_frozen + self.short_yd_frozen


    def update_order_request(self, req: OrderRequest, vt_orderid: str) -> None:
        '''
        根据委托请求, 更新订单的状态
        ''' 
        # 根据委托请求, 创建委托
        gateway_name, orderid = vt_orderid.split(".")
        order: OrderData = req.create_order_data(orderid, gateway_name)
        # 根据委托更新
        self.update_order(order)

    def update_order(self, order: OrderData) -> None:
        '''
        根据委托更新详细仓位: 记录active订单; 
        已申报未成交为冻结: 调整冻结数量
        '''
        if order.is_active(): # 记录active订单
            self.active_orders[order.vt_orderid] = order
        else: # 移除非active订单
            if order.vt_orderid in self.active_orders:
                self.active_orders.pop(order.vt_orderid)
        self.calculate_frozen()
    
    
    def calculate_frozen(self) -> None:
        '''
        调整冻结数量
        '''
        # 重新完整计算冻结数量
        self.long_pos_frozen = 0
        self.long_yd_frozen = 0
        self.long_td_frozen = 0
        self.short_pos_frozen = 0
        self.short_yd_frozen = 0
        self.short_td_frozen = 0
        # 遍历所有挂单
        for order in self.active_orders.values():
            # 不需要考虑开仓委托
            if order.offset == Offset.OPEN:
                continue

            frozen: float = order.volume - order.traded

            if order.direction == Direction.LONG:
                if order.offset == Offset.CLOSETODAY:
                    self.short_td_frozen += frozen
                elif order.offset == Offset.CLOSEYESTERDAY:
                    self.short_yd_frozen += frozen
                elif order.offset == Offset.CLOSE:
                    #### 以下为vnpy源码
                    self.short_td_frozen += frozen # 到底是先平昨还是先平今?????????????????????
                    if self.short_td_frozen > self.short_td:
                        self.short_yd_frozen += (self.short_td_frozen - self.short_td)
                        self.short_td_frozen = self.short_td
        self.sum_pos_frozen()
    
    
    ####TODO 下面三个函数到底什么联系什么区别?
    def convert_order_request_shfe(self, req: OrderRequest) -> List[OrderRequest]:
        '''转换委托, 但是上期所: 能平今则平今'''
        if req.offset == Offset.OPEN:
            return [req]
        # 计算可用
        if req.direction == Direction.LONG:
            pos_available: int = self.short_pos - self.short_pos_frozen
            td_available: int = self.short_td - self.short_td_frozen
        else:
            pos_available: int = self.long_pos - self.long_pos_frozen
            td_available: int = self.long_td - self.long_td_frozen
        # 委托数量大于总可用数量, 无法下单
        if req.volume > pos_available:
            return []
        # 委托数量小于今日可用数量, 将offset改为平今
        elif req.volume <= td_available:
            req_td: OrderRequest = copy(req)
            req_td.offset = Offset.CLOSETODAY
            return [req_td]
        # 委托数量大于今日可用数量, 小于总可用数量,
        else:
            req_list: List[OrderRequest] = []
            # 今日可用数量大于0, 今日可用全部平掉, 剩下平昨
            if td_available > 0:
                req_td: OrderRequest = copy(req)
                req_td.offset = Offset.CLOSETODAY
                req_td.volume = td_available
                req_list.append(req_td)
            # (今日可用数量小于0)剩下平昨
            req_yd: OrderRequest = copy(req)
            req_yd.offset = Offset.CLOSEYESTERDAY
            req_yd.volume = req.volume - td_available
            req_list.append(req_yd)
            return req_list
    
    def convert_order_request_lock(self, req: OrderRequest) -> List[OrderRequest]:
        '''转换委托, 但是锁仓模式'''
        if req.direction == Direction.LONG:
            td_volume: int = self.short_td
            yd_available: int = self.short_yd - self.short_yd_frozen
        else:
            td_volume: int = self.long_td
            yd_available: int = self.long_yd - self.long_yd_frozen

        close_yd_exchanges: Set[Exchange] = {Exchange.SHFE, Exchange.INE}

        # If there is td_volume, we can only lock position
        if td_volume and self.exchange not in close_yd_exchanges:
            req_open: OrderRequest = copy(req)
            req_open.offset = Offset.OPEN
            return [req_open]
        # If no td_volume, we close opposite yd position first
        # then open new position
        else:
            close_volume: int = min(req.volume, yd_available)
            open_volume: int = max(0, req.volume - yd_available)
            req_list: List[OrderRequest] = []

            if yd_available:
                req_yd: OrderRequest = copy(req)
                if self.exchange in close_yd_exchanges:
                    req_yd.offset = Offset.CLOSEYESTERDAY
                else:
                    req_yd.offset = Offset.CLOSE
                req_yd.volume = close_volume
                req_list.append(req_yd)

            if open_volume:
                req_open: OrderRequest = copy(req)
                req_open.offset = Offset.OPEN
                req_open.volume = open_volume
                req_list.append(req_open)

            return req_list

    def convert_order_request_net(self, req: OrderRequest) -> List[OrderRequest]:
        """@TODO net到底是什么意思? 净仓模式?"""
        if req.direction == Direction.LONG:
            pos_available: int = self.short_pos - self.short_pos_frozen
            td_available: int = self.short_td - self.short_td_frozen
            yd_available: int = self.short_yd - self.short_yd_frozen
        else:
            pos_available: int = self.long_pos - self.long_pos_frozen
            td_available: int = self.long_td - self.long_td_frozen
            yd_available: int = self.long_yd - self.long_yd_frozen

        # Split close order to close today/yesterday for SHFE/INE exchange
        if req.exchange in {Exchange.SHFE, Exchange.INE}:
            reqs: List[OrderRequest] = []
            volume_left: float = req.volume
            # 若今仓有可用仓位,
            if td_available:
                # 先平今, 平完为止
                td_volume: int = min(td_available, volume_left)
                volume_left -= td_volume

                td_req: OrderRequest = copy(req)
                td_req.offset = Offset.CLOSETODAY
                td_req.volume = td_volume
                reqs.append(td_req)
            # 若今仓可用仓位不足, 且昨仓有可用仓位
            if volume_left and yd_available:
                # 再平昨
                yd_volume: int = min(yd_available, volume_left)
                volume_left -= yd_volume

                yd_req: OrderRequest = copy(req)
                yd_req.offset = Offset.CLOSEYESTERDAY
                yd_req.volume = yd_volume
                reqs.append(yd_req)
            # 若可用仓位不足, 再反向开仓
            if volume_left > 0:
                open_volume: int = volume_left

                open_req: OrderRequest = copy(req)
                open_req.offset = Offset.OPEN
                open_req.volume = open_volume
                reqs.append(open_req)

            return reqs
        # Just use close for other exchanges
        else:
            reqs: List[OrderRequest] = []
            volume_left: float = req.volume
            # 平可用, 若超出可用数量则再反向开仓
            if pos_available:
                close_volume: int = min(pos_available, volume_left)
                volume_left -= pos_available

                close_req: OrderRequest = copy(req)
                close_req.offset = Offset.CLOSE
                close_req.volume = close_volume
                reqs.append(close_req)

            if volume_left > 0:
                open_volume: int = volume_left

                open_req: OrderRequest = copy(req)
                open_req.offset = Offset.OPEN
                open_req.volume = open_volume
                reqs.append(open_req)

            return reqs


            

class OffsetConverter:
    '''
    封装了详细仓位信息Dict(self.holdings)
    对于每个合约, 判断是否需要convert, 再调用PositionHolding的仓位更新方法
    '''
    def __init__(self, main_engine: "MainEngine") -> None:
        self.holdings: Dict[str, "PositionHolding"] = {} # {vt_symbol: PositionHolding}
        self.get_contract = main_engine.get_contract

    def is_convert_required(self, vt_symbol: str) -> bool:
        '''
        检查该合约是否需要offset convert ---?不需要convert的合约仓位在哪更新?
        '''
        contract: ContractData = self.get_contract(vt_symbol)
        if not contract:
            return False
        elif contract.net_position:
            return False
        else:
            return True
        
    def get_position_holding(self, vt_symbol: str) -> "PositionHolding":
        '''
        根据合约名得到该合约当前持仓详细信息; 若没有持仓, 则初始化一个仓位
        '''
        holding: PositionHolding = self.holdings.get(vt_symbol, None)
        if not holding:
            contract: ContractData = self.get_contract(vt_symbol)
            holding = PositionHolding(contract)
            self.holdings[vt_symbol] = holding
        return holding


    def update_position(self, position: PositionData) -> None:
        '''
        根据最新的仓位信息更新详细仓位信息
        '''
        if not self.is_convert_required(position.vt_symbol):
            return
        holding: PositionHolding = self.get_position_holding(position.vt_symbol)
        holding.update_position(position)
    
    def update_trade(self, trade: TradeData) -> None:
        '''
        根据最新的成交信息更新详细仓位信息
        '''
        if not self.is_convert_required(trade.vt_symbol):
            return
        holding: PositionHolding = self.get_position_holding(trade.vt_symbol)
        holding.update_trade(trade)

    def update_order(self, order: OrderData) -> None:
        '''
        根据最新的委托信息更新详细仓位信息
        '''
        if not self.is_convert_required(order.vt_symbol):
            return
        holding: PositionHolding = self.get_position_holding(order.vt_symbol)
        holding.update_order(order)       

    def update_order_request(self, req: OrderRequest, vt_orderid: str) -> None:
        if not self.is_convert_required(req.vt_symbol):
            return
        holding: PositionHolding = self.get_position_holding(req.vt_symbol)
        holding.update_order_request(req, vt_orderid)


    
    def convert_order_request(self, req: OrderRequest, lock: bool, net: bool = False) -> List[OrderRequest]:
        '''
        lock: 锁仓(http://www.khqihuo.com/qhdy/592.html?)
        net: ?
        '''
        if not self.is_convert_required(req.vt_symbol):
            return [req]
        holding: PositionHolding = self.get_position_holding(req.vt_symbol)

        if lock:
            return holding.convert_order_request_lock(req)
        elif net:
            return holding.convert_order_request_net(req)
        elif req.exchange in [Exchange.SHFE, Exchange.INE]:
            return holding.convert_order_request_shfe(req)
        else:
            return [req]
    



