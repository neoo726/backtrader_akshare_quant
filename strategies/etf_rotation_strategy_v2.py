"""
ETF轮动策略V3.0
该策略基于动量和波动率在ETF之间进行轮动。
它选择具有最高动量（一段时间内的价格变化）
和最低波动率的ETF。
20250302：
更新轮动池，增加科技与高端制造、周期与资源、消费与医药、战略新兴ETF

更新3.0：
1. 最多同时持仓5个ETF，如果没有满足条件的则空仓
2. 每个ETF最多持仓比例不能超过20%，得分最高的持仓20%
3. 其他ETF持仓比例 = (得分/最高分) * 20%
4. 执行顺序：先卖出，再买入
5. 短期和长期收益率均为负值的ETF不纳入计算
"""

import backtrader as bt
import numpy as np
import pandas as pd
from loguru import logger
from config.config import DEFAULT_BACKTEST_START, DEFAULT_BACKTEST_END

# ETF轮动池
ETF_POOL = [
    # 宽基指数
    '510300',  # 华泰柏瑞沪深300ETF
    '510500',  # 南方中证500ETF
    '159915',  # 易方达创业板ETF
    # 科技与高端制造
    '512760',  # 国泰CES半导体芯片ETF
    '515050',  # 华夏中证5G通信主题ETF
    '515790',  # 华泰柏瑞中证光伏产业ETF
    '588000',  # 华夏中证科创创业50ETF
    '515030',  # 华夏中证新能源汽车ETF（新增）
    # 周期与资源
    '512880',  # 国泰中证全指证券公司ETF
    '512400',  # 南方中证申万有色金属ETF
    '561700',  # 国泰中证全指电力ETF
    # 消费与医药
    '512690',  # 鹏华中证酒ETF
    '512480',  # 国联安中证医药ETF
    '517090',  # 华泰柏瑞中证港股通医疗ETF
    # 战略新兴
    '516510',  # 易方达中证人工智能ETF
]


