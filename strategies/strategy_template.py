"""
A股交易系统策略模板
兼容回测和实盘交易
"""
from datetime import datetime
import backtrader as bt
import pandas as pd
import logging
from loguru import logger
import argparse
import akshare as ak

class BaseStrategy(bt.Strategy):
    """
    基础策略类，兼容回测和实盘交易
    核心方法按执行顺序排列，用户只需填写特定逻辑
    """
    
    # ==================== 可配置参数 ====================
    params = (
        ('mode', 'backtest'),  # 运行模式: 'backtest'/'live'
        ('symbol', '600519'),  # 交易标的
        ('risk_ratio', 0.02),  # 单次风险比例（基于总账户资金）
        ('log_path', './logs/trading_log.txt'),  # 实盘交易日志路径
        ('benchmark', '000300'),  # 基准指数代码
    )
    
    def __init__(self):
        """初始化数据和指标"""
        # 数据预处理（兼容AKShare和实盘数据）
        self.data_close = self.datas[0].close
        self.data_high = self.datas[0].high
        self.data_low = self.datas[0].low
        self.data_open = self.datas[0].open
        self.data_volume = self.datas[0].volume
        
        # 技术指标计算（示例：双均线）
        self.sma_fast = bt.indicators.SMA(self.data_close, period=5)
        self.sma_slow = bt.indicators.SMA(self.data_close, period=20)
        
        # 实盘交易初始化（仅在实盘模式下生效）
        if self.p.mode == 'live':
            self.logger = self._init_logger()
            self.current_position = 0  # 实际持仓
            
    def next(self):
        """为每个K线执行策略逻辑"""
        # 步骤1：生成信号
        signal = self.generate_signal()
        
        # 步骤2：风险检查（持仓、涨跌停、流动性）
        if not self.check_risk(signal):
            return
        
        # 步骤3：执行交易订单
        self.execute_trade(signal)
        
        # 步骤4：记录日志（实盘模式下生效）
        self.record_log(signal)
    
    # ==================== 用户需要自定义的方法 ====================  
    def generate_signal(self):
        """
        生成交易信号，返回格式示例：
        {'direction': 1,  # 1: 做多, -1: 做空, 0: 平仓
         'price': self.data_close[0],  # 触发价格
         'size': 100}  # 交易数量（股）
        """
        # 示例：双均线金叉/死叉策略
        signal = {'direction': 0, 'price': 0, 'size': 0}
        
        # 金叉：快线上穿慢线
        if self.sma_fast[0] > self.sma_slow[0] and self.sma_fast[-1] <= self.sma_slow[-1]:
            signal['direction'] = 1
            signal['size'] = self.calculate_position_size()  # 计算持仓规模
            
        # 死叉：快线下穿慢线
        elif self.sma_fast[0] < self.sma_slow[0] and self.sma_fast[-1] >= self.sma_slow[-1]:
            signal['direction'] = -1
            signal['size'] = self.position.size  # 清仓
            
        signal['price'] = self.data_close[0]
        return signal
    
    def calculate_position_size(self):
        """计算持仓规模（基于风险比例）"""
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.p.risk_ratio
        price = self.data_close[0]
        return int(risk_amount / price / 100) * 100  # A股按手（100股）取整
    
    # ==================== 通用方法（无需修改） ====================
    def check_risk(self, signal):
        """风险检查（涨跌停、流动性、持仓限制）"""
        # 示例：避免在涨跌停时交易
        if self.data_close[0] == self.data_high[0] and signal['direction'] == 1:
            return False  # 不在涨停时买入
        if self.data_close[0] == self.data_low[0] and signal['direction'] == -1:
            return False  # 不在跌停时卖出
        return True
    
    def execute_trade(self, signal):
        """执行交易（自动兼容回测/实盘交易）"""
        if signal['direction'] == 1:
            self.buy(price=signal['price'], size=signal['size'])
        elif signal['direction'] == -1:
            self.sell(price=signal['price'], size=signal['size'])
    
    def record_log(self, signal):
        """记录交易日志（实盘模式下生效）"""
        if self.p.mode == 'live':
            log_msg = f"{datetime.now()}, {self.p.symbol}, Direction:{signal['direction']}, Price:{signal['price']}, Size:{signal['size']}"
            self.logger.info(log_msg)
            # 记录持仓到CSV（示例）
            pd.DataFrame([{'Time': datetime.now(), 'Position': self.current_position}]).to_csv('logs/position.csv', mode='a', header=False)
    
    def _init_logger(self):
        """初始化实盘交易日志记录器"""
        logger = logging.getLogger('A-Shares Trading System')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.p.log_path)
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

