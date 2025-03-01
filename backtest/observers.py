"""
Backtrader的观察者组件
"""

import backtrader as bt
import numpy as np

class ValueObserver(bt.Observer):
    """
    观察者，用于跟踪投资组合的每日净值
    """
    
    lines = ('value',)
    
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue() 