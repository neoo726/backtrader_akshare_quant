from datetime import datetime
import backtrader as bt
import akshare as ak
import pandas as pd
from plotly_observer import PlotlyObserver
# import matplotlib.pyplot as plt  # 由于 Backtrader 的问题，此处要求 pip install matplotlib==3.2.2
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# 从strategies包导入策略
from strategies import MACrossStrategy
from config import BACKTEST_CONFIG, DATA_CONFIG

#plt.rcParams["font.sans-serif"] = ["SimHei"]
#plt.rcParams["axes.unicode_minus"] = False
# 设置日期范围
start_date = datetime(2024, 6, 16)  # 回测开始时间
end_date = datetime(2025, 2, 16)  # 回测结束时间
# 利用 AKShare 获取股票的后复权数据，这里只获取前 7 列
stock_hfq_df = ak.fund_etf_hist_em(
    symbol=DATA_CONFIG['stock_code'], 
    adjust="hfq"
).iloc[:, :6]

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

# 在数据准备部分添加
print("\n数据检查:")
print(f"数据起始日期: {stock_hfq_df.index[0]}")
print(f"数据结束日期: {stock_hfq_df.index[-1]}")
print(f"数据天数: {len(stock_hfq_df)}")
print("\n前20天数据:")
print(stock_hfq_df.head(20))

# Create and update the Plotly observer
observer = PlotlyObserver()

# 准备数据
data = bt.feeds.PandasData(
    dataname=stock_hfq_df,
    datetime=None,
    fromdate=BACKTEST_CONFIG['start_date'],
    todate=BACKTEST_CONFIG['end_date']
)

# 初始化回测系统
cerebro = bt.Cerebro()

# 添加数据
cerebro.adddata(data)

# 设置初始资金和手续费
cerebro.broker.setcash(BACKTEST_CONFIG['initial_cash'])
cerebro.broker.setcommission(commission=BACKTEST_CONFIG['commission_rate'])

# 添加策略，同时传入观察者和基准数据
cerebro.addstrategy(
    MACrossStrategy,
    observer=observer,
    benchmark_df=benchmark_df
)

# 运行回测
cerebro.run()

# 输出结果
port_value = cerebro.broker.getvalue()
pnl = port_value - BACKTEST_CONFIG['initial_cash']

# 绘制结果
observer.plot()

print(f"初始资金: {BACKTEST_CONFIG['initial_cash']:,.2f}")
print(f"回测期间：{BACKTEST_CONFIG['start_date'].strftime('%Y%m%d')}:{BACKTEST_CONFIG['end_date'].strftime('%Y%m%d')}")
print(f"总资金: {port_value:,.2f}")
print(f"净收益: {pnl:,.2f}")

#cerebro.plot(style='candlestick')  # 画图