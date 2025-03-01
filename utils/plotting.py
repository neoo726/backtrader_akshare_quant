"""
绘图工具模块
用于绘制回测结果图表和其他可视化功能
"""
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties
import pandas as pd
from loguru import logger

def setup_chinese_fonts():
    """设置中文字体，确保图表中的中文正确显示"""
    # 查找系统中的中文字体
    chinese_fonts = []
    
    # Windows常见中文字体
    windows_fonts = [
        'C:\\Windows\\Fonts\\simhei.ttf',  # 黑体
        'C:\\Windows\\Fonts\\simsun.ttc',  # 宋体
        'C:\\Windows\\Fonts\\msyh.ttc',    # 微软雅黑
        'C:\\Windows\\Fonts\\simkai.ttf',  # 楷体
    ]
    
    # 检查字体文件是否存在
    for font_path in windows_fonts:
        if os.path.exists(font_path):
            chinese_fonts.append(font_path)
            logger.info(f"找到中文字体: {font_path}")
    
    if chinese_fonts:
        # 使用找到的第一个中文字体
        font_path = chinese_fonts[0]
        # 添加字体
        font_prop = fm.FontProperties(fname=font_path)
        # 设置matplotlib默认字体
        plt.rcParams['font.family'] = font_prop.get_name()
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        logger.info(f"已设置中文字体: {font_path}")
        return font_prop
    else:
        logger.warning("未找到中文字体，图表中的中文可能无法正确显示")
        return None

def plot_returns(strategy_returns, benchmark_returns=None, font_properties=None, statistics=None):
    """
    绘制策略收益率曲线
    
    参数:
    -----------
    strategy_returns : pd.Series
        策略收益率序列
    benchmark_returns : pd.Series, optional
        基准收益率序列
    font_properties : FontProperties, optional
        字体属性
    statistics : dict, optional
        策略统计数据
    """
    plt.figure(figsize=(12, 8))
    
    # 绘制策略收益率曲线（蓝色面积图）
    plt.fill_between(strategy_returns.index, 0, strategy_returns.values, 
                    color='blue', alpha=0.3, label='_nolegend_')
    plt.plot(strategy_returns.index, strategy_returns.values, 'b-', 
             label='策略', linewidth=2)
    
    # 如果有基准收益率，也绘制基准曲线（暗红色）
    if benchmark_returns is not None:
        plt.plot(benchmark_returns.index, benchmark_returns.values, 
                color='darkred', linestyle='-', label='基准', linewidth=2)
    
    # 添加标题和标签
    plt.title('累计收益率', fontproperties=font_properties)
    plt.xlabel('日期', fontproperties=font_properties)
    plt.ylabel('收益率 (%)', fontproperties=font_properties)
    plt.grid(True)
    plt.legend(prop=font_properties)
    
    # 如果有统计数据，添加到图表中
    if statistics:
        stats_text = f"总收益率: {statistics['returns']:.2f}%\n"
        stats_text += f"年化收益率: {statistics['annual_return']:.2f}%\n"
        stats_text += f"最大回撤: {statistics['max_drawdown']:.2f}%\n"
        stats_text += f"夏普系数: {statistics['sharpe_ratio']:.2f}\n"
        stats_text += f"交易次数: {statistics['total_trades']}\n"
        stats_text += f"胜率: {statistics['win_rate']:.2f}%"
        
        # 在图表右上角添加统计数据
        plt.text(0.98, 0.98, stats_text,
                transform=plt.gca().transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(facecolor='white', alpha=0.8),
                fontproperties=font_properties)
    
    # 保存图表
    plt.savefig('回测结果.png')
    plt.close()

def plot_drawdown(drawdown, font_properties=None):
    plt.figure(figsize=(12, 6))
    plt.plot(drawdown.index, drawdown.values)
    plt.grid(True)
    plt.title('回撤走势图', fontproperties=font_properties)
    plt.xlabel('日期', fontproperties=font_properties)
    plt.ylabel('回撤', fontproperties=font_properties)
    plt.tight_layout()
    plt.savefig('回撤.png')
    plt.close()

def plot_monthly_returns(returns, font_properties=None):
    monthly_returns = returns.resample('M').sum()
    plt.figure(figsize=(12, 6))
    monthly_returns.plot(kind='bar')
    plt.grid(True)
    plt.title('月度收益', fontproperties=font_properties)
    plt.xlabel('月份', fontproperties=font_properties)
    plt.ylabel('收益率', fontproperties=font_properties)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('月度收益.png')
    plt.close()

def plot_position_changes(position_data, font_properties=None):
    plt.figure(figsize=(12, 6))
    for symbol in position_data.columns:
        plt.plot(position_data.index, position_data[symbol], label=symbol)
    plt.grid(True)
    plt.legend(prop=font_properties)
    plt.title('持仓变化', fontproperties=font_properties)
    plt.xlabel('日期', fontproperties=font_properties)
    plt.ylabel('持仓量', fontproperties=font_properties)
    plt.tight_layout()
    plt.savefig('持仓变化.png')
    plt.close() 