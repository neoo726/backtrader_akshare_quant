"""
Single Moving Average Strategy
"""
import pandas as pd
import numpy as np
from loguru import logger

from strategies.base_strategy import BaseStrategy
from config.config import MA_PERIOD

class MAStrategy(BaseStrategy):
    """
    Single Moving Average Strategy
    
    Strategy logic:
    - Buy when price crosses above the moving average
    - Sell when price crosses below the moving average
    """
    
    def __init__(self, name="MA Strategy", ma_period=None):
        """
        Initialize the MA strategy
        
        Parameters:
        -----------
        name : str
            Strategy name
        ma_period : int
            Moving average period (default is from config)
        """
        super().__init__(name=name)
        
        # Strategy parameters
        self.ma_period = ma_period if ma_period is not None else MA_PERIOD
        self.logger.info(f"Using moving average period: {self.ma_period}")
        
        # Previous MA values for crossover detection
        self.previous_ma = {}  # stock_code -> previous MA value
        self.previous_price = {}  # stock_code -> previous price
        
    def _strategy_logic(self):
        """
        Implement the single moving average strategy logic
        
        Returns:
        --------
        list
            List of order decisions
        """
        orders = []
        
        for stock_code in self.universe:
            # Skip if no data for this stock
            if stock_code not in self.current_data:
                continue
                
            # Get current price
            current_price = self.get_price(stock_code, 'close')
            if current_price == 0:
                continue
                
            # Get price history
            price_history = self.current_data[stock_code].get('history', None)
            if price_history is None or len(price_history) < self.ma_period:
                self.logger.debug(f"Not enough price history for {stock_code}")
                continue
                
            # Calculate moving average
            ma = price_history['close'].rolling(window=self.ma_period).mean().iloc[-1]
            
            # Get previous values for crossover detection
            prev_ma = self.previous_ma.get(stock_code, ma)
            prev_price = self.previous_price.get(stock_code, current_price)
            
            # Check for crossover
            current_crossover = current_price > ma
            previous_crossover = prev_price > prev_ma
            
            # Current position
            current_position = self.get_position(stock_code)
            
            # Buy signal: price crosses above MA
            if current_crossover and not previous_crossover and current_position == 0:
                # Calculate position size (10% of portfolio)
                position_value = self.portfolio_value * 0.1
                quantity = int(position_value / current_price)
                
                if quantity > 0 and position_value <= self.cash:
                    self.logger.info(f"BUY SIGNAL for {stock_code}: Price {current_price} crossed above MA {ma}")
                    orders.append(self.order(stock_code, quantity))
            
            # Sell signal: price crosses below MA
            elif not current_crossover and previous_crossover and current_position > 0:
                self.logger.info(f"SELL SIGNAL for {stock_code}: Price {current_price} crossed below MA {ma}")
                orders.append(self.order(stock_code, -current_position))
            
            # Update previous values for next iteration
            self.previous_ma[stock_code] = ma
            self.previous_price[stock_code] = current_price
        
        return orders 