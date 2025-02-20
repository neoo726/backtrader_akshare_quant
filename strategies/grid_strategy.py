from .base_strategy import BaseStrategy
import backtrader as bt
import numpy as np

class GridStrategy(BaseStrategy):
    """
    网格交易策略
    - 以20日均线为基准价格
    - 固定5层网格（买入和卖出）
    - 根据趋势动态调整网格间距：
      - 趋势向上：1%间距
      - 趋势向下：2.5%间距，同一价位不重复触发
    - 每层使用5%的资金
    """
    
    params = (
        ("grid_levels", 5),          # 固定网格层数（单向）
        ("up_grid_spacing", 0.01),   # 上涨趋势网格间距（1%）
        ("down_grid_spacing", 0.025), # 下跌趋势网格间距（2.5%）
        ("capital_per_grid", 0.05),   # 每个网格使用的资金比例（5%）
        ("maperiod", 20),            # 均线周期
    )

    def __init__(self):
        super().__init__()
        self.data_close = self.datas[0].close
        
        # 修改20日均线计算方式，使用精确计算
        self.sma = bt.indicators.MovingAverageSimple(
            self.data_close,
            period=self.params.maperiod,
            plotname='20日均线'
        )
        
        # 添加趋势判断指标（使用5日均线斜率）
        self.sma5 = bt.indicators.MovingAverageSimple(
            self.sma,  # 使用20日均线的5日均线
            period=5,
            plotname='5日均线'
        )
        
        # 初始化网格
        self.grid_orders = []
        self.base_price = None
        self.grids = []
        self.trend = None  # 用于存储当前趋势
        
        # 修改网格跟踪方式
        self.grid_positions = {}  # 记录每个网格的持仓 {grid_price: quantity}
        self.active_buy_grids = 0  # 当前持有的买入网格数
        self.triggered_grids = set()  # 记录下跌趋势中已触发的网格价格

    def next(self):
        super().next()
        
        # 添加调试信息
        print(f"\n当前日期: {self.data.datetime.date(0)}")
        print(f"收盘价: {self.data_close[0]:.3f}")
        print(f"20日均线: {self.sma[0]:.3f}")
        print(f"当前持仓: {self.position.size if self.position else 0}")
        print(f"当前持仓网格数: {self.active_buy_grids}")
        print(f"活跃网格: {self.grid_positions}")
        
        # 如果有待执行订单，跳过
        if self.order:
            return
            
        # 判断趋势
        current_trend = 'up' if self.sma5[0] > self.sma5[-1] else 'down'
        
        # 如果趋势改变或首次运行，重新设置网格
        if not self.base_price or current_trend != self.trend:
            self.trend = current_trend
            self.setup_grids()
        # 如果均线变化超过当前网格间距，也重新设置网格
        elif abs(self.sma[0] - self.base_price) / self.base_price > (
            self.p.up_grid_spacing if self.trend == 'up' else self.p.down_grid_spacing
        ):
            self.setup_grids()
        
        current_price = self.data_close[0]
        
        # 检查是否触发网格交易
        for grid in self.grids:
            grid_price = grid['price']
            grid_type = grid['type']
            grid_index = grid['index']
            
            # 计算每个网格的目标持仓量
            available_cash = self.broker.getcash()
            grid_cash = self.broker.getvalue() * self.p.capital_per_grid
            target_size = int(grid_cash / current_price)
            
            if grid_type == 'buy' and current_price <= grid_price:
                # 检查是否已达到最大网格数
                if self.active_buy_grids >= self.p.grid_levels:
                    print(f"已达到最大网格数 {self.active_buy_grids}，跳过买入")
                    continue
                    
                # 检查该价格网格是否已经持有
                grid_price_key = round(grid_price, 3)
                if grid_price_key in self.grid_positions:
                    print(f"价格 {grid_price_key} 已有持仓，跳过买入")
                    continue
                    
                # 在下跌趋势中检查是否已触发过该价格网格
                if self.trend == 'down' and grid_price_key in self.triggered_grids:
                    print(f"下跌趋势中价格 {grid_price_key} 已触发过，跳过买入")
                    continue
                
                # 买入网格
                if available_cash >= grid_cash:
                    print(f"触发买入网格 {grid_index}: 价格 {grid_price:.3f}")
                    self.order = self.buy(size=target_size)
                    
                    # 在下跌趋势中记录已触发的网格价格
                    if self.trend == 'down':
                        self.triggered_grids.add(grid_price_key)
                    
                    self.current_grid_info = {
                        'grid_levels': self.p.grid_levels,
                        'trend': self.trend,
                        'grid_type': 'buy',
                        'grid_index': grid_index,
                        'price_level': grid_price_key
                    }
                    
            elif grid_type == 'sell' and current_price >= grid_price:
                # 检查是否有足够的持仓可以卖出
                if not self.position or self.position.size < target_size:
                    print(f"持仓不足，跳过卖出")
                    continue
                    
                # 检查是否还有活跃的买入网格
                if self.active_buy_grids <= 0:
                    print(f"没有活跃的买入网格，跳过卖出")
                    continue
                    
                print(f"触发卖出网格 {grid_index}: 价格 {grid_price:.3f}")
                self.order = self.sell(size=target_size)
                self.current_grid_info = {
                    'grid_levels': self.p.grid_levels,
                    'trend': self.trend,
                    'grid_type': 'sell',
                    'grid_index': grid_index,
                    'price_level': grid_price
                }

    def setup_grids(self):
        """设置网格"""
        print("\n重新设置网格 - 清空所有持仓")
        # 如果有持仓，先全部卖出
        if self.position and self.position.size > 0:
            self.order = self.sell(size=self.position.size)
        
        self.base_price = self.sma[0]
        self.grids = []
        
        # 重置网格状态
        self.grid_positions = {}
        self.active_buy_grids = 0
        self.triggered_grids = set()
        
        # 根据趋势选择网格间距
        grid_spacing = self.p.up_grid_spacing if self.trend == 'up' else self.p.down_grid_spacing
        
        print(f"\n重新设置网格 - 基准价格: {self.base_price:.3f}")
        print(f"当前趋势: {'上涨' if self.trend == 'up' else '下跌'}")
        print(f"网格层数: {self.p.grid_levels}")
        print(f"网格间距: {grid_spacing:.1%}")
        
        # 设置买入网格（低于基准价）
        for i in range(1, self.p.grid_levels + 1):
            grid_price = self.base_price * (1 - i * grid_spacing)
            self.grids.append({
                'price': grid_price,
                'type': 'buy',
                'index': i
            })
            print(f"买入网格 {i}: {grid_price:.3f}")
            
        # 设置卖出网格（高于基准价）
        for i in range(1, self.p.grid_levels + 1):
            grid_price = self.base_price * (1 + i * grid_spacing)
            self.grids.append({
                'price': grid_price,
                'type': 'sell',
                'index': i
            })
            print(f"卖出网格 {i}: {grid_price:.3f}")

    def notify_order(self, order):
        """订单状态更新"""
        # 首先调用父类的方法处理基本的订单状态
        super().notify_order(order)
        
        # 然后添加网格特有的处理
        if order.status == order.Completed:
            price_level = round(self.current_grid_info['price_level'], 3)
            
            print(f"\n订单执行详情:")
            print(f"价格: {price_level}")
            print(f"订单类型: {'买入' if order.isbuy() else '卖出'}")
            print(f"订单数量: {order.executed.size}")
            print(f"执行前网格状态: {self.grid_positions}")
            print(f"执行前持仓网格数: {self.active_buy_grids}")
            
            if order.isbuy():
                # 买入时添加网格持仓
                if price_level not in self.grid_positions:
                    self.grid_positions[price_level] = 0
                    self.active_buy_grids += 1
                self.grid_positions[price_level] += order.executed.size
                
                print(f"买入后网格状态: {self.grid_positions}")
                print(f"买入后持仓网格数: {self.active_buy_grids}")
                
            else:  # 卖出
                # 从最高价格的网格开始卖出
                if self.grid_positions:
                    # 按价格从高到低排序网格
                    sorted_prices = sorted(self.grid_positions.keys(), reverse=True)
                    sell_price = sorted_prices[0]
                    
                    # 从该网格减少持仓
                    self.grid_positions[sell_price] -= order.executed.size
                    if self.grid_positions[sell_price] <= 0:
                        del self.grid_positions[sell_price]
                        self.active_buy_grids -= 1
                    
                    print(f"卖出后网格状态: {self.grid_positions}")
                    print(f"卖出后持仓网格数: {self.active_buy_grids}")
            
            self.observer.add_trade_signal(
                self.data.datetime.date(0),
                order.executed.price,
                is_buy=order.isbuy(),
                grid_info={
                    **self.current_grid_info,
                    'active_grids': self.active_buy_grids
                }
            ) 