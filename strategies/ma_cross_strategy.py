from .base_strategy import BaseStrategy
import backtrader as bt

class MACrossStrategy(BaseStrategy):
    """
    均线交叉策略
    """
    params = (
        ("maperiod", 20),
    )

    def __init__(self):
        """初始化策略"""
        super().__init__()  # 调用父类初始化
        self.data_close = self.datas[0].close  # 指定价格序列
        # 初始化交易指令、买卖价格和手续费
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        # 添加移动均线指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod
        )

    def next(self):
        """策略逻辑"""
        # 首先调用父类的next方法更新观察者数据
        super().next()
        
        # 添加调试信息
        print(f"\n当前日期: {self.data.datetime.date(0)}")
        print(f"收盘价: {self.data_close[0]:.2f}")
        print(f"20日均线: {self.sma[0]:.2f}")
        print(f"当前持仓: {self.position.size if self.position else 0}")
        
        if self.order:  # 检查是否有指令等待执行
            print("有待执行订单，跳过本次交易")
            return
        
        # 交易逻辑
        if not self.position:  # 没有持仓
            if self.data_close[0] > self.sma[0]:  # 执行买入条件判断
                print(f"买入信号：收盘价 {self.data_close[0]:.2f} > 均线 {self.sma[0]:.2f}")
                self.order = self.buy(size=100)
        else:
            if self.data_close[0] < self.sma[0]:  # 执行卖出条件判断
                print(f"卖出信号：收盘价 {self.data_close[0]:.2f} < 均线 {self.sma[0]:.2f}")
                self.order = self.sell(size=100)

    def notify_order(self, order):
        """订单状态更新"""
        # 打印订单的详细状态
        print(f"\n订单状态详情:")
        print(f"订单状态代码: {order.status}")
        print(f"订单状态名称: {order.Status[order.status]}")
        print(f"订单类型: {'买入' if order.isbuy() else '卖出'}")
        print(f"订单数量: {order.size}")
        print(f"订单价格: {order.price}")
        
        # 根据不同状态处理订单
        if order.status in [order.Submitted, order.Accepted]:
            print('订单已提交/已接受')
            return

        if order.status == order.Completed:
            print('订单已完成')
            if order.isbuy():
                print(f'买入执行价格: {order.executed.price:.2f}, 数量: {order.executed.size}')
                self.observer.add_trade_signal(
                    self.data.datetime.date(0),
                    order.executed.price,
                    is_buy=True
                )
            else:
                print(f'卖出执行价格: {order.executed.price:.2f}, 数量: {order.executed.size}')
                self.observer.add_trade_signal(
                    self.data.datetime.date(0),
                    order.executed.price,
                    is_buy=False
                )
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('订单取消/保证金不足/被拒绝')
        
        # 重置订单
        self.order = None

    def set_observer(self, observer, benchmark_df):
        """设置观察者和基准数据"""
        self.observer = observer
        self.benchmark_df = benchmark_df 