"""
使用新模板结构实现的单均线策略
"""
from strategies.strategy_template import BaseStrategy
import backtrader as bt
from loguru import logger

class SMAStrategy(BaseStrategy):
    """
    单均线策略
    
    交易逻辑:
    - 当价格上穿均线时买入
    - 当价格下穿均线时卖出
    """
    
    params = (
        ('mode', 'backtest'),  # 运行模式: 'backtest'/'live'
        ('symbol', '600519'),  # 交易标的
        ('risk_ratio', 0.02),  # 单次风险比例
        ('log_path', './logs/trading_log.txt'),  # 实盘交易日志路径
        ('ma_period', 20),  # 移动平均周期
        ('is_etf', False),  # 是否交易ETF
    )
    
    def __init__(self):
        """初始化策略指标"""
        # 调用父类初始化方法
        super(SMAStrategy, self).__init__()
        
        # 创建简单移动平均指标
        self.sma = bt.indicators.SMA(self.data_close, period=self.params.ma_period)
        logger.info(f"初始化SMA策略，周期: {self.params.ma_period}")
        logger.info(f"交易类型: {'ETF' if self.params.is_etf else '股票'}")
    
    def generate_signal(self):
        """
        基于价格穿越移动平均线生成交易信号
        """
        signal = {'direction': 0, 'price': self.data_close[0], 'size': 0}
        
        # 价格上穿均线 - 买入信号
        if self.data_close[0] > self.sma[0] and self.data_close[-1] <= self.sma[-1]:
            signal['direction'] = 1
            signal['size'] = self.calculate_position_size()
            logger.info(f"买入信号: 价格 {self.data_close[0]} 上穿均线 {self.sma[0]}")
            
        # 价格下穿均线 - 卖出信号
        elif self.data_close[0] < self.sma[0] and self.data_close[-1] >= self.sma[-1]:
            signal['direction'] = -1
            # 使用backtrader中的self.position.size获取当前持仓
            signal['size'] = self.position.size if self.position.size > 0 else 0
            logger.info(f"卖出信号: 价格 {self.data_close[0]} 下穿均线 {self.sma[0]}")
            
        return signal

