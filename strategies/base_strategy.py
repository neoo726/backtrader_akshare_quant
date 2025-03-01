"""
Base strategy class for the trading system
"""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from loguru import logger

class BaseStrategy(ABC):
    """
    Base strategy class to be inherited by all trading strategies
    
    This class implements common functionality and defines the interface
    for strategies to be used in both backtesting and real-time trading.
    """
    
    def __init__(self, name="BaseStrategy"):
        """
        Initialize the strategy
        
        Parameters:
        -----------
        name : str
            Name of the strategy
        """
        self.name = name
        self.logger = logger.bind(strategy=name)
        self.logger.info(f"Initializing strategy: {name}")
        
        # Current positions and portfolio state
        self.positions = {}  # stock_code -> quantity
        self.portfolio_value = 0.0
        self.cash = 0.0
        self.initial_capital = 0.0
        
        # Internal state variables
        self.current_date = None
        self.current_data = {}  # stock_code -> price data
        self.universe = []  # List of stock codes
        
    def set_universe(self, universe):
        """
        Set the universe of stocks for this strategy
        
        Parameters:
        -----------
        universe : list
            List of stock codes
        """
        self.universe = universe
        self.logger.info(f"Set universe with {len(universe)} stocks")
        
    def set_initial_capital(self, capital):
        """
        Set the initial capital for the strategy
        
        Parameters:
        -----------
        capital : float
            Initial capital
        """
        self.initial_capital = capital
        self.cash = capital
        self.logger.info(f"Set initial capital to {capital}")
        
    def update_portfolio_value(self):
        """
        Update the portfolio value based on current positions and prices
        """
        portfolio_value = self.cash
        
        for stock_code, quantity in self.positions.items():
            if stock_code in self.current_data:
                price = self.current_data[stock_code].get('close', 0)
                portfolio_value += price * quantity
        
        self.portfolio_value = portfolio_value
        return portfolio_value
        
    def handle_data(self, current_date, current_data):
        """
        Handle new data and execute strategy logic
        
        Parameters:
        -----------
        current_date : datetime.datetime
            Current date
        current_data : dict
            Dictionary mapping stock codes to price data
            
        Returns:
        --------
        list
            List of order decisions
        """
        self.current_date = current_date
        self.current_data = current_data
        
        # Update portfolio value
        self.update_portfolio_value()
        
        # Call the strategy-specific implementation
        return self._strategy_logic()
    
    @abstractmethod
    def _strategy_logic(self):
        """
        Implement the strategy logic
        
        This method should be implemented by each specific strategy.
        
        Returns:
        --------
        list
            List of order decisions, where each order is a dict with keys:
            - 'stock_code': str
            - 'action': 'BUY' or 'SELL'
            - 'quantity': int
            - 'price': float (optional, market order if not provided)
            - 'order_type': str (optional, default is 'MARKET')
        """
        pass
    
    def get_position(self, stock_code):
        """
        Get current position for a stock
        
        Parameters:
        -----------
        stock_code : str
            Stock code
            
        Returns:
        --------
        int
            Current position quantity (0 if not held)
        """
        return self.positions.get(stock_code, 0)
    
    def get_price(self, stock_code, field='close'):
        """
        Get current price for a stock
        
        Parameters:
        -----------
        stock_code : str
            Stock code
        field : str
            Price field: 'open', 'high', 'low', 'close'
            
        Returns:
        --------
        float
            Current price (0 if not available)
        """
        if stock_code in self.current_data:
            return self.current_data[stock_code].get(field, 0)
        return 0
    
    def calculate_ma(self, stock_code, period, field='close'):
        """
        Calculate moving average for a stock
        
        Parameters:
        -----------
        stock_code : str
            Stock code
        period : int
            Moving average period
        field : str
            Price field to use
            
        Returns:
        --------
        float
            Moving average value (or None if not enough data)
        """
        if stock_code not in self.current_data:
            return None
        
        price_history = self.current_data[stock_code].get('history', None)
        
        if price_history is None or len(price_history) < period:
            return None
        
        ma = price_history[field].rolling(window=period).mean().iloc[-1]
        return ma
    
    def order(self, stock_code, quantity, price=None, order_type="MARKET"):
        """
        Place an order (for backtesting)
        
        Parameters:
        -----------
        stock_code : str
            Stock code
        quantity : int
            Quantity to buy (positive) or sell (negative)
        price : float
            Limit price (optional)
        order_type : str
            Order type: 'MARKET' or 'LIMIT'
            
        Returns:
        --------
        dict
            Order details
        """
        action = "BUY" if quantity > 0 else "SELL"
        abs_quantity = abs(quantity)
        
        order_details = {
            'stock_code': stock_code,
            'action': action,
            'quantity': abs_quantity,
            'price': price,
            'order_type': order_type
        }
        
        self.logger.info(f"Generated order: {action} {abs_quantity} shares of {stock_code}")
        return order_details
    
    def update_position(self, stock_code, quantity_change, price):
        """
        Update position after an order is executed
        
        Parameters:
        -----------
        stock_code : str
            Stock code
        quantity_change : int
            Change in quantity (positive for buy, negative for sell)
        price : float
            Execution price
        """
        current_position = self.positions.get(stock_code, 0)
        new_position = current_position + quantity_change
        
        # Update cash
        self.cash -= quantity_change * price
        
        # Update position
        if new_position == 0:
            # If position is closed, remove it from positions
            if stock_code in self.positions:
                del self.positions[stock_code]
        else:
            self.positions[stock_code] = new_position
            
        self.logger.info(f"Updated position for {stock_code}: {current_position} -> {new_position}")
        self.logger.info(f"Cash balance: {self.cash}")
        
        # Update portfolio value
        self.update_portfolio_value()
    
    def get_info(self):
        """
        Get strategy information and current state
        
        Returns:
        --------
        dict
            Strategy information
        """
        return {
            'name': self.name,
            'portfolio_value': self.portfolio_value,
            'cash': self.cash,
            'positions': self.positions,
            'current_date': self.current_date
        } 