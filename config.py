from datetime import datetime

# 回测配置
BACKTEST_CONFIG = {
    'start_date': datetime(2024, 6, 16),
    'end_date': datetime(2025, 2, 16),
    'initial_cash': 15000,
    'commission_rate': 0.00005,  # 0.5‰
    'slippage': 0.0001,  # 滑点 0.1‰
}

# 数据配置
DATA_CONFIG = {
    'stock_code': '510300',  # 股票代码
    'benchmark_code': '510300',  # 基准代码
} 