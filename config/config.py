"""
Configuration settings for the trading system
"""
import os
from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.parent

# Data directories
DATA_DIR = os.path.join(ROOT_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# Log directories
LOG_DIR = os.path.join(ROOT_DIR, "logs")
ORDER_LOG_DIR = os.path.join(LOG_DIR, "orders")
POSITION_LOG_DIR = os.path.join(LOG_DIR, "positions")
ERROR_LOG_DIR = os.path.join(LOG_DIR, "errors")

# Ensure directories exist
for directory in [DATA_DIR, CACHE_DIR, LOG_DIR, ORDER_LOG_DIR, POSITION_LOG_DIR, ERROR_LOG_DIR]:
    os.makedirs(directory, exist_ok=True)

# Backtest settings
BACKTEST_START_DATE = "2022-01-01"
BACKTEST_END_DATE = "2025-12-31"
BACKTEST_INITIAL_CAPITAL = 20000  # 2万初始资金
DEFAULT_BENCHMARK_CODE = "000300"  # 默认基准指数：沪深300

# Trading settings
DEFAULT_COMMISSION_RATE = 0.00005  # 万0.5手续费
DEFAULT_SLIPPAGE = 0.0001  # 滑点设置

# Strategy settings
MA_PERIOD = 20  # Default moving average period for the sample strategy

# miniQMT settings
QMT_ACCOUNT = ""  # Fill in your miniQMT account information
QMT_PASSWORD = ""  # Fill in your miniQMT password

# Data refresh settings
CACHE_EXPIRY_DAYS = 1  # Data cache expiry in days 