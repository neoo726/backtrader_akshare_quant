import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pandas as pd

class PlotlyObserver:
    def __init__(self):
        # 基础数据
        self.dates = []
        self.close_prices = []
        self.sma_values = []
        
        # 策略收益相关
        self.portfolio_values = []
        self.returns = []
        self.benchmark_values = []  # 沪深300基准
        self.benchmark_returns = []
        self.initial_benchmark_value = None  # 存储基准的初始值
        self.drawdowns = []
        self.daily_pnl = []  # 每日盈亏
        
        # 交易统计
        self.trades = []
        self.winning_trades = []  # 盈利交易
        self.losing_trades = []   # 亏损交易
        
        # 添加 OHLC 数据存储
        self.open_prices = []
        self.high_prices = []
        self.low_prices = []
        
        # 添加交易信号存储
        self.buy_signals = {'dates': [], 'prices': []}
        self.sell_signals = {'dates': [], 'prices': []}
        
        # 添加仓位记录
        self.positions = []  # 记录每日仓位
        
    def update(self, strategy, benchmark_df):
        try:
            current_date = strategy.data.datetime.date(0)
             # 将当前日期转换为 pandas Timestamp 以确保格式匹配
            current_date_ts = pd.Timestamp(current_date)
        
            # 调试信息
            print(f"Updating for date: {current_date}")
            print(f"Benchmark index type: {type(benchmark_df.index[0])}")
            print(f"Current date type: {type(current_date_ts)}")
            
            # 更新基础数据
            self.dates.append(current_date)
            self.close_prices.append(strategy.data_close[0])
            self.sma_values.append(strategy.sma[0])
            
            # 更新组合价值和基准
            current_value = strategy.broker.getvalue()
            self.portfolio_values.append(current_value)
            
            # 更新基准数据
            benchmark_price = benchmark_df.loc[current_date_ts, 'close']
            if self.initial_benchmark_value is None:
                self.initial_benchmark_value = benchmark_price
            self.benchmark_values.append(benchmark_price)
            print(f"Added benchmark value: {benchmark_price}")
            # 计算每日收益
            if len(self.portfolio_values) > 1:
                # 策略收益
                daily_return = (current_value / self.portfolio_values[-2]) - 1
                self.returns.append(daily_return)
                self.daily_pnl.append(current_value - self.portfolio_values[-2])
                
                # 基准收益
                if len(self.benchmark_values) > 1 and self.benchmark_values[-1] is not None and self.benchmark_values[-2] is not None:
                    benchmark_return = (self.benchmark_values[-1] / self.benchmark_values[-2]) - 1
                    self.benchmark_returns.append(benchmark_return)
                else:
                    self.benchmark_returns.append(0)
            else:
                self.returns.append(0)
                self.daily_pnl.append(0)
                self.benchmark_returns.append(0)
                
            # 添加 OHLC 数据收集
            self.open_prices.append(strategy.data.open[0])
            self.high_prices.append(strategy.data.high[0])
            self.low_prices.append(strategy.data.low[0])
            
            # 记录仓位，直接使用持仓数量
            current_position = strategy.position.size if strategy.position else 0
            self.positions.append(current_position)
        except Exception as e:
            print(f"Error in update: {str(e)}")
            raise
    
    def calculate_metrics(self):
        """计算策略指标"""
        try:
            if not self.portfolio_values or not self.benchmark_values:
                return {
                    'total_return': 0,
                    'benchmark_return': 0,
                    'excess_return': 0,
                    'annual_return': 0,
                    'max_drawdown': 0,
                    'win_rate': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'profit_factor': 0,
                    'alpha': 0,
                    'beta': 0,
                    'sharpe_ratio': 0
                }
            
            # 计算收益相关指标
            total_return = (self.portfolio_values[-1] / self.portfolio_values[0]) - 1
            benchmark_total_return = (self.benchmark_values[-1] / self.benchmark_values[0] - 1) if self.benchmark_values and None not in (self.benchmark_values[0], self.benchmark_values[-1]) else 0
            excess_return = total_return - benchmark_total_return
            
            # 计算年化收益
            days = len(self.dates)
            annual_return = (1 + total_return) ** (365/days) - 1 if days > 0 else 0
            
            # 计算最大回撤
            max_drawdown = max((max(self.portfolio_values[:i+1]) - val) / max(self.portfolio_values[:i+1])
                              for i, val in enumerate(self.portfolio_values))
            
            # 计算交易统计
            winning_trades = len(self.winning_trades)
            losing_trades = len(self.losing_trades)
            total_trades = winning_trades + losing_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # 计算盈亏比
            avg_win = np.mean(self.winning_trades) if self.winning_trades else 0
            avg_loss = abs(np.mean(self.losing_trades)) if self.losing_trades else 0
            profit_factor = avg_win / avg_loss if avg_loss != 0 else float('inf')
            
            # 计算Alpha和Beta
            returns_array = np.array(self.returns)
            benchmark_array = np.array(self.benchmark_returns)
            
            # Beta计算
            beta = np.cov(returns_array, benchmark_array)[0,1] / np.var(benchmark_array) if len(returns_array) > 1 and np.var(benchmark_array) != 0 else 0
            
            # Alpha计算（简化版）
            risk_free_rate = 0.02 / 252  # 假设无风险利率2%
            alpha = np.mean(returns_array) - risk_free_rate - beta * np.mean(benchmark_array)
            alpha = alpha * 252  # 年化Alpha
            
            # 计算夏普比率
            returns_std = np.std(returns_array) * np.sqrt(252)  # 年化波动率
            sharpe_ratio = (annual_return - 0.02) / returns_std if returns_std != 0 else 0  # 假设无风险利率2%
            
            return {
                'total_return': total_return,
                'benchmark_return': benchmark_total_return,
                'excess_return': excess_return,
                'annual_return': annual_return,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'profit_factor': profit_factor,
                'alpha': alpha,
                'beta': beta,
                'sharpe_ratio': sharpe_ratio
            }
        except Exception as e:
            print(f"Error in calculate_metrics: {str(e)}")
            raise
    
    def plot(self):
        try:
            metrics = self.calculate_metrics()
            
            # 创建连续的交易日期序列
            df = pd.DataFrame({
                'date': self.dates,
                'open': self.open_prices,
                'high': self.high_prices,
                'low': self.low_prices,
                'close': self.close_prices,
                'daily_pnl': self.daily_pnl,
                'portfolio_value': self.portfolio_values
            })
            
            # 设置日期索引并按日期排序
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            # 创建四行子图，调整间距
            fig = make_subplots(
                rows=4, cols=1,  # 改为4行
                vertical_spacing=0.12,
                row_heights=[0.3, 0.3, 0.2, 0.2],  # 调整每个子图的高度比例
                specs=[[{"secondary_y": False}], 
                      [{"secondary_y": False}],
                      [{"secondary_y": False}],
                      [{"secondary_y": False}]]
            )
            
            # 计算累积收益
            cumulative_returns = [v/self.portfolio_values[0] - 1 for v in self.portfolio_values]
            
            # 计算基准累积收益
            valid_benchmark_values = [v for v in self.benchmark_values if v is not None]
            benchmark_cum_returns = [(v/valid_benchmark_values[0] - 1) for v in valid_benchmark_values] if valid_benchmark_values else []
            
            # 添加基准收益曲线（暗红色）
            if benchmark_cum_returns:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=benchmark_cum_returns,
                        mode='lines',
                        name='沪深300',
                        line=dict(color='darkred', width=1.5),
                        connectgaps=True,
                        showlegend=True,
                        legendgroup='strategy'
                    ),
                    row=1, col=1
                )
            
            # 添加策略收益曲线（蓝黑色）
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=cumulative_returns,
                    mode='lines',
                    name='策略收益',
                    line=dict(color='rgb(0, 0, 139)', width=2),
                    connectgaps=True,
                    showlegend=True,
                    legendgroup='strategy'
                ),
                row=1, col=1
            )
            
            # 添加K线图，移除legend
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    increasing_line_color='red',
                    decreasing_line_color='green',
                    showlegend=False,
                    xperiod='D1',  # 设置时间周期为1天
                    xperiodalignment='middle',  # 将对齐方式改为middle
                    hovertext=[f'开盘: {o:.2f}<br>最高: {h:.2f}<br>最低: {l:.2f}<br>收盘: {c:.2f}'
                              for o, h, l, c in zip(df['open'], df['high'], df['low'], df['close'])],
                    hoverlabel=dict(
                        bgcolor='white',
                        font_size=12,
                        font_family="Arial"
                    ),
                    hoverinfo='text+x',
                    legendgroup='kline'  # 添加legendgroup
                ),
                row=2, col=1
            )
            
            # 在添加K线图后，添加买卖点标记
            # 添加买入点（红色三角形，显示在K线上方）
            if self.buy_signals['dates']:
                fig.add_trace(
                    go.Scatter(
                        x=self.buy_signals['dates'],
                        y=[df.loc[date, 'high'] * 1.03 for date in self.buy_signals['dates']],
                        mode='markers',
                        name='买入',
                        marker=dict(
                            symbol='triangle-down',
                            size=12,
                            color='red',
                        ),
                        showlegend=False,
                    ),
                    row=2, col=1
                )

            # 添加卖出点（绿色三角形，显示在K线下方）
            if self.sell_signals['dates']:
                fig.add_trace(
                    go.Scatter(
                        x=self.sell_signals['dates'],
                        y=[df.loc[date, 'low'] * 0.97 for date in self.sell_signals['dates']],
                        mode='markers',
                        name='卖出',
                        marker=dict(
                            symbol='triangle-up',
                            size=12,
                            color='green',
                        ),
                        showlegend=False,
                    ),
                    row=2, col=1
                )
            
            # 收集所有交易记录并按日期排序
            all_trades = []
            
            # 添加买入记录
            for date, price in zip(self.buy_signals['dates'], self.buy_signals['prices']):
                all_trades.append({
                    'date': date,
                    'price': price,
                    'type': '买入',
                    'size': 100
                })
                
            # 添加卖出记录
            for date, price in zip(self.sell_signals['dates'], self.sell_signals['prices']):
                all_trades.append({
                    'date': date,
                    'price': price,
                    'type': '卖出',
                    'size': 100
                })
            
            # 按日期排序
            all_trades.sort(key=lambda x: x['date'])
            
            # 打印排序后的交易记录
            print("\n交易记录:")
            for trade in all_trades:
                print(f"日期：{trade['date']}，价格：{trade['price']:.3f}，数量：{trade['size']}，{trade['type']}")
            
            # 在添加仓位图表之前，计算合适的刻度
            max_position = max(self.positions) if self.positions else 0
            min_position = min(self.positions) if self.positions else 0
            position_ticks = self.get_nice_ticks(min_position, max_position)

            # 添加仓位面积图
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=self.positions,
                    fill='tozeroy',
                    name='持仓数量',
                    showlegend=False,
                    line=dict(color='rgba(0, 100, 180, 0.3)'),
                    fillcolor='rgba(0, 100, 180, 0.1)',
                    hovertemplate='持仓: %{y:~s}股<extra></extra>'  # 使用SI格式
                ),
                row=3, col=1
            )
            
            # 每日盈亏柱状图移到第4行
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['daily_pnl'],
                    name='每日盈亏',
                    marker_color=['red' if x > 0 else 'green' for x in df['daily_pnl']],
                    showlegend=False
                ),
                row=4, col=1
            )
            
            # 计算日期范围并选择显示格式
            date_range = (df.index[-1] - df.index[0]).days
            
            # 根据日期范围选择显示格式和间隔
            if date_range > 365 * 1.5:  # 如果超过1.5年，只显示年份
                date_format = '%Y'
                interval = 20  # 增加间隔
            else:  # 否则显示年月
                date_format = '%Y-%m'
                interval = 10  # 较小的间隔

            # 创建日期标签
            date_indices = list(range(0, len(df.index), interval))
            if len(df.index) - 1 not in date_indices:  # 确保包含最后一个日期
                date_indices.append(len(df.index) - 1)
            
            date_labels = []
            filtered_indices = []
            last_label = None
            
            for idx in date_indices:
                current_label = df.index[idx].strftime(date_format)
                if current_label != last_label:  # 只添加不重复的标签
                    date_labels.append(current_label)
                    filtered_indices.append(idx)
                    last_label = current_label

            # 更新布局
            fig.update_layout(
                height=1200,  # 增加总高度
                showlegend=True,
                hovermode='x unified',
                margin=dict(t=150),
                # 统一所有x轴的设置
                xaxis=dict(
                    type="category",
                    rangeslider_visible=False,  # 隐藏范围滑块
                    tickmode='array',
                    ticktext=date_labels,
                    tickvals=filtered_indices,
                    tickangle=45,
                    range=[-0.5, len(df.index) - 0.5],
                    fixedrange=True  # 禁止缩放
                ),
                xaxis2=dict(
                    type="category",
                    rangeslider=dict(visible=False),  # 隐藏范围滑块
                    tickmode='array',
                    ticktext=date_labels,
                    tickvals=filtered_indices,
                    tickangle=45,
                    range=[-0.5, len(df.index) - 0.5],
                    fixedrange=True  # 禁止缩放
                ),
                xaxis3=dict(
                    type="category",
                    rangeslider_visible=False,  # 隐藏范围滑块
                    tickmode='array',
                    ticktext=date_labels,
                    tickvals=filtered_indices,
                    tickangle=45,
                    range=[-0.5, len(df.index) - 0.5],
                    fixedrange=True  # 禁止缩放
                ),
                xaxis4=dict(
                    type="category",
                    rangeslider_visible=False,  # 隐藏范围滑块
                    tickmode='array',
                    ticktext=date_labels,
                    tickvals=filtered_indices,
                    tickangle=45,
                    range=[-0.5, len(df.index) - 0.5],
                    fixedrange=True  # 禁止缩放
                ),
                yaxis=dict(fixedrange=True),  # 禁止y轴缩放
                yaxis2=dict(fixedrange=True),  # 禁止y轴缩放
                yaxis3=dict(
                    fixedrange=True,  # 禁止y轴缩放
                    tickformat='~s',  # 使用SI格式 (k, M, G等)
                    tickmode='array',  # 使用自定义刻度
                    tickvals=position_ticks,  # 设置刻度值
                    ticktext=[f'{int(x):,}' for x in position_ticks],  # 格式化刻度标签
                    separatethousands=True,  # 添加千位分隔符
                    range=[min_position * 0.9, max_position * 1.1]  # 稍微扩大范围，使图表更美观
                ),
                yaxis4=dict(fixedrange=True),  # 禁止y轴缩放
                bargap=0.2,
                bargroupgap=0.1,
                # 禁用所有模式栏按钮
                modebar=dict(
                    remove=['zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 
                            'autoScale2d', 'resetScale2d', 'hoverClosestCartesian',
                            'hoverCompareCartesian', 'toggleSpikelines']
                ),
                # 修改图例设置，将第一个图例（策略收益相关）放在第一个子图的右上角
                legend=dict(
                    y=0.98,  # 调整到更靠近折线图顶部
                    x=0.98,
                    xanchor='right',
                    yanchor='top',
                    bgcolor='rgba(255, 255, 255, 0.8)',
                    bordercolor='rgba(0, 0, 0, 0.3)',
                    borderwidth=1,
                    font=dict(size=10)  # 可以适当减小字体大小
                ),
            )

            # 更新所有x轴的显示设置
            fig.update_xaxes(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgrey',
                showline=True,
                linewidth=1,
                linecolor='black',
                mirror=True,
                rangebreaks=[dict(bounds=["sat", "mon"])],  # 去除周末
                dtick="M1",  # 按月显示刻度
                range=[-0.5, len(df.index) - 0.5]  # 确保从最左侧开始显示
            )
            
            # 添加指标注释
            metrics_info = [
                ('策略收益', f"{metrics['total_return']:.2%}", 0.02, True),
                ('基准收益', f"{metrics['benchmark_return']:.2%}", 0.10, True),
                ('超额收益', f"{metrics['excess_return']:.2%}", 0.18, True),
                ('最大回撤', f"{metrics['max_drawdown']:.2%}", 0.26, False),
                ('胜率', f"{metrics['win_rate']:.2%}", 0.34, False),
                ('盈利次数', f"{metrics['winning_trades']}", 0.42, False),
                ('亏损次数', f"{metrics['losing_trades']}", 0.50, False),
                ('盈亏比', 'NA' if metrics['winning_trades'] == 0 and metrics['losing_trades'] > 0 else f"{metrics['profit_factor']:.2f}", 0.58, False),
                ('Alpha', f"{metrics['alpha']:.2f}", 0.66, True),
                ('Beta', f"{metrics['beta']:.2f}", 0.74, True),
                ('夏普比率', f"{metrics['sharpe_ratio']:.2f}", 0.82, False)
            ]
            
            annotations = []
            for title, value, x_pos, use_color in metrics_info:
                # 确定颜色逻辑
                if use_color:
                    if float(value.strip('%').strip('-')) == 0:
                        color = 'black'
                    else:
                        is_negative = '-' in str(value)
                        color = 'green' if is_negative else 'red'
                else:
                    color = 'black'
                
                # 修改指标值的位置和字体大小
                annotations.append(dict(
                    x=x_pos,
                    y=1.10,  # 将y位置从1.12改为1.10
                    xref="paper",
                    yref="paper",
                    text=value,
                    showarrow=False,
                    font=dict(size=16, color=color),  # 将字体大小从20改为16
                    align='center',
                ))
                # 修改指标标题的位置
                annotations.append(dict(
                    x=x_pos,
                    y=1.05,  # 将y位置从1.06改为1.05
                    xref="paper",
                    yref="paper",
                    text=title,
                    showarrow=False,
                    font=dict(size=12),
                    align='center',
                ))
            
            # 更新布局
            fig.update_layout(
                height=1200,  # 增加总高度
                showlegend=True,
                hovermode='x unified',
                margin=dict(t=150),
                annotations=annotations,
                yaxis_tickformat='.2%',
                yaxis2_tickformat='.0f',
                yaxis4_tickformat='.0f',
            )
            
            # 更新y轴标题
            fig.update_yaxes(title_text="累积收益率", row=1, col=1)
            fig.update_yaxes(title_text="K线", row=2, col=1)
            fig.update_yaxes(title_text="持仓数量(股)", row=3, col=1)
            fig.update_yaxes(title_text="每日盈亏", row=4, col=1)
            
            # 添加20日均线到K线图
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=self.sma_values,
                    mode='lines',
                    name='20日均线',
                    line=dict(
                        color='blue',
                        width=1,
                        dash='solid'
                    ),
                    showlegend=False,
                ),
                row=2, col=1
            )
            
            fig.show()
        except Exception as e:
            print(f"Error in plot: {str(e)}")
            raise 

    def add_trade_signal(self, date, price, is_buy):
        """添加交易信号
        
        Args:
            date: 交易日期
            price: 交易价格
            is_buy: 是否为买入信号
        """
        if is_buy:
            self.buy_signals['dates'].append(date)
            self.buy_signals['prices'].append(price)
        else:
            self.sell_signals['dates'].append(date)
            self.sell_signals['prices'].append(price)

        # 统一格式打印交易记录
        print(f"日期：{date}，价格：{price:.3f}，数量：100，{'买入' if is_buy else '卖出'}")

        # 计算交易盈亏
        if not is_buy and len(self.buy_signals['prices']) > 0:
            last_buy_price = self.buy_signals['prices'][-1]
            trade_profit = (price - last_buy_price) * 100  # 假设数量固定为100
            if trade_profit > 0:
                self.winning_trades.append(trade_profit)
            else:
                self.losing_trades.append(trade_profit) 

    def get_nice_ticks(self, min_val, max_val, n_ticks=4):
        """生成合适的刻度"""
        range_val = max_val - min_val
        if range_val == 0:
            return [min_val]
        
        # 计算合适的刻度间隔
        tick_size = range_val / (n_ticks - 1)
        # 将tick_size转换为"整数"，如1000, 2000, 5000等
        magnitude = 10 ** np.floor(np.log10(tick_size))
        possible_ticks = [1, 2, 5, 10]
        tick_size = magnitude * min([x for x in possible_ticks if x * magnitude >= tick_size])
        
        # 生成刻度值
        start = np.floor(min_val / tick_size) * tick_size
        ticks = np.arange(start, max_val + tick_size, tick_size)
        return ticks 