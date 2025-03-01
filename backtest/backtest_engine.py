"""
Backtesting engine using backtrader
"""
import os
from datetime import datetime
import pandas as pd
import backtrader as bt
from loguru import logger
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from utils.data_fetcher import DataFetcher
from config.config import (
    BACKTEST_START_DATE, 
    BACKTEST_END_DATE, 
    BACKTEST_INITIAL_CAPITAL,
    DEFAULT_COMMISSION_RATE,
    DEFAULT_SLIPPAGE,
    DEFAULT_BENCHMARK_CODE
)

class StrategyWrapper(bt.Strategy):
    """
    Wrapper for custom strategy to use with backtrader
    """
    
    params = (
        ('strategy', None),  # Our custom strategy instance
    )
    
    def __init__(self):
        """Initialize the strategy wrapper"""
        self.strategy = self.params.strategy
        
        # Data dictionaries
        self.current_data = {}
        self.history_data = {}
        
        # Set the initial cash for our strategy
        self.strategy.set_initial_capital(self.broker.getvalue())
        
        # Map backtrader data feeds to our strategy's universe
        for i, d in enumerate(self.datas):
            stock_code = d._name
            self.history_data[stock_code] = None  # Initialize history data
    
    def next(self):
        """Called for each bar"""
        # Prepare data for our strategy
        current_date = self.datetime.date()
        
        # Update data for each symbol
        for i, d in enumerate(self.datas):
            stock_code = d._name
            
            # Current data
            self.current_data[stock_code] = {
                'open': d.open[0],
                'high': d.high[0],
                'low': d.low[0],
                'close': d.close[0],
                'volume': d.volume[0],
                'date': current_date
            }
            
            # Historical data for this stock
            hist_data = pd.DataFrame({
                'open': [d.open[j] for j in range(-len(d) + 1, 1)],
                'high': [d.high[j] for j in range(-len(d) + 1, 1)],
                'low': [d.low[j] for j in range(-len(d) + 1, 1)],
                'close': [d.close[j] for j in range(-len(d) + 1, 1)],
                'volume': [d.volume[j] for j in range(-len(d) + 1, 1)]
            })
            
            # Add history to current data
            self.current_data[stock_code]['history'] = hist_data
        
        # Execute our strategy
        orders = self.strategy.handle_data(current_date, self.current_data)
        
        # Convert orders to backtrader orders
        for order in orders:
            stock_code = order['stock_code']
            action = order['action']
            quantity = order['quantity']
            
            # Find the data feed for this stock
            data = None
            for i, d in enumerate(self.datas):
                if d._name == stock_code:
                    data = d
                    break
            
            if data is None:
                logger.warning(f"Stock {stock_code} not found in data feeds")
                continue
            
            # Create backtrader order
            if action == 'BUY':
                self.buy(data=data, size=quantity)
                # Update our strategy's position
                price = self.current_data[stock_code]['close']
                self.strategy.update_position(stock_code, quantity, price)
            elif action == 'SELL':
                self.sell(data=data, size=quantity)
                # Update our strategy's position
                price = self.current_data[stock_code]['close']
                self.strategy.update_position(stock_code, -quantity, price)
    
    def stop(self):
        """Called when backtesting is finished"""
        # Print final results
        portfolio_value = self.broker.getvalue()
        initial_value = self.broker.startingcash
        returns = (portfolio_value / initial_value - 1) * 100
        
        logger.info(f"Final Portfolio Value: {portfolio_value:.2f}")
        logger.info(f"Return: {returns:.2f}%")
        
        # Print positions
        positions = {}
        for i, d in enumerate(self.datas):
            stock_code = d._name
            position = self.getposition(d).size
            if position != 0:
                positions[stock_code] = position
        
        logger.info(f"Final Positions: {positions}")


