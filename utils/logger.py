"""
Logging utility for the trading system
"""
import os
import sys
import datetime
from loguru import logger

from config.config import LOG_DIR, ERROR_LOG_DIR

def setup_logger():
    """
    Configure the logger for the system
    """
    # Remove default handlers
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler for general logs
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f"trading_{current_date}.log")
    
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation="1 day",
        retention="30 days"
    )
    
    # Add file handler for error logs
    error_log_file = os.path.join(ERROR_LOG_DIR, f"error_{current_date}.log")
    
    logger.add(
        error_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 day",
        retention="30 days"
    )
    
    logger.info("Logger initialized")
    return logger

def get_strategy_logger(strategy_name):
    """
    Get a logger specifically for a strategy
    
    Parameters:
    -----------
    strategy_name : str
        Name of the strategy
    
    Returns:
    --------
    loguru.Logger
        Logger configured for the strategy
    """
    strategy_log_dir = os.path.join(LOG_DIR, "strategies", strategy_name)
    os.makedirs(strategy_log_dir, exist_ok=True)
    
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    strategy_log_file = os.path.join(strategy_log_dir, f"{strategy_name}_{current_date}.log")
    
    # Create a copy of the main logger
    strategy_logger = logger.bind(strategy=strategy_name)
    
    # Add file handler specific to this strategy
    logger.add(
        strategy_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[strategy]} | {function}:{line} - {message}",
        filter=lambda record: record["extra"].get("strategy") == strategy_name,
        level="INFO",
        rotation="1 day",
        retention="30 days"
    )
    
    return strategy_logger

class CSVLogger:
    """
    Logger for order and position CSV files
    """
    def __init__(self, log_dir, prefix):
        """
        Initialize the CSV logger
        
        Parameters:
        -----------
        log_dir : str
            Directory to save CSV logs
        prefix : str
            Prefix for log files
        """
        self.log_dir = log_dir
        self.prefix = prefix
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate log filename with date
        current_date = datetime.datetime.now().strftime("%Y%m%d")
        self.log_file = os.path.join(log_dir, f"{prefix}_{current_date}.csv")
        
        # Create file with header if it doesn't exist
        if not os.path.exists(self.log_file):
            self._create_header()
    
    def _create_header(self):
        """
        Create CSV file with header
        """
        if self.prefix == "orders":
            header = "timestamp,stock_code,action,price,quantity,order_id,status,message\n"
        elif self.prefix == "positions":
            header = "timestamp,stock_code,quantity,cost_price,current_price,market_value,profit_loss,profit_loss_pct\n"
        else:
            header = "timestamp,message\n"
            
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(header)
    
    def log_order(self, stock_code, action, price, quantity, order_id, status, message=""):
        """
        Log an order to CSV
        """
        if self.prefix != "orders":
            logger.error("Trying to log order with non-order logger")
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp},{stock_code},{action},{price},{quantity},{order_id},{status},{message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line)
            
    def log_position(self, stock_code, quantity, cost_price, current_price, market_value, profit_loss, profit_loss_pct):
        """
        Log a position to CSV
        """
        if self.prefix != "positions":
            logger.error("Trying to log position with non-position logger")
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp},{stock_code},{quantity},{cost_price},{current_price},{market_value},{profit_loss},{profit_loss_pct}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def log_message(self, message):
        """
        Log a general message to CSV
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp},{message}\n"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(line) 