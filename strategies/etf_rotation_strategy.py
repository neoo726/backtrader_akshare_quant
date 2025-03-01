"""
ETF轮动策略

该策略基于动量和波动率在ETF之间进行轮动。
它选择具有最高动量（一段时间内的价格变化）
和最低波动率的ETF。
"""

import backtrader as bt
import numpy as np
import pandas as pd
from loguru import logger

# ETF轮动池
ETF_POOL = [
    '159915',  # 易方达创业板ETF
    '510300',  # 华泰柏瑞沪深300ETF
    '510500',  # 南方中证500ETF
    '512880',  # 国泰中证军工ETF
    '512660',  # 国泰中证军工ETF
    '512010',  # 国泰中证军工ETF
    '512800',  # 华宝中证银行ETF
    '512200',  # 南方中证全指证券公司ETF
    '512690',  # 鹏华中证酒ETF
    '512980',  # 广发中证传媒ETF
    '512760',  # 国泰CES半导体芯片ETF
    '512480',  # 国联安中证医药ETF
    '512330',  # 南方中证500信息技术ETF
    '512170',  # 华安中证细分医药ETF
    '515000',  # 华夏中证央企ETF
    '515030',  # 华夏中证新能源汽车ETF
    '515880',  # 国泰中证全指证券公司ETF
    '515050',  # 华夏中证5G通信主题ETF
    '515220',  # 华泰柏瑞中证光伏产业ETF
    '515790',  # 华泰柏瑞中证智能汽车ETF
    '516160',  # 南方中证申万有色金属ETF
    '516950',  # 华夏中证四川国企改革ETF
    '588080',  # 易方达中证科创创业50ETF
    '588090',  # 国泰中证新能源汽车ETF
    '588000',  # 华夏中证科创板50ETF
]

class ETFRotationStrategy(bt.Strategy):
    """
    ETF轮动策略
    
    该策略基于动量和波动率在ETF之间进行轮动。
    它选择具有最高动量（一段时间内的价格变化）
    和最低波动率的ETF。
    """
    
    params = (
        ('short_period', 20),      # 短期动量周期
        ('long_period', 60),       # 长期动量周期
        ('max_volatility', 0.3),   # 最大允许波动率
        ('top_n', 3),              # 持有ETF数量
        ('rebalance_days', 5),     # 每N天再平衡一次
        ('benchmark', False),      # 最后一个数据源是否为基准
    )
    
    def __init__(self):
        """
        初始化策略
        """
        # 初始化变量
        self.order_dict = {}  # 用于跟踪订单
        self.current_holdings = {}  # 当前持仓
        self.day_count = 0  # 再平衡计数器
        
        # 为每个数据源计算动量和波动率
        self.momentum = {}
        self.volatility = {}
        
        for i, d in enumerate(self.datas):
            # 如果最后一个数据源是基准，则跳过
            if i == len(self.datas) - 1 and self.p.benchmark:
                continue
                
            # 使用短期和长期移动平均线计算动量
            self.momentum[d._name] = bt.indicators.ROC(
                d, period=self.p.short_period, plot=False
            )
            
            # 使用标准差计算波动率
            self.volatility[d._name] = bt.indicators.StdDev(
                d.close, period=self.p.long_period, plot=False
            ) / d.close
    
    def next(self):
        """
        主策略逻辑，每个K线调用一次
        """
        # 增加天数计数器
        self.day_count += 1
        
        # 只在指定天数进行再平衡
        if self.day_count % self.p.rebalance_days != 0:
            return
            
        # 获取当前投资组合价值
        portfolio_value = self.broker.getvalue()
        
        # 计算每个ETF的动量和波动率得分
        scores = {}
        for i, d in enumerate(self.datas):
            # 如果最后一个数据源是基准，则跳过
            if i == len(self.datas) - 1 and hasattr(self.p, 'benchmark') and self.p.benchmark:
                continue
                
            # 获取动量和波动率值
            momentum_value = self.momentum[d._name][0]
            volatility_value = self.volatility[d._name][0]
            
            # 如果数据不足或波动率过高则跳过
            if np.isnan(momentum_value) or np.isnan(volatility_value):
                continue
                
            if volatility_value > self.p.max_volatility:
                continue
                
            # 计算得分（更高的动量，更低的波动率更好）
            scores[d._name] = momentum_value / (volatility_value + 0.0001)  # 避免除以零
        
        # 按得分排序ETF并选择前N个
        sorted_etfs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_etfs = [etf for etf, score in sorted_etfs[:self.p.top_n]]
        
        # 记录选中的ETF
        if top_etfs:
            logger.info(f"选中的ETF: {', '.join(top_etfs)}")
        else:
            logger.warning("根据条件未选中任何ETF")
            return
            
        # 关闭不在前列表中的ETF持仓
        for etf in list(self.current_holdings.keys()):
            if etf not in top_etfs:
                self.close(data=self.getdatabyname(etf))
                logger.info(f"关闭{etf}的持仓")
                if etf in self.current_holdings:
                    del self.current_holdings[etf]
        
        # 计算每个选中ETF的持仓规模
        position_size = portfolio_value / len(top_etfs) if top_etfs else 0
        
        # 为顶级ETF开设或调整持仓
        for etf in top_etfs:
            data = self.getdatabyname(etf)
            
            # 计算要买入的股票数量
            price = data.close[0]
            target_shares = int(position_size / price)
            
            # 获取当前持仓
            current_position = self.getposition(data).size
            
            # 根据需要调整持仓
            if target_shares > current_position:
                # 买入更多股票
                shares_to_buy = target_shares - current_position
                self.buy(data=data, size=shares_to_buy)
                logger.info(f"买入{shares_to_buy}股{etf}")
                self.current_holdings[etf] = target_shares
            elif target_shares < current_position:
                # 卖出一些股票
                shares_to_sell = current_position - target_shares
                self.sell(data=data, size=shares_to_sell)
                logger.info(f"卖出{shares_to_sell}股{etf}")
                if target_shares > 0:
                    self.current_holdings[etf] = target_shares
                else:
                    if etf in self.current_holdings:
                        del self.current_holdings[etf]
    
    def notify_order(self, order):
        """
        订单成交或拒绝时调用
        """
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(
                    f"买入执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 成本: {order.executed.value:.2f}, "
                    f"佣金: {order.executed.comm:.2f}"
                )
            else:
                logger.info(
                    f"卖出执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 成本: {order.executed.value:.2f}, "
                    f"佣金: {order.executed.comm:.2f}"
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"订单取消/保证金不足/拒绝: {order.status}")
    
    def notify_trade(self, trade):
        """
        交易完成时调用
        """
        if trade.isclosed:
            logger.info(
                f"交易完成: {trade.data._name}, 毛利: {trade.pnl:.2f}, "
                f"净利: {trade.pnlcomm:.2f}"
            )
    
    def stop(self):
        """
        策略停止时调用
        """
        # 计算最终投资组合价值
        portfolio_value = self.broker.getvalue()
        initial_value = self.broker.startingcash
        
        # 计算回报率
        returns = (portfolio_value / initial_value - 1) * 100
        
        logger.info(f"最终投资组合价值: {portfolio_value:.2f}")
        logger.info(f"回报率: {returns:.2f}%") 