# Example usage
if __name__ == '__main__':
    import akshare as ak
    import pandas as pd
    import backtrader as bt
    import argparse
    import datetime
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SMA Strategy Backtest')
    parser.add_argument('--symbol', type=str, default='600519', help='Stock or ETF symbol')
    parser.add_argument('--ma-period', type=int, default=20, help='Moving average period')
    parser.add_argument('--etf', action='store_true', help='Trade ETF instead of stock')
    parser.add_argument('--benchmark', type=str, default='000300', help='Benchmark index code (default: 000300 for CSI 300)')
    parser.add_argument('--start-date', type=str, default='2020-01-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31', help='End date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    # Create a backtrader instance
    cerebro = bt.Cerebro()
    
    # Get data using AKShare
    if args.etf:
        print(f"获取ETF数据: {args.symbol}")
        df = ak.fund_etf_hist_em(symbol=args.symbol, period="daily", adjust="qfq")
    else:
        print(f"获取股票数据: {args.symbol}")
        df = ak.stock_zh_a_hist(symbol=args.symbol, period="daily", adjust="qfq")
    
    # Rename columns to match backtrader requirements
    df = df.rename(columns={
        '日期': 'date',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
    })
    
    # Set date as index
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # Filter by date range
    if args.start_date:
        start_date = pd.to_datetime(args.start_date)
        df = df[df.index >= start_date]
    if args.end_date:
        end_date = pd.to_datetime(args.end_date)
        df = df[df.index <= end_date]
    
    # Create data feed
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # Get benchmark data
    benchmark_data = None
    benchmark_return = None
    benchmark_annual_returns = {}
    
    if args.benchmark:
        try:
            print(f"获取基准指数数据: {args.benchmark}")
            # Get benchmark data
            benchmark_df = ak.stock_zh_index_daily(symbol=args.benchmark)
            
            # Rename columns if needed
            benchmark_df = benchmark_df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Set date as index
            benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
            benchmark_df.set_index('date', inplace=True)
            
            # Filter by date range
            if args.start_date:
                benchmark_df = benchmark_df[benchmark_df.index >= start_date]
            if args.end_date:
                benchmark_df = benchmark_df[benchmark_df.index <= end_date]
            
            # Store benchmark data
            benchmark_data = benchmark_df
            
            # Calculate benchmark returns
            if not benchmark_df.empty:
                first_close = benchmark_df['close'].iloc[0]
                last_close = benchmark_df['close'].iloc[-1]
                benchmark_return = (last_close / first_close - 1) * 100
                
                # Calculate annual benchmark returns
                years = benchmark_df.index.year.unique()
                for year in years:
                    year_data = benchmark_df[benchmark_df.index.year == year]
                    if not year_data.empty:
                        first = year_data['close'].iloc[0]
                        last = year_data['close'].iloc[-1]
                        benchmark_annual_returns[str(year)] = (last / first - 1) * 100
                
                print(f"基准指数 {args.benchmark} 收益率: {benchmark_return:.2f}%")
            else:
                print(f"无法获取基准指数 {args.benchmark} 的数据")
                
        except Exception as e:
            print(f"获取基准指数数据时出错: {e}")
    
    # Add strategy with custom parameters
    cerebro.addstrategy(
        SMAStrategy, 
        mode='backtest', 
        ma_period=args.ma_period,
        symbol=args.symbol,
        is_etf=args.etf
    )
    
    # Set initial cash
    cerebro.broker.setcash(1000000.0)
    
    # Set commission
    cerebro.broker.setcommission(commission=0.0003)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    # Print final portfolio value
    final_value = cerebro.broker.getvalue()
    initial_value = 1000000.0
    returns_pct = (final_value / initial_value - 1) * 100
    
    print('=' * 50)
    print('回测结果')
    print('=' * 50)
    print(f'交易品种: {"ETF" if args.etf else "股票"}')
    print(f'代码: {args.symbol}')
    print(f'移动平均周期: {args.ma_period}')
    print(f'初始资金: {initial_value:.2f}')
    print(f'最终资产: {final_value:.2f}')
    print(f'盈亏: {final_value - initial_value:.2f}')
    print(f'收益率: {returns_pct:.2f}%')
    
    # Print benchmark comparison if available
    if benchmark_return is not None:
        print(f'基准收益率: {benchmark_return:.2f}%')
        print(f'超额收益率: {returns_pct - benchmark_return:.2f}%')
    
    # Get analyzer results
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    annual = strat.analyzers.annual.get_analysis()
    
    # Calculate max drawdown as negative value
    max_drawdown = -drawdown.get('max', {}).get('drawdown', 0) * 100
    
    # Print more statistics
    print(f'夏普比率: {sharpe.get("sharperatio", 0):.4f}')
    print(f'最大回撤: {max_drawdown:.2f}%')
    print(f'总交易次数: {trades.get("total", {}).get("total", 0)}')
    
    # Calculate win rate
    total_trades = trades.get("total", {}).get("total", 0)
    won_trades = trades.get("won", {}).get("total", 0)
    if total_trades > 0:
        win_rate = won_trades / total_trades * 100
    else:
        win_rate = 0
    
    print(f'盈利交易: {won_trades}')
    print(f'亏损交易: {trades.get("lost", {}).get("total", 0)}')
    print(f'胜率: {win_rate:.2f}%')
    
    # Print annual returns
    print('-' * 30)
    print('年度收益率')
    
    # Prepare data for side-by-side comparison
    years = sorted([str(year) for year in annual.keys()])
    
    # If benchmark data is available
    if benchmark_annual_returns:
        print(f"{'年份':<6}{'策略收益率':>12}{'基准收益率':>12}{'超额收益率':>12}")
        for year in years:
            strategy_return = annual.get(int(year), 0) * 100
            benchmark_return = benchmark_annual_returns.get(year, 0)
            excess_return = strategy_return - benchmark_return
            print(f"{year:<6}{strategy_return:>11.2f}%{benchmark_return:>11.2f}%{excess_return:>11.2f}%")
    else:
        print(f"{'年份':<6}{'收益率':>10}")
        for year in years:
            ret = annual.get(int(year), 0) * 100
            print(f"{year:<6}{ret:>9.2f}%")
    
    print('=' * 50) 