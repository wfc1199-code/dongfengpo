# 东风破策略插件SDK

## 简介

用于开发东风破交易策略的Python SDK。

## 安装

```bash
pip install -e libs/strategy-sdk
```

## 快速开始

### 1. 创建策略

```python
# strategies/my_strategy/strategy.py

from strategy_sdk import BaseStrategy, Signal, SignalType
from datetime import datetime

class RapidRiseStrategy(BaseStrategy):
    """快速拉升策略"""

    name = "rapid_rise"
    version = "1.0.0"
    author = "your_name"
    description = "检测快速拉升异动"

    required_features = [
        "price_change_rate",
        "volume_ratio",
        "money_flow_5min"
    ]

    default_parameters = {
        "price_threshold": 0.03,
        "volume_threshold": 2.0
    }

    async def initialize(self, config: dict):
        """初始化策略参数"""
        self.price_threshold = config.get('price_threshold', 0.03)
        self.volume_threshold = config.get('volume_threshold', 2.0)
        print(f"RapidRiseStrategy initialized: threshold={self.price_threshold}")

    async def analyze(self, features: dict) -> list[Signal]:
        """分析特征并生成信号"""
        signals = []

        # 检查必要特征
        if not self.validate_features(features):
            return signals

        # 策略逻辑
        price_change = features['price_change_rate']
        volume_ratio = features['volume_ratio']

        if price_change > self.price_threshold and volume_ratio > self.volume_threshold:
            # 生成信号
            confidence = min(
                (price_change / self.price_threshold) * 0.5 +
                (volume_ratio / self.volume_threshold) * 0.3,
                1.0
            )

            signals.append(Signal(
                type=SignalType.ANOMALY,
                stock_code=features['code'],
                stock_name=features['name'],
                confidence=confidence,
                timestamp=int(datetime.now().timestamp()),
                reason=f"快速拉升: 涨幅{price_change*100:.2f}%, 量比{volume_ratio:.2f}",
                metadata={
                    "price_change_rate": price_change,
                    "volume_ratio": volume_ratio,
                    "money_flow": features['money_flow_5min']
                }
            ))

        return signals

    async def on_market_open(self):
        """开盘回调"""
        print(f"[{self.name}] 市场开盘，策略开始运行")

    async def on_market_close(self):
        """收盘回调"""
        print(f"[{self.name}] 市场收盘，策略停止运行")
```

### 2. 创建配置文件

```yaml
# strategies/my_strategy/strategy.yaml

name: rapid_rise
version: 1.0.0
author: your_name
description: 检测快速拉升异动

dependencies:
  - price_change_rate
  - volume_ratio
  - money_flow_5min

parameters:
  price_threshold: 0.03
  volume_threshold: 2.0
  time_window: 300

risk_controls:
  max_signals_per_minute: 10
  min_confidence: 0.6

backtest:
  start_date: 2024-01-01
  end_date: 2024-12-31
```

### 3. 使用装饰器

```python
from strategy_sdk import BaseStrategy, strategy

@strategy(
    name="my_strategy",
    version="1.0.0",
    author="john",
    description="我的策略"
)
class MyStrategy(BaseStrategy):
    async def initialize(self, config):
        pass

    async def analyze(self, features):
        return []
```

## API文档

### BaseStrategy

策略基类，所有策略必须继承此类。

#### 必须实现的方法

- `initialize(config: Dict)` - 初始化策略
- `analyze(features: Dict) -> List[Signal]` - 分析并生成信号

#### 可选实现的方法

- `on_market_open()` - 开盘回调
- `on_market_close()` - 收盘回调
- `on_feature_update(feature_name, value)` - 特征更新回调

#### 属性

- `name: str` - 策略名称
- `version: str` - 版本号
- `author: str` - 作者
- `description: str` - 描述
- `required_features: List[str]` - 依赖特征
- `default_parameters: Dict` - 默认参数

### Signal

信号数据类。

#### 字段

- `type: SignalType` - 信号类型
- `stock_code: str` - 股票代码
- `stock_name: str` - 股票名称
- `confidence: float` - 置信度（0-1）
- `timestamp: int` - 时间戳
- `reason: str` - 原因说明
- `metadata: Dict` - 额外元数据

### SignalType

信号类型枚举。

- `BUY` - 买入
- `SELL` - 卖出
- `HOLD` - 持有
- `ANOMALY` - 异动
- `WARNING` - 警告
- `LIMIT_UP` - 涨停

## 示例策略

### 涨停预测策略

```python
class LimitUpPredictor(BaseStrategy):
    name = "limit_up_predictor"
    version = "1.0.0"

    async def analyze(self, features):
        if features['price_change_rate'] > 0.095:
            return [Signal(
                type=SignalType.LIMIT_UP,
                stock_code=features['code'],
                confidence=0.9,
                reason="接近涨停"
            )]
        return []
```

### 资金流向策略

```python
class MoneyFlowStrategy(BaseStrategy):
    name = "money_flow"
    version = "1.0.0"

    async def analyze(self, features):
        if features['money_flow_5min'] > 10000000:
            return [Signal(
                type=SignalType.BUY,
                stock_code=features['code'],
                confidence=0.75,
                reason="大额资金流入"
            )]
        return []
```

## 最佳实践

1. **参数化配置**: 所有阈值都应通过配置文件设置
2. **特征验证**: 使用 `validate_features()` 检查必要特征
3. **置信度计算**: 合理设置信号置信度（0-1）
4. **错误处理**: 捕获异常并记录日志
5. **回测验证**: 新策略必须通过回测验证

## 贡献策略

1. Fork项目
2. 在 `strategies/community/` 创建策略目录
3. 实现策略并添加回测报告
4. 提交Pull Request

## License

MIT