import backtrader as bt

class BaseStrategy(bt.Strategy):
    """基础策略类，处理通用配置和功能"""
    
    params = (
        ("observer", None),      # 观察者
        ("benchmark_df", None),  # 基准数据
    )

    def __init__(self):
        """初始化基础功能"""
        self.order = None  # 当前待执行订单
        self.observer = self.params.observer
        self.benchmark_df = self.params.benchmark_df

    def notify_order(self, order):
        """通用订单状态处理"""
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
            else:
                print(f'卖出执行价格: {order.executed.price:.2f}, 数量: {order.executed.size}')
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('订单取消/保证金不足/被拒绝')
        
        # 重置订单
        self.order = None

    def next(self):
        """每个交易日更新观察者数据"""
        self.observer.update(self, self.benchmark_df) 