class BacktestEngine:
    """
    Backtesting engine using backtrader
    """
    
    def __init__(self, 
                 start_date=None, 
                 end_date=None, 
                 initial_capital=None,
                 commission_rate=None,
                 slippage=None,
                 benchmark_code=None):
        """
        Initialize the backtest engine
        
        Parameters:
        -----------
        start_date : str
            Start date in 'YYYY-MM-DD' format
        end_date : str
            End date in 'YYYY-MM-DD' format
        initial_capital : float
            Initial capital for backtesting
        commission_rate : float
            Commission rate (e.g., 0.0003 for 0.03%)
        slippage : float
            Slippage (e.g., 0.0001 for 0.01%)
        benchmark_code : str
            Benchmark code (e.g., '000300' for CSI 300)
        """
        self.start_date = start_date or BACKTEST_START_DATE
        self.end_date = end_date or BACKTEST_END_DATE
        self.initial_capital = initial_capital or BACKTEST_INITIAL_CAPITAL
        self.commission_rate = commission_rate or DEFAULT_COMMISSION_RATE
        self.slippage = slippage or DEFAULT_SLIPPAGE
        self.benchmark_code = benchmark_code or DEFAULT_BENCHMARK_CODE
        
        self.data_fetcher = DataFetcher()
        self.cerebro = bt.Cerebro()
        
        # Set initial capital
        self.cerebro.broker.setcash(self.initial_capital)
        
        # Set commission scheme
        self.cerebro.broker.setcommission(commission=self.commission_rate)
        
        # 添加自定义观察者，用于记录每日净值
        from backtest.observers import ValueObserver
        self.cerebro.addobserver(ValueObserver)
        
        logger.info(f"初始化回测引擎，日期范围: {self.start_date} 至 {self.end_date}")
        logger.info(f"初始资金: {self.initial_capital}")
        if self.benchmark_code:
            logger.info(f"基准指数: {self.benchmark_code}")
    
    def add_data(self, stock_code, adjust="qfq", is_etf=False):
        """
        Add stock or ETF data to the backtest engine
        
        Parameters:
        -----------
        stock_code : str
            Stock or ETF code
        adjust : str
            Price adjustment method: "qfq" for forward adjustment,
            "hfq" for backward adjustment, None for no adjustment
        is_etf : bool
            Whether the code is an ETF (True) or stock (False)
        """
        # Get data from data fetcher
        if is_etf:
            df = self.data_fetcher.get_etf_data(
                stock_code, 
                self.start_date, 
                self.end_date, 
                adjust=adjust
            )
            logger.info(f"Using ETF data for {stock_code}")
        else:
            df = self.data_fetcher.get_stock_data(
                stock_code, 
                self.start_date, 
                self.end_date, 
                adjust=adjust
            )
        
        if df.empty:
            logger.warning(f"No data available for {stock_code}")
            return False
        
        # Create a backtrader data feed
        data = bt.feeds.PandasData(
            dataname=df,
            name=stock_code,
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1,  # Not used
            datetime=None,    # Use index as datetime
        )
        
        # Add data to cerebro
        self.cerebro.adddata(data)
        logger.info(f"Added data for {stock_code}")
        return True
    
    def add_benchmark(self):
        """
        Add benchmark data to the backtest engine
        
        Returns:
        --------
        bool
            True if benchmark data was added successfully, False otherwise
        """
        if not self.benchmark_code:
            logger.warning("No benchmark code specified")
            return False
        
        # Check if benchmark is an ETF or stock
        is_etf = False
        if self.benchmark_code.startswith('5') or self.benchmark_code.startswith('1'):
            is_etf = True
            logger.info(f"Benchmark {self.benchmark_code} is an ETF")
        
        # Add benchmark data
        success = self.add_data(self.benchmark_code, is_etf=is_etf)
        if success:
            logger.info(f"Added benchmark data for {self.benchmark_code}")
        else:
            logger.warning(f"Failed to add benchmark data for {self.benchmark_code}")
        
        return success
    
    def run(self, strategy, strategy_params=None):
        """Run backtest with the given strategy"""
        if strategy_params is None:
            strategy_params = {}
            
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TimeDrawDown, _name='timedrawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
        
        # Add benchmark analyzer if benchmark data is available
        if len(self.cerebro.datas) > 1:
            self.cerebro.addanalyzer(
                bt.analyzers.TimeReturn,
                _name='benchmark',
                data=self.cerebro.datas[-1],
                timeframe=bt.TimeFrame.Days
            )
            strategy_params['benchmark'] = True
            
        self.cerebro.addstrategy(strategy, **strategy_params)
        
        # Run backtest
        logger.info("Running backtest...")
        results = self.cerebro.run()
        
        # Get the first strategy instance
        if not results:
            logger.error("Backtest failed - no results returned")
            return None
            
        strat = results[0]
        
        # Process results
        return self._process_results(strat)
    
    def _process_results(self, strat):
        """Process backtest results"""
        # Get returns analysis from TimeReturn analyzer
        returns_analysis = strat.analyzers.timereturn.get_analysis()
        
        # Extract returns data properly
        daily_returns_data = []
        for k, v in returns_analysis.items():
            # Skip non-datetime keys and ensure v is a valid number
            if isinstance(k, datetime) and isinstance(v, (int, float)):
                daily_returns_data.append((k, float(v)))
        
        if not daily_returns_data:
            logger.warning("No valid return data found in returns analysis")
            logger.debug(f"Returns analysis content: {returns_analysis}")
            # Initialize with zero returns for the backtest period
            start_date = pd.to_datetime(self.start_date)
            end_date = pd.to_datetime(self.end_date)
            dates = pd.date_range(start=start_date, end=end_date, freq='B')
            daily_returns = pd.Series(0.0, index=dates)
        else:
            # Sort by date and create returns series
            daily_returns_data.sort(key=lambda x: x[0])
            dates = [x[0] for x in daily_returns_data]
            returns = [x[1] for x in daily_returns_data]
            daily_returns = pd.Series(returns, index=dates)
        
        # Calculate cumulative returns
        cumulative_returns = (1 + daily_returns).cumprod() - 1
        
        # Process benchmark returns
        benchmark_returns = None
        try:
            if hasattr(strat.analyzers, 'benchmark'):
                benchmark_analysis = strat.analyzers.benchmark.get_analysis()
                benchmark_rets = []
                benchmark_dates = []
                for k, v in benchmark_analysis.items():
                    if isinstance(k, datetime) and isinstance(v, (int, float)):
                        benchmark_dates.append(k)
                        benchmark_rets.append(float(v))
                if benchmark_dates:
                    benchmark_returns = pd.Series(benchmark_rets, index=benchmark_dates)
                    benchmark_returns = (1 + benchmark_returns).cumprod() - 1
        except Exception as e:
            logger.warning(f"Could not process benchmark returns: {e}")
            benchmark_returns = None
        
        # Calculate statistics
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        years = (end_date - start_date).days / 365.0
        
        initial_capital = self.initial_capital
        final_value = strat.broker.getvalue()
        total_return = (final_value - initial_capital) / initial_capital
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Get other statistics
        try:
            sharpe_ratio = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
        except:
            sharpe_ratio = 0.0
            
        try:
            drawdown = strat.analyzers.drawdown.get_analysis()
            max_drawdown = drawdown.get('max', {}).get('drawdown', 0.0) / 100
        except:
            max_drawdown = 0.0
            
        try:
            trade_analyzer = strat.analyzers.trades.get_analysis()
            total_trades = trade_analyzer.total.closed if hasattr(trade_analyzer, 'total') else 0
            won_trades = trade_analyzer.won.total if hasattr(trade_analyzer, 'won') else 0
            win_rate = won_trades / total_trades if total_trades > 0 else 0
        except:
            total_trades = 0
            win_rate = 0.0
        
        # Create results dictionary
        statistics = {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'returns': total_return * 100,  # Convert to percentage
            'annual_return': annual_return * 100,  # Convert to percentage
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown * 100,  # Convert to percentage
            'total_trades': total_trades,
            'win_rate': win_rate * 100,  # Convert to percentage
        }

        results = {
            'daily_returns': daily_returns,
            'cumulative_returns': cumulative_returns,
            'benchmark_returns': benchmark_returns,  # Always include benchmark_returns, even if None
            'statistics': statistics  # Add statistics to results
        }
        
        # Plot results
        self._plot_results(results, start_date, end_date)
        
        return results
    
    def _plot_results(self, results, start_date, end_date):
        """Plot backtest results"""
        # Plot cumulative returns
        plt.figure(figsize=(12, 8))
        
        # 绘制策略收益率曲线（蓝色面积图）
        plt.fill_between(results['cumulative_returns'].index, 
                         0, 
                         results['cumulative_returns'].values * 100, 
                         color='blue', alpha=0.3, label='_nolegend_')
        plt.plot(results['cumulative_returns'].index, 
                 results['cumulative_returns'].values * 100, 
                 color='blue', linewidth=2, label='策略')
        
        # Only plot benchmark returns if they exist in the results
        if 'benchmark_returns' in results and results['benchmark_returns'] is not None:
            plt.plot(results['benchmark_returns'].index, 
                    results['benchmark_returns'].values * 100,
                    color='darkred', linewidth=2, linestyle='-', label='基准')

        plt.grid(True)
        plt.xlabel('日期')
        plt.ylabel('累计收益率 (%)')
        plt.title(f'回测结果 ({start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")})')
        
        # Add statistics to plot
        stats_text = (
            f'总收益率: {results["statistics"]["returns"]:.2f}%\n'
            f'年化收益率: {results["statistics"]["annual_return"]:.2f}%\n'
            f'最大回撤: {results["statistics"]["max_drawdown"]:.2f}%\n'
            f'夏普系数: {results["statistics"]["sharpe_ratio"]:.2f}\n'
            f'交易次数: {results["statistics"]["total_trades"]}\n'
            f'胜率: {results["statistics"]["win_rate"]:.2f}%'
        )
        
        plt.text(0.02, 0.02, stats_text,
                 transform=plt.gca().transAxes,
                 bbox=dict(facecolor='white', alpha=0.8),
                 fontsize=10,
                 verticalalignment='bottom')
        
        plt.legend()
        
        # Save plot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 确保输出目录存在
        os.makedirs('backtest_output', exist_ok=True)
        plt.savefig(f'backtest_output/回测结果_{timestamp}.png')
        plt.close()

    def plot(self, filename=None):
        """
        Plot backtest results
        
        Parameters:
        -----------
        filename : str
            Filename to save the plot (if None, display the plot)
        """
        try:
            if filename:
                # 确保输出目录存在
                os.makedirs('backtest_output', exist_ok=True)
                output_path = os.path.join('backtest_output', filename)
                self.cerebro.plot(style='candle', barup='red', bardown='green',
                                 volup='red', voldown='green', 
                                 save_as=output_path)
                logger.info(f"Saved backtest plot to {output_path}")
            else:
                self.cerebro.plot(style='candle', barup='red', bardown='green',
                                 volup='red', voldown='green')
        except Exception as e:
            logger.error(f"Failed to plot backtest results: {e}")


# Function to run a backtest
def run_backtest(strategy, universe, start_date=None, end_date=None, initial_capital=None, is_etf=False, benchmark_code=None, strategy_params=None):
    """
    Run a backtest with the given strategy and universe
    
    Parameters:
    -----------
    strategy : bt.Strategy
        Backtrader strategy class
    universe : list
        List of stock or ETF codes
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    initial_capital : float
        Initial capital for backtesting
    is_etf : bool
        Whether the universe contains ETFs (True) or stocks (False)
    benchmark_code : str
        Benchmark code (e.g., '000300' for CSI 300)
    strategy_params : dict
        Strategy parameters
        
    Returns:
    --------
    dict
        Backtest results
    """
    # Create backtest engine
    engine = BacktestEngine(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        benchmark_code=benchmark_code
    )
    
    # Add data for each stock/ETF in the universe
    for code in universe:
        engine.add_data(code, is_etf=is_etf)
    
    # Add benchmark data if specified
    if benchmark_code:
        engine.add_benchmark()
    
    # Run the backtest
    results = engine.run(strategy, strategy_params)
    
    return results 