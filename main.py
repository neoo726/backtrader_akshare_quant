from datetime import datetime
import backtrader as bt
import akshare as ak
import pandas as pd
from plotly_observer import PlotlyObserver
# import matplotlib.pyplot as plt  # 由于 Backtrader 的问题，此处要求 pip install matplotlib==3.2.2
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
#plt.rcParams["font.sans-serif"] = ["SimHei"]
#plt.rcParams["axes.unicode_minus"] = False
# 设置日期范围
start_date = datetime(2021, 2, 16)  # 回测开始时间
end_date = datetime(2025, 2, 16)  # 回测结束时间
# 利用 AKShare 获取股票的后复权数据，这里只获取前 7 列
stock_hfq_df = ak.fund_etf_hist_em(symbol="510300", adjust="hfq").iloc[:, :6]

# 删除 `股票代码` 列
# del stock_hfq_df['股票代码']
# 处理字段命名，以符合 Backtrader 的要求
stock_hfq_df.columns = [
    'date',
    'open',
    'close',
    'high',
    'low',
    'volume',
]
# 把 date 作为日期索引，以符合 Backtrader 的要求
stock_hfq_df.index = pd.to_datetime(stock_hfq_df['date'])
# 获取沪深300数据
benchmark_df = ak.fund_etf_hist_em(symbol="510300",  adjust="hfq").iloc[:, :6]
#del benchmark_df['股票代码']
benchmark_df.columns = [
    'date',
    'open',
    'close',
    'high',
    'low',
    'volume',
]
# 把 date 作为日期索引，以符合 Backtrader 的要求
benchmark_df.index = pd.to_datetime(benchmark_df['date'])

# 截取日期范围
stock_hfq_df = stock_hfq_df.loc[start_date:end_date]
benchmark_df = benchmark_df.loc[start_date:end_date]
print('stock_hfq_df',stock_hfq_df)
print('benchmark_df',benchmark_df)

# Create and update the Plotly observer
observer = PlotlyObserver()

class MyStrategy(bt.Strategy):
    """
    主策略程序
    """
    params = (("maperiod", 20),)  # 全局设定交易策略的参数

    def __init__(self):
        """
        初始化函数
        """
        self.data_close = self.datas[0].close  # 指定价格序列
        # 初始化交易指令、买卖价格和手续费
        self.order = None
        self.buy_price = None
        self.buy_comm = None
        # 添加移动均线指标
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod
        )
        # 添加观察者引用
        self.observer = observer

    def next(self):
        """
        执行逻辑
        """
        # 在每个交易日更新观察者数据
        self.observer.update(self, benchmark_df)
        if self.order:  # 检查是否有指令等待执行,
            return
        # 检查是否持仓
        if not self.position:  # 没有持仓
            if self.data_close[0] > self.sma[0]:  # 执行买入条件判断：收盘价格上涨突破20日均线
                self.order = self.buy(size=100)  # 执行买入
        else:
            if self.data_close[0] < self.sma[0]:  # 执行卖出条件判断：收盘价格跌破20日均线
                self.order = self.sell(size=100)  # 执行卖出


cerebro = bt.Cerebro()  # 初始化回测系统

# 准备数据
data = bt.feeds.PandasData(
    dataname=stock_hfq_df,
    datetime=None,  # 使用索引作为日期
    fromdate=start_date,
    todate=end_date
)

# 添加数据和策略
cerebro.adddata(data)
cerebro.addstrategy(MyStrategy)

# 设置初始资金和手续费
start_cash = 15000
cerebro.broker.setcash(start_cash)
cerebro.broker.setcommission(commission=0.00005)  # 设置交易手续费为 0.5‰

# 运行回测
cerebro.run()

# 输出结果
port_value = cerebro.broker.getvalue()
pnl = port_value - start_cash

# 绘制结果
observer.plot()

print(f"初始资金: {start_cash:,.2f}")
print(f"回测期间：{start_date.strftime('%Y%m%d')}:{end_date.strftime('%Y%m%d')}")
print(f"总资金: {port_value:,.2f}")
print(f"净收益: {pnl:,.2f}")

#cerebro.plot(style='candlestick')  # 画图