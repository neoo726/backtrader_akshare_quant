# CyberTrader 量化交易系统

CyberTrader是一个基于Python的量化交易系统，支持多种交易策略的回测和实盘交易。目前实现了简单移动平均线策略和ETF轮动策略。

## 功能特点

- 支持股票和ETF的历史数据获取和回测
- 内置多种交易策略模板
- 提供详细的回测统计指标，包括收益率、夏普比率、最大回撤等
- 支持与基准指数的对比分析
- 提供可视化的回测结果展示

## 安装依赖

### 环境要求

- Python 3.8+
- pip 包管理工具

### 安装步骤

1. 克隆代码库到本地

```bash
git clone https://github.com/yourusername/cyber_trader.git
cd cyber_trader
```

2. 安装依赖包

```bash
pip install -r requirements.txt
```

## 系统结构

```
cyber_trader/
├── config/                 # 配置文件目录
│   └── config.py           # 系统配置
├── strategies/             # 策略目录
│   ├── strategy_template.py # 策略模板
│   ├── sma_strategy.py     # 简单移动平均线策略
│   └── etf_rotation_strategy.py # ETF轮动策略
├── utils/                  # 工具函数目录
│   ├── data_fetcher.py     # 数据获取工具
│   └── logger.py           # 日志工具
├── main.py                 # 主程序
├── run_strategy.py         # 策略运行工具
├── etf_rotation_backtest.py # ETF轮动策略回测脚本
└── requirements.txt        # 依赖包列表
```

## 使用方法

### 运行简单移动平均线策略回测

```bash
python run_strategy.py --strategy sma --symbol 600519 --ma-period 20 --start-date 2020-01-01 --end-date 2023-12-31
```

参数说明：
- `--strategy sma`: 选择简单移动平均线策略
- `--symbol`: 股票代码，如600519（贵州茅台）
- `--ma-period`: 移动平均线周期，默认为20天
- `--is-etf`: 如果是ETF，添加此参数
- `--start-date`: 回测开始日期，格式为YYYY-MM-DD
- `--end-date`: 回测结束日期，格式为YYYY-MM-DD
- `--benchmark`: 基准指数代码，默认为000300（沪深300）
- `--initial-cash`: 初始资金，默认为1000000（100万）

### 运行ETF轮动策略回测

```bash
python run_strategy.py --strategy etf_rotation --start-date 2018-01-01 --end-date 2024-06-30 --lookback-period 20 --rebalance-freq 5
```

参数说明：
- `--strategy etf_rotation`: 选择ETF轮动策略
- `--lookback-period`: 回看周期，用于计算ETF收益率，默认为20天
- `--rebalance-freq`: 再平衡频率，每隔多少天重新评估ETF排名，默认为5天
- `--start-date`: 回测开始日期，格式为YYYY-MM-DD
- `--end-date`: 回测结束日期，格式为YYYY-MM-DD
- `--benchmark`: 基准指数代码，默认为000300（沪深300）
- `--initial-cash`: 初始资金，默认为1000000（100万）

## ETF轮动策略说明

ETF轮动策略是一种动态资产配置策略，通过定期评估ETF的表现，将资金配置到表现最好的ETF上。具体规则如下：

1. 定义ETF池，包含多种不同类型的ETF
2. 每隔一定时间（如5个交易日）评估ETF池中各ETF过去一段时间（如20个交易日）的收益率
3. 根据收益率对ETF进行排名
4. 将资金按照预定比例分配给排名靠前的ETF：
   - 排名第1的ETF：40%的资金
   - 排名第2的ETF：30%的资金
   - 排名第3的ETF：20%的资金
   - 其余ETF：不持有
5. 在下一个评估日重复上述过程，调整持仓

该策略的优势在于能够自动追踪市场热点，将资金配置到表现较好的板块，同时通过分散投资降低风险。

## 简单移动平均线策略说明

简单移动平均线策略是一种经典的趋势跟踪策略，通过比较价格与移动平均线的关系来生成交易信号：

1. 当价格从下方突破移动平均线时，产生买入信号
2. 当价格从上方跌破移动平均线时，产生卖出信号

该策略适用于有明显趋势的市场，在震荡市场中可能会产生较多的假信号。

## 回测结果说明

回测结果包含以下指标：

- 总收益率：策略在回测期间的总收益率
- 年化收益率：将总收益率转换为年化收益率
- 夏普比率：策略的风险调整后收益
- 最大回撤：策略在回测期间的最大亏损幅度
- 总交易次数：策略在回测期间的交易次数
- 胜率：盈利交易占总交易的比例
- 基准对比：策略与基准指数的收益率对比
- 年度收益：策略在各年度的收益率

## 注意事项

1. 本系统仅供学习和研究使用，不构成投资建议
2. 回测结果不代表未来表现
3. 在实盘交易前，请充分了解策略的风险和特点
4. 使用前请确保已安装所有依赖包

## 贡献指南

欢迎贡献代码或提出建议，请通过以下方式参与：

1. Fork 本仓库
2. 创建新的分支 (`git checkout -b feature/your-feature`)
3. 提交更改 (`git commit -m 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

python main.py --backtest --strategy etf_rotation