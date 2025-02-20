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
        
    def update(self, strategy, benchmark_df):
        try:
            current_date = strategy.data.datetime.date(0)
            
            # 更新基础数据
            self.dates.append(current_date)
            self.close_prices.append(strategy.data_close[0])
            self.sma_values.append(strategy.sma[0])
            
            # 更新组合价值和基准
            current_value = strategy.broker.getvalue()
            self.portfolio_values.append(current_value)
            
            # 更新基准数据
            if current_date in benchmark_df.index:
                benchmark_price = benchmark_df.loc[current_date, 'close']
                if self.initial_benchmark_value is None:
                    self.initial_benchmark_value = benchmark_price
                self.benchmark_values.append(benchmark_price)
            else:
                # 如果当前日期不在基准数据中，使用最近的有效值
                if len(self.benchmark_values) > 0:
                    self.benchmark_values.append(self.benchmark_values[-1])
                else:
                    self.benchmark_values.append(None)
            
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
                
            # 更新交易统计
            if strategy.order and strategy.order.status == strategy.order.Completed:
                trade_profit = strategy.order.executed.pnl
                if trade_profit > 0:
                    self.winning_trades.append(trade_profit)
                else:
                    self.losing_trades.append(trade_profit)
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
                    'beta': 0
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
                'beta': beta
            }
        except Exception as e:
            print(f"Error in calculate_metrics: {str(e)}")
            raise
    
    def plot(self):
        try:
            metrics = self.calculate_metrics()
            
            # 创建子图
            fig = make_subplots(rows=2, cols=1, 
                            vertical_spacing=0.12,
                            row_heights=[0.7, 0.3])
            
            # 计算累积收益
            cumulative_returns = [v/self.portfolio_values[0] - 1 for v in self.portfolio_values] if self.portfolio_values else []
            
            # 计算基准累积收益
            valid_benchmark_values = [v for v in self.benchmark_values if v is not None]
            benchmark_cum_returns = [(v/valid_benchmark_values[0] - 1) for v in valid_benchmark_values] if valid_benchmark_values else []
            
            # 添加基准收益曲线（暗红色）
            if benchmark_cum_returns:
                fig.add_trace(
                    go.Scatter(x=self.dates[:len(benchmark_cum_returns)], y=benchmark_cum_returns,
                            mode='lines', name='沪深300',
                            line=dict(color='darkred', width=1.5),
                            legendgroup='group1',
                            legendgrouptitle_text="收益曲线"),
                    row=1, col=1
                )
            
            # 添加策略收益曲线（蓝黑色）
            if cumulative_returns:
                fig.add_trace(
                    go.Scatter(x=self.dates, y=cumulative_returns,
                            mode='lines', name='策略收益',
                            line=dict(color='rgb(0, 0, 139)', width=2),
                            legendgroup='group1'),
                    row=1, col=1
                )
            
            # 添加每日盈亏柱状图（红色表示盈利，绿色表示亏损）
            if self.daily_pnl:
                fig.add_trace(
                    go.Bar(x=self.dates, y=self.daily_pnl,
                        name='每日盈亏',
                        marker_color=['red' if x > 0 else 'green' for x in self.daily_pnl],
                        legendgroup='group2',
                        legendgrouptitle_text="盈亏分布"),
                    row=2, col=1
                )
            
            # 定义指标及其位置
            metrics_info = [
                ('策略收益', f"{metrics['total_return']:.2%}", 0.08, True),
                ('基准收益', f"{metrics['benchmark_return']:.2%}", 0.18, True),
                ('超额收益', f"{metrics['excess_return']:.2%}", 0.28, True),
                ('最大回撤', f"{metrics['max_drawdown']:.2%}", 0.38, False),
                ('胜率', f"{metrics['win_rate']:.2%}", 0.48, False),
                ('盈利次数', f"{metrics['winning_trades']}", 0.58, False),
                ('亏损次数', f"{metrics['losing_trades']}", 0.68, False),
                ('盈亏比', f"{metrics['profit_factor']:.2f}", 0.78, False),
                ('Alpha', f"{metrics['alpha']:.4f}", 0.88, True),
                ('Beta', f"{metrics['beta']:.4f}", 0.98, True)
            ]
            
            # 添加指标注释
            annotations = []
            for title, value, x_pos, use_color in metrics_info:
                if use_color:
                    is_negative = '-' in str(value)
                    color = 'green' if is_negative else 'red'
                else:
                    color = 'black'
                
                annotations.append(dict(
                    x=x_pos,
                    y=1.12,
                    xref="paper",
                    yref="paper",
                    text=value,
                    showarrow=False,
                    font=dict(size=20, color=color),
                    align='center',
                ))
                annotations.append(dict(
                    x=x_pos,
                    y=1.06,
                    xref="paper",
                    yref="paper",
                    text=title,
                    showarrow=False,
                    font=dict(size=12),
                    align='center',
                ))
            
            # 更新布局
            fig.update_layout(
                height=800,
                showlegend=True,
                hovermode='x unified',
                margin=dict(t=150),
                annotations=annotations,
                yaxis_tickformat='.2%',
                yaxis2_tickformat='.0f',
                legend=dict(
                    groupclick="toggleitem",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            fig.show()
        except Exception as e:
            print(f"Error in plot: {str(e)}")
            raise 