class ETFRotationStrategy2(bt.Strategy):
    """
    ETF轮动策略 3.0
    
    该策略基于动量和波动率在ETF之间进行轮动。
    1. 最多同时持仓5个ETF，如果没有满足条件的则空仓
    2. 每个ETF最多持仓比例不能超过20%，得分最高的持仓20%
    3. 其他ETF持仓比例 = (得分/最高分) * 20%
    4. 执行顺序：先卖出，再买入
    5. 短期和长期收益率均为负值的ETF不纳入计算
    """
    
    params = (
        ('short_period', 10),      # 短期动量周期
        ('long_period', 30),       # 长期动量周期
        ('volume_weight', 0.3),    # 成交量在动量计算中的权重
        ('max_etfs', 5),           # 最大持有ETF数量
        ('rebalance_days', 5),     # 每N天再平衡一次
        ('benchmark', False),      # 最后一个数据源是否为基准
        ('position_limit', 0.20),  # 单ETF持仓上限
        ('start_date', pd.to_datetime(DEFAULT_BACKTEST_START).date()),  # 默认开始日期
        ('end_date', pd.to_datetime(DEFAULT_BACKTEST_END).date()),      # 默认结束日期
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
        self.short_momentum = {}
        self.long_momentum = {}
        self.volatility = {}
        self.volume = {}
        
        for i, d in enumerate(self.datas):
            # 如果最后一个数据源是基准，则跳过
            if i == len(self.datas) - 1 and self.p.benchmark:
                continue
                
            # 计算短期和长期动量
            self.short_momentum[d._name] = bt.indicators.ROC(
                d, period=self.p.short_period, plot=False
            )
            
            self.long_momentum[d._name] = bt.indicators.ROC(
                d, period=self.p.long_period, plot=False
            )
            
            # 使用标准差计算波动率
            self.volatility[d._name] = bt.indicators.StdDev(
                d.close, period=self.p.long_period, plot=False
            ) / d.close
            
            # 计算成交量变化
            self.volume[d._name] = bt.indicators.ROC(
                d.volume, period=self.p.short_period, plot=False
            )
        
        self._value_history = []  # 添加净值记录器
    
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
            if i == len(self.datas) - 1 and self.p.benchmark:
                continue
                
            # 获取短期和长期动量值
            short_momentum_value = self.short_momentum[d._name][0]
            long_momentum_value = self.long_momentum[d._name][0]
            volatility_value = self.volatility[d._name][0]
            volume_change = self.volume[d._name][0]
            
            # 如果数据不足则跳过
            if (np.isnan(short_momentum_value) or np.isnan(long_momentum_value) or 
                np.isnan(volatility_value) or np.isnan(volume_change)):
                continue
                
            # 如果短期和长期动量均为负，则排除该ETF
            if short_momentum_value < 0 and long_momentum_value < 0:
                logger.info(f"{d._name} 短期和长期动量均为负，排除")
                continue
                
            # 计算价格和成交量加权的动量值
            price_weight = 1 - self.p.volume_weight
            weighted_momentum = (price_weight * short_momentum_value + 
                                self.p.volume_weight * volume_change)
            
            # 计算风险调整后的动量得分（更高的动量，更低的波动率更好）
            # 避免除以零
            if volatility_value <= 0:
                volatility_value = 0.0001
                
            score = weighted_momentum / volatility_value
            
            # 只有得分为正的ETF才纳入考虑
            if score > 0:
                scores[d._name] = score
        
        # 按得分排序ETF并选择前N个
        sorted_etfs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_etfs = sorted_etfs[:self.p.max_etfs]  # 最多选择5个
        
        # 记录选中的ETF
        if top_etfs:
            logger.info(f"选中的ETF: {', '.join([etf for etf, _ in top_etfs])}")
            logger.info(f"得分: {', '.join([f'{etf}: {score:.4f}' for etf, score in top_etfs])}")
        else:
            logger.warning("根据条件未选中任何ETF，将保持空仓")
            
        # 第一阶段：执行所有卖出操作
        
        # 如果没有符合条件的ETF或持仓ETF不在选中列表中，则清空持仓
        for etf in list(self.current_holdings.keys()):
            if not top_etfs or etf not in [e for e, _ in top_etfs]:
                data = self.getdatabyname(etf)
                if data:
                    position = self.getposition(data).size
                    if position > 0:
                        self.close(data=data)
                        logger.info(f"关闭{etf}的持仓")
                del self.current_holdings[etf]
        
        # 如果没有选中的ETF，直接返回（保持空仓）
        if not top_etfs:
            return
        
        # 获取最高得分作为基准
        highest_score = top_etfs[0][1]
        
        # 计算持仓比例字典
        target_weights = {}
        for etf, score in top_etfs:
            # 得分最高的ETF占20%
            if score == highest_score:
                target_weights[etf] = self.p.position_limit
            else:
                # 其他ETF按照 (得分/最高分) * 20% 计算
                weight = (score / highest_score) * self.p.position_limit
                target_weights[etf] = weight
                
        # 记录目标持仓比例
        logger.info(f"目标持仓比例: {', '.join([f'{etf}: {weight:.2%}' for etf, weight in target_weights.items()])}")
        
        # 2. 减少需要减仓的ETF持仓
        for etf, target_weight in target_weights.items():
            data = self.getdatabyname(etf)
            
            # 计算目标持仓规模
            position_size = portfolio_value * target_weight
            
            # 计算目标股数
            price = data.close[0]
            if price <= 0:
                logger.error(f"无效价格: {etf} 价格={price}")
                continue
                
            target_shares = int(position_size / price)
            
            # 获取当前持仓
            current_position = self.getposition(data).size
            
            # 如果需要减少持仓，先执行卖出操作
            if target_shares < current_position:
                # 卖出一些股票
                shares_to_sell = current_position - target_shares
                self.sell(data=data, size=shares_to_sell)
                logger.info(f"卖出{shares_to_sell}股{etf}，目标持仓比例: {target_weight:.2%}")
                if target_shares > 0:
                    self.current_holdings[etf] = target_shares
                else:
                    if etf in self.current_holdings:
                        del self.current_holdings[etf]
        
        # 更新当前投资组合价值（卖出操作后）
        portfolio_value = self.broker.getvalue()
            
        # 第二阶段：执行所有买入操作
        for etf, target_weight in target_weights.items():
            data = self.getdatabyname(etf)
            
            # 计算目标持仓规模
            position_size = portfolio_value * target_weight
            
            # 计算目标股数
            price = data.close[0]
            if price <= 0:
                logger.error(f"无效价格: {etf} 价格={price}")
                continue
                
            target_shares = int(position_size / price)
            
            # 获取当前持仓
            current_position = self.getposition(data).size
            
            # 如果需要增加持仓，执行买入操作
            if target_shares > current_position:
                # 买入更多股票
                shares_to_buy = target_shares - current_position
                self.buy(data=data, size=shares_to_buy)
                logger.info(f"买入{shares_to_buy}股{etf}，目标持仓比例: {target_weight:.2%}")
                self.current_holdings[etf] = target_shares
        
        # 只记录在回测时间段内的数据
        current_date = self.data.datetime.date(0)
        
        # 添加空值检查
        if (self.p.start_date is not None and 
            self.p.end_date is not None and 
            self.p.start_date <= current_date <= self.p.end_date):
            
            self._value_history.append((
                current_date,
                self.broker.getvalue()
            ))
    
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