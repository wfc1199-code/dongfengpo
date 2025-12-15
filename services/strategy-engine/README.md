# strategy-engine

策略执行服务：
- 订阅 `dfp:features` 特征频道，加载策略插件计算信号。
- 支持通过配置启用/禁用策略，输出信号到 `dfp:strategy_signals`。
- 提供基础插件框架，可扩展规则策略与模型策略。

## 配置

- 环境变量前缀 `STRATEGY_ENGINE_`
- `REDIS_URL`：Redis 连接串。
- `FEATURE_CHANNEL`：订阅的特征频道 (默认 `dfp:features`)
- `SIGNAL_STREAM`：策略信号输出 Stream
- `STRATEGIES`：策略列表，可使用 JSON 指定，例如：

```json
[
  {
    "name": "rapid-rise",
    "module": "strategy_engine.strategies.rapid_rise",
    "class_name": "RapidRiseStrategy",
    "parameters": {"min_change": 2.0, "min_volume": 30000}
  }
]
```

若未配置，将默认启用 `RapidRiseStrategy`。

## 运行

```bash
pip install -r requirements.txt
python -m strategy_engine.main
```

## 开发与测试

```bash
pip install -r requirements-dev.txt
pytest services/strategy-engine/tests
```