# ==================== Strategy usage example ==================== 
if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='A股交易策略回测')
    parser.add_argument('--symbol', type=str, default='600519', help='股票代码 (默认: 600519)')
    parser.add_argument('--benchmark', type=str, default='000300', help='基准指数代码 (默认: 000300 沪深300)')
    parser.add_argument('--start-date', type=str, default='2020-01-01', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31', help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--initial-cash', type=float, default=1000000.0, help='初始资金 (默认: 1,000,000)')
    args = parser.parse_args()
    
    # Backtesting mode
    cerebro = bt.Cerebro()
    
    # 获取股票数据
    print(f"获取股票数据: {args.symbol}")
    df = ak.stock_zh_a_hist(symbol=args.symbol, period="daily", adjust="qfq", 
                           start_date=args.start_date, end_date=args.end_date)
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
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # 获取基准指数数据
    print(f"获取基准指数数据: {args.benchmark}")
    try:
        benchmark_df = ak.stock_zh_index_daily(symbol=args.benchmark)
        benchmark_df = benchmark_df.rename(columns={
            '日期': 'date',
            '收盘': 'close',
        })
        benchmark_df['date'] = pd.to_datetime(benchmark_df['date'])
        benchmark_df.set_index('date', inplace=True)
        
        # 过滤日期范围
        benchmark_df = benchmark_df.loc[args.start_date:args.end_date]
        
        # 计算基准收益率
        benchmark_returns = benchmark_df['close'].pct_change().fillna(0)
        benchmark_cumulative_return = (1 + benchmark_returns).cumprod().iloc[-1] - 1
        
        # 计算基准年化收益率
        days = (benchmark_df.index[-1] - benchmark_df.index[0]).days
        benchmark_annual_return = (1 + benchmark_cumulative_return) ** (365 / days) - 1
    except Exception as e:
        print(f"获取基准指数数据失败: {e}")
        benchmark_cumulative_return = 0
        benchmark_annual_return = 0
    
    # Add analyzers for performance metrics
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual')
    
    # Add strategy
    cerebro.addstrategy(BaseStrategy, mode='backtest', symbol=args.symbol, benchmark=args.benchmark)
    
    # Set initial cash
    cerebro.broker.setcash(args.initial_cash)
    
    # Set commission
    cerebro.broker.setcommission(commission=0.0003)
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    # Print performance metrics
    print('=' * 50)
    print('回测结果')
    print('=' * 50)
    
    # Portfolio value
    initial_value = args.initial_cash
    final_value = cerebro.broker.getvalue()
    returns_pct = (final_value / initial_value - 1) * 100
    
    print(f'初始资金: {initial_value:,.2f}')
    print(f'最终资金: {final_value:,.2f}')
    print(f'收益: {returns_pct:.2f}%')
    
    # Get analyzer results
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    annual = strat.analyzers.annual.get_analysis()
    
    # Print more statistics
    print(f'夏普比率: {sharpe.get("sharperatio", 0):.4f}')
    print(f'最大回撤: {-drawdown.get("max", {}).get("drawdown", 0) * 100:.2f}%')
    print(f'交易次数: {trades.get("total", {}).get("total", 0)}')
    
    # Calculate win rate
    total_trades = trades.get("total", {}).get("total", 0)
    won_trades = trades.get("won", {}).get("total", 0)
    if total_trades > 0:
        win_rate = won_trades / total_trades * 100
    else:
        win_rate = 0
    print(f'胜率: {win_rate:.2f}%')
    
    # 计算策略年化收益率
    days = (df.index[-1] - df.index[0]).days
    if days > 0:
        annual_return = ((final_value / initial_value) ** (365 / days) - 1) * 100
        print(f'年化收益率: {annual_return:.2f}%')
    
    # 打印基准对比
    print('-' * 30)
    print('基准对比')
    print(f'基准指数: {args.benchmark}')
    print(f'基准累计收益率: {benchmark_cumulative_return * 100:.2f}%')
    print(f'基准年化收益率: {benchmark_annual_return * 100:.2f}%')
    print(f'超额收益: {returns_pct - benchmark_cumulative_return * 100:.2f}%')
    if days > 0:
        print(f'年化超额收益: {annual_return - benchmark_annual_return * 100:.2f}%')
    
    # Print annual returns
    print('-' * 30)
    print('年度收益')
    for year, ret in annual.items():
        print(f'{year}: {ret * 100:.2f}%')
    print('=' * 50)
    
    # Live trading mode (requires miniQMT connection)
    # cerebro.addstrategy(BaseStrategy, mode='live', symbol='600519')
    # cerebro.run() 