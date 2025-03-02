# A股交易策略模板使用指南

本指南介绍如何使用新的交易策略模板，该模板基于backtrader框架，兼容回测和实盘交易，提供了结构化的策略开发方法。

## 策略模板结构

新的策略模板 (`strategies/strategy_template.py`) 具有以下特点：

1. **结构分层**
   - 参数区：通过`params`集中管理策略参数
   - 核心方法：规范化的策略执行流程（信号生成 → 风险检查 → 交易执行 → 日志记录）
   - 自定义区域：用户只需要实现特定的策略逻辑

2. **兼容性**
   - 同一套代码兼容回测和实盘
   - 通过`mode`参数切换运行模式
   - 自动适配不同数据源

3. **风险管理**
   - 内置风险控制机制，如涨跌停检查
   - 基于账户风险比例的仓位控制

## 使用方法

### 创建新策略

要创建新策略，只需从`BaseStrategy`继承并实现自己的信号生成逻辑：

```python
from strategies.strategy_template import BaseStrategy
import backtrader as bt

class MyStrategy(BaseStrategy):
    """自定义策略"""
    
    # 添加自定义参数（可选）
    params = (
        ('my_param', 10),  # 自定义参数
    )
    
    def __init__(self):
        """初始化策略"""
        # 调用父类初始化
        super(MyStrategy, self).__init__()
        
        # 添加自定义指标
        self.my_indicator = bt.indicators.RSI(self.data_close, period=self.params.my_param)
    
    def generate_signal(self):
        """实现信号生成逻辑"""
        signal = {'direction': 0, 'price': self.data_close[0], 'size': 0}
        
        # 示例：RSI超买超卖策略
        if self.my_indicator[0] < 30:  # 超卖
            signal['direction'] = 1  # 买入信号
            signal['size'] = self.calculate_position_size()
        elif self.my_indicator[0] > 70:  # 超买
            signal['direction'] = -1  # 卖出信号
            signal['size'] = self.position.size  # 全部卖出
            
        return signal
```

### 独立运行策略

每个策略文件都可以作为独立模块运行，包含了完整的回测逻辑：

```python
if __name__ == '__main__':
    import akshare as ak
    import pandas as pd
    import backtrader as bt
    
    # 创建backtrader实例
    cerebro = bt.Cerebro()
    
    # 使用akshare获取数据
    df = ak.stock_zh_a_hist(symbol='600519', period="daily", adjust="qfq")
    
    # 重命名列以匹配backtrader要求
    df = df.rename(columns={
        '日期': 'date',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
    })
    
    # 设置日期为索引
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # 创建数据源
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    # 添加策略
    cerebro.addstrategy(MyStrategy, mode='backtest', my_param=14)
    
    # 设置初始资金
    cerebro.broker.setcash(1000000.0)
    
    # 设置佣金
    cerebro.broker.setcommission(commission=0.0003)
    
    # 运行回测
    results = cerebro.run()
    
    # 绘制结果
    cerebro.plot()
```

### 使用主程序运行

系统的主程序也已更新，支持新的模板策略：

```bash
# 使用模板策略进行回测
python main.py backtest --universe 600000 --strategy sma_template --ma-period 20 --risk-ratio 0.02
```

## 内置策略示例

系统已经包含一个使用新模板的SMA策略示例：

- `strategies/sma_strategy.py`: 单一移动平均线策略，当价格上穿MA买入，下穿MA卖出

## 实盘交易注意事项

- 使用模板策略进行实盘交易时，确保设置`mode='live'`
- 实时日志会保存在`logs/trading_log.txt`
- 持仓记录会保存在`logs/position.csv`

## 与原系统的区别

新的模板策略与原系统的主要区别：

1. **框架集成**: 新模板直接集成backtrader框架，而原系统使用自定义的回测引擎
2. **信号生成**: 新模板使用标准化的信号格式，原系统使用特定的订单格式
3. **风险管理**: 新模板内置风险控制逻辑，原系统在回测引擎中实现

## 进一步开发

目前系统可以同时支持原始策略和新模板策略，您可以根据需要选择使用哪种方式。

未来将进一步增强模板策略的功能，包括：
-策略2.0优化：
- 最多同时持仓5个ETF，如果没有满足条件的可以空仓（如果已经持有仓位，则清仓）；
- 另外每个ETF最多持仓比例不能超过20%，按照计算得分排名，得分为正的ETF中，排名最高的持仓20%，其他符合条件的ETF按照各自得分与最高分的比值，再乘以20%来获得实际的持仓比例：
- 买卖操作时，先执行卖出操作，再执行买入操作
- 另外单个ETF持仓亏损达到5%时，减仓50%，亏损达到15%时，清仓。
