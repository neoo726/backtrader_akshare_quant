from strategies.base_strategy import BaseStrategy
import backtrader as bt
import numpy as np

class GridStrategy(BaseStrategy):
    """
    网格交易策略
    - 以20日均线为基准价格
    - 上下各5层网格
    - 每层间距为基准价格的1%
    - 每层使用5%的资金
    """
    
    params = (
        ("grid_levels", 5),      # 网格层数（单向）
        ("grid_spacing", 0.01),  # 网格间距（1%）
        ("capital_per_grid", 0.05),  # 每个网格使用的资金比例（5%）
        ("maperiod", 20),        # 均线周期
    )

    def __init__(self):
        super().__init__()
        self.data_close = self.datas[0].close
        
        # 添加20日均线作为基准价格
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod
        )
        
        # 初始化网格
        self.grid_orders = []  # 存储网格订单
        self.base_price = None  # 基准价格
        self.grids = []  # 存储网格价格水平

    def next(self):
        super().next()
        
        # 添加调试信息
        print(f"\n当前日期: {self.data.datetime.date(0)}")
        print(f"收盘价: {self.data_close[0]:.3f}")
        print(f"20日均线: {self.sma[0]:.3f}")
        print(f"当前持仓: {self.position.size if self.position else 0}")
        
        # 如果有待执行订单，跳过
        if self.order:
            return
            
        # 首次运行或需要重新设置网格时
        if not self.base_price or abs(self.sma[0] - self.base_price) / self.base_price > self.p.grid_spacing:
            self.setup_grids()
        
        current_price = self.data_close[0]
        
        # 检查是否触发网格交易
        for grid in self.grids:
            grid_price = grid['price']
            grid_type = grid['type']
            
            # 计算每个网格的目标持仓量
            available_cash = self.broker.getcash()
            grid_cash = self.broker.getvalue() * self.p.capital_per_grid
            target_size = int(grid_cash / current_price)
            
            if grid_type == 'buy' and current_price <= grid_price:
                # 买入网格
                if available_cash >= grid_cash:
                    print(f"触发买入网格: 价格 {grid_price:.3f}")
                    self.order = self.buy(size=target_size)
                    
            elif grid_type == 'sell' and current_price >= grid_price:
                # 卖出网格
                if self.position and self.position.size >= target_size:
                    print(f"触发卖出网格: 价格 {grid_price:.3f}")
                    self.order = self.sell(size=target_size)

    def setup_grids(self):
        """设置网格"""
        self.base_price = self.sma[0]
        self.grids = []
        
        print(f"\n重新设置网格 - 基准价格: {self.base_price:.3f}")
        
        # 设置买入网格（低于基准价）
        for i in range(1, self.p.grid_levels + 1):
            grid_price = self.base_price * (1 - i * self.p.grid_spacing)
            self.grids.append({
                'price': grid_price,
                'type': 'buy'
            })
            print(f"买入网格 {i}: {grid_price:.3f}")
            
        # 设置卖出网格（高于基准价）
        for i in range(1, self.p.grid_levels + 1):
            grid_price = self.base_price * (1 + i * self.p.grid_spacing)
            self.grids.append({
                'price': grid_price,
                'type': 'sell'
            })
            print(f"卖出网格 {i}: {grid_price:.3f}") 