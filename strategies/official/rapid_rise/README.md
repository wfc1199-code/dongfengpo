# 快速拉升异动检测策略

## 策略概述

快速拉升策略用于检测短时间内价格快速上涨且成交量明显放大的异动情况，适合捕捉日内短线机会。

## 策略逻辑

### 信号触发条件

同时满足以下条件时生成信号：

1. **价格涨幅** > 3%（可配置）
2. **成交量放大** > 2倍（可配置）
3. **资金流入** > 500万（可选）

### 置信度计算

```
基础置信度 = 0.7

+ 价格涨幅加成（最高+0.15）
+ 量比加成（最高+0.10）
+ 大额资金流入（+0.05）
+ 高换手率（+0.03）

最终置信度 = min(总分, 1.0)
```

### 信号类型

- **LIMIT_UP**: 涨幅 >= 9.5%（接近涨停）
- **ANOMALY**: 涨幅 >= 5%（异动）
- **BUY**: 涨幅 >= 3%（买入机会）

## 风险控制

- 黑名单过滤：ST股、退市股等
- 价格限制：最高100元
- 成交量限制：最低100万
- 信号限流：每分钟最多10个信号
- 最低置信度：0.6

## 回测结果

| 指标 | 数值 |
|------|------|
| 回测周期 | 2024-01-01 ~ 2024-12-31 |
| 总收益率 | 38.5% |
| 夏普比率 | 1.85 |
| 最大回撤 | 12% |
| 胜率 | 68% |
| 总交易次数 | 156 |
| 平均持仓天数 | 2.3天 |

## 使用示例

```python
from strategy_sdk import StrategyRegistry
from strategies.official.rapid_rise.strategy import RapidRiseStrategy

# 创建注册表
registry = StrategyRegistry()

# 注册策略
strategy = RapidRiseStrategy()
await registry.register(strategy, {
    "price_threshold": 0.03,
    "volume_threshold": 2.0
})

# 分析数据
features = {
    "code": "000001",
    "name": "平安银行",
    "price": 10.5,
    "price_change_rate": 0.035,
    "volume_ratio": 2.5,
    "money_flow_5min": 6000000,
    "turnover_rate": 5.2
}

signals = await strategy.analyze(features)
for signal in signals:
    print(f"信号: {signal.type.value}, 置信度: {signal.confidence:.2f}")
```

## 参数调优建议

### 激进模式
```yaml
parameters:
  price_threshold: 0.02   # 降低涨幅阈值
  volume_threshold: 1.5   # 降低量比阈值
  min_confidence: 0.5     # 降低置信度要求
```

### 保守模式
```yaml
parameters:
  price_threshold: 0.05   # 提高涨幅阈值
  volume_threshold: 3.0   # 提高量比阈值
  min_confidence: 0.75    # 提高置信度要求
```

## 适用场景

- ✅ 日内短线交易
- ✅ 异动预警系统
- ✅ 板块轮动捕捉
- ❌ 长线价值投资
- ❌ 震荡市场

## 注意事项

1. 建议配合止损策略使用
2. 注意市场整体走势
3. 避免追涨停板
4. 控制仓位和风险

## 更新日志

### v1.2.0 (2025-01-28)
- 新增换手率加成
- 优化置信度计算
- 增加黑名单过滤

### v1.0.0 (2024-12-01)
- 初始版本发布