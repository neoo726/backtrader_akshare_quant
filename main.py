#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CyberTrader - 自动化交易系统

主入口文件，用于启动不同的功能模块：
1. 回测模式：运行历史数据回测
2. 实盘交易模式：连接券商API进行实盘交易
3. 股票代码检查：检查股票代码的有效性和基本信息

使用方法:
    python main.py --mode backtest --strategy etf_rotation --start_date 2020-01-01 --end_date 2023-12-31
    python main.py --mode trade --strategy etf_rotation
    python main.py --mode check --code 000001
"""

import os
import sys
import argparse
import importlib
import inspect
import datetime
import backtrader as bt
import akshare as ak
import pandas as pd
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, MonthLocator, DateFormatter, WeekdayLocator
from config.config import DEFAULT_BACKTEST_START, DEFAULT_BACKTEST_END

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入工具和策略
from utils.logger import setup_logger
from utils.data_fetcher import DataFetcher

# 导入策略模块
try:
    from strategies.ma_strategy import MAStrategy
except ImportError:
    MAStrategy = None

try:
    from strategies.sma_strategy import SMAStrategy
except ImportError:
    SMAStrategy = None

try:
    from strategies.etf_rotation_strategy_v2 import ETFRotationStrategy2
except ImportError:
    logger.error("无法导入ETFRotationStrategy2，请确保文件存在")
    ETFRotationStrategy2 = None

# 策略映射字典
STRATEGY_MAP = {}
if MAStrategy:
    STRATEGY_MAP['ma'] = MAStrategy
if SMAStrategy:
    STRATEGY_MAP['sma'] = SMAStrategy
if ETFRotationStrategy2:
    STRATEGY_MAP['etf_rotation2'] = ETFRotationStrategy2

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='量化交易回测系统')
    
    # 运行模式
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--backtest', action='store_true', help='运行回测模式')
    mode_group.add_argument('--realtime', action='store_true', help='运行实盘模式')
    mode_group.add_argument('--check', action='store_true', help='运行代码检查模式')
    
    # 检查模式参数
    parser.add_argument('--code', type=str, help='要检查的股票/ETF代码')
    
    # 策略选择
    available_strategies = list(STRATEGY_MAP.keys())
    default_strategy = 'etf_rotation2' if 'etf_rotation2' in STRATEGY_MAP else (available_strategies[0] if available_strategies else None)
    
    parser.add_argument('--strategy', '-s', type=str, default=default_strategy,
                        help='要运行的策略名称，可选值: ' + ', '.join(available_strategies) if available_strategies else '无可用策略')
    
    # 回测参数
    parser.add_argument('--cash', type=float, default=100000.0,
                        help='初始资金')
    parser.add_argument('--commission', type=float, default=0.0003,
                        help='佣金率')
    parser.add_argument('--start', type=str, default=DEFAULT_BACKTEST_START,
                        help=f'回测开始日期 (YYYYMMDD)，默认: {DEFAULT_BACKTEST_START}')
    parser.add_argument('--end', type=str, default=DEFAULT_BACKTEST_END,
                        help=f'回测结束日期 (YYYYMMDD)，默认: {DEFAULT_BACKTEST_END}')
    
    # 策略参数 - ETF轮动
    parser.add_argument('--short-period', type=int, default=20,
                        help='短期动量周期')
    parser.add_argument('--long-period', type=int, default=60,
                        help='长期动量周期')
    parser.add_argument('--top-n', type=int, default=3,
                        help='持有ETF数量')
    parser.add_argument('--rebalance-days', type=int, default=5,
                        help='再平衡天数')
    parser.add_argument('--volume-weight', type=float, default=0.3,
                        help='成交量权重 (仅用于ETF轮动2.0)')
    
    args = parser.parse_args()
    
    # 如果没有指定模式，默认为回测模式
    if not (args.backtest or args.realtime or args.check):
        args.backtest = True
        
    return args

def get_stock_data(stock_code, start_date, end_date):
    """获取股票/ETF数据"""
    try:
        # 使用ETF专用接口获取数据
        df = ak.fund_etf_hist_em(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if df is None or df.empty:
            logger.error(f"{stock_code} 未获取到数据")
            return None
            
        logger.info(f"{stock_code} 原始数据样本:\n{df.head()}")
        logger.info(f"数据列: {df.columns.tolist()}")
        
        # 重命名列以匹配backtrader要求
        df = df.rename(columns={
            '日期': 'datetime',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'price_change',
            '换手率': 'turnover'
        })
        
        # 确保日期格式正确
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # 确保数据类型正确
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if df[col].isnull().any():
                logger.warning(f"{stock_code} {col}列存在空值")
        
        # 检查是否有必要的列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                logger.error(f"{stock_code} 缺少必要的列: {col}")
                return None
        
        # 按日期排序
        df.sort_index(inplace=True)
        
        logger.info(f"{stock_code} 处理后数据样本:\n{df.head()}")
        logger.info(f"数据范围: {df.index.min()} 至 {df.index.max()}")
        logger.info(f"数据行数: {len(df)}")
        
        return df
        
    except Exception as e:
        logger.error(f"获取{stock_code}数据失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return None

def run_backtest(args):
    """运行回测"""
    logger.info(f"开始回测 策略: {args.strategy}")
    
    # 检查策略是否存在
    if not STRATEGY_MAP:
        logger.error("没有可用的策略")
        return
        
    if args.strategy not in STRATEGY_MAP:
        logger.error(f"未知策略: {args.strategy}，可用策略: {', '.join(STRATEGY_MAP.keys())}")
        return
    
    # 创建Cerebro引擎
    cerebro = bt.Cerebro()
    
    # 设置初始资金
    cerebro.broker.setcash(args.cash)
    
    # 设置佣金
    cerebro.broker.setcommission(commission=args.commission)
    
    # 获取策略类
    strategy_class = STRATEGY_MAP[args.strategy]
    
    # 准备策略参数
    strategy_params = {
        'start_date': pd.to_datetime(args.start).date(),
        'end_date': pd.to_datetime(args.end).date()
    }
    
    # 添加策略
    cerebro.addstrategy(strategy_class, **strategy_params)
    
    # 确定要加载的股票列表
    stock_list = []
    
    if args.strategy == 'etf_rotation2':
        try:
            from strategies.etf_rotation_strategy_v2 import ETF_POOL
            stock_list = ETF_POOL
            logger.info(f"使用ETF轮动池，共{len(stock_list)}个ETF")
        except (ImportError, AttributeError) as e:
            logger.error(f"无法导入ETF_POOL: {e}")
            stock_list = ['510300']  # 默认使用沪深300ETF
    else:
        # 默认股票列表
        stock_list = ['510300']
    
    # 加载数据
    start_date = args.start
    end_date = args.end
    
    data_loaded = False
    for stock_code in stock_list:
        df = get_stock_data(stock_code, start_date, end_date)
        if df is not None and not df.empty:
            # 修改PandasData的配置
            data = bt.feeds.PandasData(
                dataname=df,
                datetime=None,  # 使用索引作为日期
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=None  # 不使用持仓量
            )
            cerebro.adddata(data, name=stock_code)
            logger.info(f"已加载{stock_code}数据")
            data_loaded = True
    
    if not data_loaded:
        logger.error("没有成功加载任何数据，无法进行回测")
        return
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # 运行回测
    results = cerebro.run()
    
    # 创建输出目录
    output_dir = 'backtest_output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    if not results:
        logger.error("回测未返回任何结果")
        return
        
    # 获取回测结果
    strat = results[0]
    
    # 获取回测指标
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    drawdown = strat.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
    returns = strat.analyzers.returns.get_analysis().get('rnorm100', 0)
    
    # 保存回测指标到文件
    result_file = os.path.join(output_dir, 'backtest_metrics.txt')
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(f"策略: {args.strategy}\n")
        f.write(f"回测期间: {start_date} 至 {end_date}\n")
        f.write(f"初始资金: {args.cash}\n")
        f.write(f"夏普比率: {sharpe:.3f}\n")
        f.write(f"最大回撤: {drawdown:.2f}%\n")
        f.write(f"年化收益率: {returns:.2f}%\n")
    
    # 绘制结果
    try:
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 改用更全的字体
        plt.rcParams['axes.unicode_minus'] = False
        
        # 在绘图代码前添加这些设置
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.linestyle'] = '--'
        plt.rcParams['grid.alpha'] = 0.3  # 降低网格线透明度
        plt.rcParams['lines.linewidth'] = 1.5  # 适当减小线宽
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
        
        # 获取策略净值数据
        try:
            # 初始化基准数据变量
            benchmark_df = pd.DataFrame()
            close_col = 'close'
            
            # 确保策略有净值历史记录
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            if not hasattr(strat, '_value_history') or not strat._value_history:
                # 使用回测时间段创建默认数据
                returns_series = pd.Series(
                    [0, (portfolio_value / args.cash - 1) * 100],
                    index=[start_dt, end_dt]
                )
            else:
                # 严格限制在回测时间段内
                valid_history = [
                    (date, value) for date, value in strat._value_history 
                    if start_dt <= pd.to_datetime(date) <= end_dt
                ]
                
                dates = [date for date, _ in valid_history]
                values = [value for _, value in valid_history]
                portfolio_value = pd.Series(values, index=dates)
                returns_series = (portfolio_value / args.cash - 1) * 100

            # 处理基准数据的时间对齐
            try:
                # 使用更稳定的指数数据接口
                benchmark_df = ak.index_zh_a_hist(symbol="000300", period="daily")
                
                # 加强列名处理
                date_col = '日期' if '日期' in benchmark_df.columns else 'date'
                close_col = '收盘' if '收盘' in benchmark_df.columns else 'close'
                
                benchmark_df[date_col] = pd.to_datetime(benchmark_df[date_col])
                benchmark_df.set_index(date_col, inplace=True)
                benchmark_df = benchmark_df.sort_index()
                
                # 截取回测时间段
                benchmark_df = benchmark_df.loc[start_dt:end_dt]
                
                if not benchmark_df.empty:
                    benchmark_start = benchmark_df[close_col].iloc[0]
                    benchmark_returns = (benchmark_df[close_col] / benchmark_start - 1) * 100
                    # 重新索引以匹配策略时间范围
                    benchmark_returns = benchmark_returns.reindex(returns_series.index, method='ffill')
                    ax.plot(benchmark_returns.index, benchmark_returns.values, 
                           label='沪深300', color='blue', linewidth=1.5, alpha=0.7, zorder=2)
                    
            except Exception as e:
                logger.warning(f"基准数据获取失败: {str(e)}")

            # 绘制策略收益曲线
            ax.plot(returns_series.index, returns_series.values, 
                   label='策略收益', color='red', linewidth=2, zorder=3)

            # 图表格式化
            ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5, zorder=1)
            ax.set_title(f'{args.strategy} 策略回测结果', fontsize=16, pad=20)
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('收益率 (%)', fontsize=12)
            ax.grid(True, linestyle=':', alpha=0.7)
            ax.legend(loc='upper left', fontsize=10)
            
            # 智能日期刻度
            date_range = returns_series.index[-1] - returns_series.index[0]
            if date_range.days > 365*2:
                locator = YearLocator()
            elif date_range.days > 60:
                locator = MonthLocator(interval=3)
            else:
                locator = WeekdayLocator()
                
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45, ha='right')

            # 添加统计信息
            stats_text = f'''回测统计:
            期间: {start_date} 至 {end_date}
            初始资金: ￥{args.cash:,.0f}
            年化收益: {returns:.2f}%
            最大回撤: {drawdown:.2f}%
            夏普比率: {sharpe:.2f}'''
            
            ax.text(0.98, 0.02, stats_text,
                   transform=ax.transAxes,
                   verticalalignment='bottom',
                   horizontalalignment='right',
                   bbox=dict(facecolor='white', alpha=0.8),
                   fontsize=9)

            # 确保索引是datetime类型
            returns_series.index = pd.to_datetime(returns_series.index)
            
            # 转换为matplotlib可识别的日期格式
            mpl_start = matplotlib.dates.date2num(returns_series.index.min())
            mpl_end = matplotlib.dates.date2num(returns_series.index.max())
            ax.set_xlim(mpl_start, mpl_end)
            
            # 保存图表
            plt.tight_layout()
            output_file = os.path.join(output_dir, 'strategy_performance.png')
            plt.savefig(output_file, 
                       dpi=100,
                       bbox_inches='tight',
                       pil_kwargs={'optimize': True, 'compress_level': 6})
            plt.close()
            
            logger.success(f"图表已保存: {output_file} (尺寸: {os.path.getsize(output_file)/1024:.1f}KB)")

        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            raise

    except Exception as e:
        logger.error(f"绘图过程出错: {str(e)}")
    
    # 输出回测指标
    logger.info(f"夏普比率: {sharpe:.3f}")
    logger.info(f"最大回撤: {drawdown:.2f}%")
    logger.info(f"年化收益率: {returns:.2f}%")

def run_realtime(args):
    """运行实盘交易"""
    # 只在实盘模式下导入miniQMT API
    try:
        # 尝试导入但不实际使用，避免在回测模式下报错
        import importlib.util
        qmt_spec = importlib.util.find_spec('realtime.qmt_trader')
        if qmt_spec is None:
            logger.error("无法找到realtime.qmt_trader模块")
            return
            
        from realtime.qmt_trader import QMTTrader
        logger.info("成功导入miniQMT API")
    except ImportError as e:
        logger.error(f"无法导入miniQMT API: {e}")
        logger.error("实盘交易需要正确安装miniQMT")
        return
    
    logger.info(f"开始实盘交易 策略: {args.strategy}")
    # 实盘交易逻辑...

def main():
    """主函数"""
    try:
        args = parse_args()
        
        if args.check:
            # 导入并运行检查工具
            from tools.stock_code_checker import check_stock_data_availability, get_etf_info
            
            if not args.code:
                logger.error("检查模式需要指定股票代码，使用 --code 参数")
                return
                
            logger.info(f"检查代码: {args.code}")
            available, details = check_stock_data_availability(args.code)
            
            logger.info(f"数据可用: {'是' if available else '否'}")
            if isinstance(details, dict):
                for k, v in details.items():
                    logger.info(f"{k}: {v}")
            else:
                logger.info(f"详情: {details}")
                
            # 如果是ETF，获取额外信息
            etf_info = get_etf_info(args.code)
            if etf_info:
                logger.info("ETF基本信息:")
                for k, v in etf_info.items():
                    logger.info(f"{k}: {v}")
                    
        elif args.backtest:
            run_backtest(args)
        elif args.realtime:
            run_realtime(args)
        else:
            logger.error("未指定运行模式，请使用--backtest、--realtime或--check参数")
            
    except Exception as e:
        logger.exception(f"程序执行出错: {e}")

if __name__ == "__main__":
    main() 