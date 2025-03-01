"""
Real-time trading module using miniQMT
"""
import os
import time
import datetime
import pandas as pd
from loguru import logger

# Attempt to import QMT API
try:
    import xtquant.xttrader as xt
    from xtquant.xttype import StockAccount
except ImportError:
    logger.error("Failed to import miniQMT API. Make sure it's installed correctly.")

from utils.data_fetcher import DataFetcher
from utils.logger import CSVLogger
from config.config import ORDER_LOG_DIR, POSITION_LOG_DIR

class QMTTrader:
    """
    Real-time trader using miniQMT
    """
    
    def __init__(self, strategy, account_id=None, account_type="STOCK", is_etf=False):
        """
        Initialize the QMT trader
        
        Parameters:
        -----------
        strategy : BaseStrategy
            Trading strategy to use
        account_id : str
            Trading account ID
        account_type : str
            Account type (default is "STOCK")
        is_etf : bool
            Whether to trade ETFs (True) or stocks (False)
        """
        self.strategy = strategy
        self.account_id = account_id
        self.account_type = account_type
        self.is_etf = is_etf
        
        # Initialize data fetcher
        self.data_fetcher = DataFetcher()
        
        # Initialize loggers
        self.order_logger = CSVLogger(ORDER_LOG_DIR, "orders")
        self.position_logger = CSVLogger(POSITION_LOG_DIR, "positions")
        
        # Initialize connection status
        self.is_connected = False
        
        # Initialize callbacks
        self.order_callbacks = []
        
        logger.info(f"Initialized QMT trader with strategy: {strategy.name}")
        logger.info(f"Trading type: {'ETF' if is_etf else 'Stock'}")
    
    def connect(self):
        """
        Connect to the trading account
        
        Returns:
        --------
        bool
            True if connection was successful, False otherwise
        """
        try:
            # Initialize QMT client
            xt.start()
            
            # Wait a moment for connection
            time.sleep(2)
            
            # Verify QMT is running
            if not xt.get_trading_day():
                logger.error("Failed to connect to QMT. Make sure QMT is running.")
                return False
            
            # Get available accounts
            accounts = xt.get_accounts()
            
            if not accounts:
                logger.error("No trading accounts available.")
                return False
            
            # If account_id not provided, use the first available account
            if self.account_id is None:
                self.account_id = accounts[0]
                logger.info(f"Using account: {self.account_id}")
            
            # Check if the account exists
            if self.account_id not in accounts:
                logger.error(f"Account {self.account_id} not found. Available accounts: {accounts}")
                return False
            
            # Create account object
            self.account = StockAccount(self.account_id)
            
            # Register callbacks
            xt.subscribe_order_callback(self._on_order_callback)
            xt.subscribe_trade_callback(self._on_trade_callback)
            xt.subscribe_position_callback(self._on_position_callback)
            xt.subscribe_asset_callback(self._on_asset_callback)
            
            # Get initial positions
            self._update_positions()
            
            # Get initial cash
            cash = self._get_cash()
            if cash is not None:
                self.strategy.cash = cash
                self.strategy.initial_capital = cash
            
            self.is_connected = True
            logger.info(f"Successfully connected to account: {self.account_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to QMT: {e}")
            return False
    
    def disconnect(self):
        """
        Disconnect from the trading account
        """
        if self.is_connected:
            try:
                xt.stop()
                self.is_connected = False
                logger.info("Disconnected from QMT")
            except Exception as e:
                logger.error(f"Error disconnecting from QMT: {e}")
    
    def _get_cash(self):
        """
        Get available cash in the account
        
        Returns:
        --------
        float
            Available cash
        """
        try:
            asset = xt.query_asset(self.account)
            if asset:
                return asset.cash
            return None
        except Exception as e:
            logger.error(f"Error getting cash: {e}")
            return None
    
    def _update_positions(self):
        """
        Update current positions in the strategy
        """
        try:
            # Clear current positions
            self.strategy.positions = {}
            
            # Query positions from QMT
            positions = xt.query_stock_positions(self.account)
            
            # Update strategy positions
            for pos in positions:
                self.strategy.positions[pos.stock_code] = pos.volume
            
            logger.info(f"Updated positions: {self.strategy.positions}")
            
            # Log positions to CSV
            self._log_positions()
            
            return self.strategy.positions
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return {}
    
    def _log_positions(self):
        """
        Log current positions to CSV
        """
        try:
            positions = xt.query_stock_positions(self.account)
            
            for pos in positions:
                # Calculate profit/loss
                cost_price = pos.cost_price if hasattr(pos, 'cost_price') else 0
                current_price = self._get_current_price(pos.stock_code)
                market_value = pos.volume * current_price
                profit_loss = market_value - (pos.volume * cost_price)
                profit_loss_pct = (profit_loss / (pos.volume * cost_price)) * 100 if cost_price > 0 and pos.volume > 0 else 0
                
                # Log to CSV
                self.position_logger.log_position(
                    pos.stock_code,
                    pos.volume,
                    cost_price,
                    current_price,
                    market_value,
                    profit_loss,
                    profit_loss_pct
                )
        except Exception as e:
            logger.error(f"Error logging positions: {e}")
    
    def _get_current_price(self, stock_code):
        """
        Get current price for a stock or ETF
        
        Parameters:
        -----------
        stock_code : str
            Stock or ETF code
            
        Returns:
        --------
        float
            Current price
        """
        try:
            # Try to get price from QMT
            price = xt.get_last_price(stock_code)
            if price > 0:
                return price
            
            # If QMT price not available, try data fetcher
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
            
            if self.is_etf:
                df = self.data_fetcher.get_etf_data(
                    stock_code, 
                    yesterday, 
                    today, 
                    adjust="hfq"  # Use backward adjustment for real-time trading
                )
                logger.info(f"Using ETF data for price of {stock_code}")
            else:
                df = self.data_fetcher.get_stock_data(
                    stock_code, 
                    yesterday, 
                    today, 
                    adjust="hfq"  # Use backward adjustment for real-time trading
                )
            
            if not df.empty:
                return df['close'].iloc[-1]
            
            return 0
        except Exception as e:
            logger.error(f"Error getting current price for {stock_code}: {e}")
            return 0
    
    def run(self, universe=None, interval=60):
        """
        Run the trading strategy in real-time
        
        Parameters:
        -----------
        universe : list
            List of stock codes to trade (optional)
        interval : int
            Trading interval in seconds
        """
        if not self.is_connected:
            if not self.connect():
                logger.error("Cannot run trader - not connected")
                return
        
        # Set universe
        if universe:
            self.strategy.set_universe(universe)
        
        logger.info(f"Starting real-time trading with strategy: {self.strategy.name}")
        logger.info(f"Universe: {self.strategy.universe}")
        logger.info(f"Trading interval: {interval} seconds")
        
        try:
            while True:
                # Check if market is open
                if not self._is_market_open():
                    logger.info("Market is closed. Waiting...")
                    time.sleep(60)  # Check every minute
                    continue
                
                # Update positions
                self._update_positions()
                
                # Get current data
                current_date = datetime.datetime.now()
                current_data = self._get_current_data()
                
                # Execute strategy
                orders = self.strategy.handle_data(current_date, current_data)
                
                # Process orders
                if orders:
                    for order in orders:
                        self._place_order(order)
                
                # Wait for next iteration
                logger.info(f"Sleeping for {interval} seconds...")
                time.sleep(interval)
        
        except KeyboardInterrupt:
            logger.info("Trading stopped by user")
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")
        finally:
            self.disconnect()
    
    def _get_current_data(self):
        """
        Get current market data for the strategy universe
        
        Returns:
        --------
        dict
            Dictionary with current market data
        """
        current_data = {}
        
        for stock_code in self.strategy.universe:
            try:
                # Get current price
                price = self._get_current_price(stock_code)
                
                # Get historical data for calculation
                end_date = datetime.datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")
                
                if self.is_etf:
                    hist_data = self.data_fetcher.get_etf_data(
                        stock_code, 
                        start_date, 
                        end_date, 
                        adjust="hfq"  # Use backward adjustment for real-time trading
                    )
                    logger.info(f"Using ETF data for {stock_code}")
                else:
                    hist_data = self.data_fetcher.get_stock_data(
                        stock_code, 
                        start_date, 
                        end_date, 
                        adjust="hfq"  # Use backward adjustment for real-time trading
                    )
                
                # Basic data
                data = {
                    'close': price,
                    'open': price,  # Use last price as a proxy
                    'high': price,
                    'low': price,
                    'volume': 0,
                    'history': hist_data
                }
                
                current_data[stock_code] = data
            
            except Exception as e:
                logger.error(f"Error getting data for {stock_code}: {e}")
        
        return current_data
    
    def _place_order(self, order):
        """
        Place an order via QMT
        
        Parameters:
        -----------
        order : dict
            Order details
        
        Returns:
        --------
        str
            Order ID if successful, None otherwise
        """
        try:
            stock_code = order['stock_code']
            action = order['action']
            quantity = order['quantity']
            price = order.get('price', None)
            
            # Skip if quantity is zero
            if quantity <= 0:
                logger.warning(f"Skipping order with zero quantity: {order}")
                return None
            
            # Determine order type based on price
            if price is None:
                # Market order
                order_type = xt.PRICE_TYPE_LATEST
                price = self._get_current_price(stock_code)
            else:
                # Limit order
                order_type = xt.PRICE_TYPE_LIMIT
            
            # Create order
            if action == 'BUY':
                logger.info(f"Placing BUY order: {quantity} shares of {stock_code} at {price}")
                order_id = xt.order_stock(
                    self.account,
                    stock_code,
                    xt.ORDER_DIRECTION_BUY,
                    quantity,
                    order_type,
                    price
                )
            elif action == 'SELL':
                logger.info(f"Placing SELL order: {quantity} shares of {stock_code} at {price}")
                order_id = xt.order_stock(
                    self.account,
                    stock_code,
                    xt.ORDER_DIRECTION_SELL,
                    quantity,
                    order_type,
                    price
                )
            else:
                logger.error(f"Unknown order action: {action}")
                return None
            
            # Log order
            self.order_logger.log_order(
                stock_code,
                action,
                price,
                quantity,
                order_id,
                "SUBMITTED",
                ""
            )
            
            return order_id
        
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            
            # Log error
            if 'stock_code' in order and 'action' in order and 'quantity' in order:
                self.order_logger.log_order(
                    order['stock_code'],
                    order['action'],
                    order.get('price', 0),
                    order['quantity'],
                    "",
                    "ERROR",
                    str(e)
                )
            
            return None
    
    def _is_market_open(self):
        """
        Check if the market is currently open
        
        Returns:
        --------
        bool
            True if market is open, False otherwise
        """
        try:
            now = datetime.datetime.now()
            
            # Check if it's a weekend
            if now.weekday() >= 5:  # Saturday or Sunday
                return False
            
            # Check time (9:30 - 11:30, 13:00 - 15:00)
            hour, minute = now.hour, now.minute
            
            # Morning session
            if (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30):
                return True
            
            # Afternoon session
            if (hour >= 13 and hour < 15):
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def _on_order_callback(self, order):
        """
        Callback for order status updates
        
        Parameters:
        -----------
        order : OrderInfo
            Order information
        """
        try:
            logger.info(f"Order update: {order.stock_code}, Status: {order.status}, Filled: {order.filled_volume}/{order.order_volume}")
            
            # Log order update
            self.order_logger.log_order(
                order.stock_code,
                "BUY" if order.order_direction == xt.ORDER_DIRECTION_BUY else "SELL",
                order.price,
                order.order_volume,
                order.order_id,
                order.status,
                f"Filled: {order.filled_volume}/{order.order_volume}"
            )
            
            # Update positions if order is completed
            if order.status == xt.ORDER_STATUS_FILLED:
                self._update_positions()
        
        except Exception as e:
            logger.error(f"Error in order callback: {e}")
    
    def _on_trade_callback(self, trade):
        """
        Callback for trade execution
        
        Parameters:
        -----------
        trade : TradeInfo
            Trade information
        """
        try:
            logger.info(f"Trade executed: {trade.stock_code}, Price: {trade.price}, Volume: {trade.volume}")
            
            # Update positions
            self._update_positions()
        
        except Exception as e:
            logger.error(f"Error in trade callback: {e}")
    
    def _on_position_callback(self, position):
        """
        Callback for position updates
        
        Parameters:
        -----------
        position : PositionInfo
            Position information
        """
        try:
            logger.info(f"Position update: {position.stock_code}, Volume: {position.volume}")
            
            # Update strategy positions
            if position.volume > 0:
                self.strategy.positions[position.stock_code] = position.volume
            else:
                if position.stock_code in self.strategy.positions:
                    del self.strategy.positions[position.stock_code]
            
            # Log positions
            self._log_positions()
        
        except Exception as e:
            logger.error(f"Error in position callback: {e}")
    
    def _on_asset_callback(self, asset):
        """
        Callback for asset updates
        
        Parameters:
        -----------
        asset : AssetInfo
            Asset information
        """
        try:
            logger.info(f"Asset update: Cash: {asset.cash}, Total: {asset.total_asset}")
            
            # Update strategy cash
            self.strategy.cash = asset.cash
            self.strategy.portfolio_value = asset.total_asset
        
        except Exception as e:
            logger.error(f"Error in asset callback: {e}")


# Function to run real-time trading
def run_realtime(strategy, universe=None, account_id=None, interval=60, is_etf=False):
    """
    Run real-time trading with the given strategy
    
    Parameters:
    -----------
    strategy : BaseStrategy
        Strategy to use for trading
    universe : list
        List of stock or ETF codes to trade
    account_id : str
        Trading account ID
    interval : int
        Trading interval in seconds
    is_etf : bool
        Whether to trade ETFs (True) or stocks (False)
    """
    # Create trader
    trader = QMTTrader(strategy, account_id=account_id, is_etf=is_etf)
    
    # Connect to account
    if not trader.connect():
        logger.error("Failed to connect to trading account")
        return
    
    # Run the trader
    trader.run(universe=universe, interval=interval) 