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
from datetime import datetime, timedelta
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入工具和策略
from utils.logger import setup_logger
from utils.data_fetcher import DataFetcher
from strategies.ma_strategy import MAStrategy
from strategies.sma_strategy import SMAStrategy
from strategies.etf_rotation_strategy import ETFRotationStrategy, ETF_POOL
from backtest.backtest_engine import run_backtest, BacktestEngine
from realtime.qmt_trader import run_realtime
from utils.plotting import plot_returns, setup_chinese_fonts
from config.config import (
    BACKTEST_START_DATE, 
    BACKTEST_END_DATE, 
    BACKTEST_INITIAL_CAPITAL,
    DEFAULT_BENCHMARK_CODE
)

# 设置日志
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("logs/cyber_trader_{time}.log", rotation="500 MB", level="DEBUG")

def main():
    """
    主函数，解析命令行参数并启动相应功能
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="CyberTrader - 自动化交易系统")
    
    # 添加功能选择参数组
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--backtest", action="store_true", help="运行回测模式")
    mode_group.add_argument("--trade", action="store_true", help="运行实盘交易模式")
    mode_group.add_argument("--check", action="store_true", help="检查股票代码")
    
    # 添加回测模式参数
    backtest_group = parser.add_argument_group("回测参数")
    backtest_group.add_argument("--strategy", type=str, default="etf_rotation", help="策略名称: etf_rotation, sma, etc.")
    backtest_group.add_argument("--start_date", type=str, default=BACKTEST_START_DATE, help="回测开始日期 (YYYY-MM-DD)")
    backtest_group.add_argument("--end_date", type=str, default=BACKTEST_END_DATE, help="回测结束日期 (YYYY-MM-DD)")
    backtest_group.add_argument("--initial_cash", type=float, default=BACKTEST_INITIAL_CAPITAL, help="初始资金")
    backtest_group.add_argument("--benchmark", type=str, default=DEFAULT_BENCHMARK_CODE, help="基准指数代码")
    
    # 添加ETF轮动策略参数
    etf_group = parser.add_argument_group("ETF轮动策略参数")
    etf_group.add_argument("--short_period", type=int, default=20, help="短期动量周期")
    etf_group.add_argument("--long_period", type=int, default=60, help="长期动量周期")
    etf_group.add_argument("--max_volatility", type=float, default=0.3, help="最大波动率")
    etf_group.add_argument("--top_n", type=int, default=3, help="持有ETF数量")
    etf_group.add_argument("--rebalance_days", type=int, default=5, help="再平衡周期(天)")
    
    # 添加实盘交易参数
    trade_group = parser.add_argument_group("实盘交易参数")
    trade_group.add_argument("--broker", type=str, default="simulator", help="券商API: simulator, eastmoney, etc.")
    trade_group.add_argument("--account", type=str, help="交易账户")
    trade_group.add_argument("--password", type=str, help="交易密码")
    
    # 添加股票代码检查参数
    check_group = parser.add_argument_group("股票代码检查参数")
    check_group.add_argument("--code", type=str, help="股票代码")
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 根据模式启动相应功能
    if args.backtest:
        run_backtest_function(args)
    elif args.trade:
        run_trade_function(args)
    elif args.check:
        run_code_checker(args)

def run_backtest_function(args):
    """
    运行回测功能
    
    Parameters:
    -----------
    args : argparse.Namespace
        命令行参数
    """
    logger.info("启动回测模式")
    
    # 设置中文字体
    font_prop = setup_chinese_fonts()
    
    # 根据策略名称选择对应的策略
    if args.strategy.lower() == "etf_rotation":
        logger.info("使用ETF轮动策略进行回测")
        
        # 设置策略参数
        strategy_params = {
            'short_period': args.short_period,
            'long_period': args.long_period,
            'max_volatility': args.max_volatility,
            'top_n': args.top_n,
            'rebalance_days': args.rebalance_days
        }
        
        # 运行回测
        results = run_backtest(
            strategy=ETFRotationStrategy,
            universe=ETF_POOL,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.initial_cash,
            is_etf=True,
            benchmark_code=args.benchmark,
            strategy_params=strategy_params
        )
        
        # 绘制回测结果
        if results:
            plot_returns(
                strategy_returns=results['cumulative_returns'],
                benchmark_returns=results['benchmark_returns'],
                statistics=results['statistics'],
                font_properties=font_prop
            )
        else:
            logger.error("回测失败，无法绘制结果")
    
    elif args.strategy.lower() == "sma":
        logger.info("使用SMA策略进行回测")
        # 这里可以添加其他策略的回测代码
        logger.warning("SMA策略尚未实现")
    
    else:
        logger.error(f"未知策略: {args.strategy}")

def run_trade_function(args):
    """
    运行实盘交易功能
    
    Parameters:
    -----------
    args : argparse.Namespace
        命令行参数
    """
    logger.info("启动实盘交易模式")
    logger.warning("实盘交易功能尚未实现")
    # 这里可以添加实盘交易的代码

def run_code_checker(args):
    """
    运行股票代码检查功能
    
    Parameters:
    -----------
    args : argparse.Namespace
        命令行参数
    """
    logger.info(f"检查股票代码: {args.code}")
    
    # 创建数据获取器
    data_fetcher = DataFetcher()
    
    # 获取股票基本信息
    stock_info = data_fetcher.get_stock_info(args.code)
    
    if stock_info is not None:
        logger.info(f"股票名称: {stock_info.get('name', '未知')}")
        logger.info(f"所属行业: {stock_info.get('industry', '未知')}")
        logger.info(f"上市日期: {stock_info.get('list_date', '未知')}")
        logger.info(f"总股本: {stock_info.get('total_share', '未知')}")
        logger.info(f"流通股本: {stock_info.get('float_share', '未知')}")
    else:
        logger.error(f"无法获取股票 {args.code} 的信息，请检查代码是否正确")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"程序异常: {e}")
        sys.exit(1) 