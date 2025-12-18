# Phase 2 代码审查报告：策略引擎与回测系统

**审查日期**: 2025-01-XX  
**审查范围**: 策略引擎与回测系统（4个核心文件）  
**审查维度**: 算法正确性、边界条件、时间穿越、可测试性

---

## 📋 审查概览

| 文件 | Critical | Warning | Info | 总体评分 |
|------|----------|---------|------|----------|
| `strategies/base.py` | 0 | 2 | 2 | ✅ 良好 |
| `strategies/ambush.py` | 2 | 4 | 3 | ⚠️ 需改进 |
| `strategies/ignition.py` | 2 | 3 | 2 | ⚠️ 需改进 |
| `engines/backtest.py` | 3 | 4 | 2 | ⚠️ 需改进 |

**总计**: 7 Critical, 13 Warning, 9 Info

---

## 🔴 文件 1: `strategies/base.py`

### Warning 问题

#### 1. 缺少数据验证 (Line 129-142)
**严重程度**: ⚠️ Warning  
**问题**: `set_data()` 只检查列名，不验证数据质量

**当前代码**:
```python
def set_data(self, df: pd.DataFrame) -> None:
    required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
```

**问题**:
- 不检查数据是否为空
- 不检查数据类型
- 不检查价格是否合理（如负数、零值）
- 不检查时间序列是否连续

**修复建议**:
```python
def set_data(self, df: pd.DataFrame) -> None:
    required_cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    if df.empty:
        raise ValueError("DataFrame is empty")
    
    # Validate data types
    if not pd.api.types.is_datetime64_any_dtype(df['datetime']):
        df = df.copy()
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # Validate price data
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if (df[col] <= 0).any():
            raise ValueError(f"Column {col} contains non-positive values")
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column {col} must be numeric")
    
    # Validate OHLC relationships
    invalid_ohlc = (
        (df['high'] < df['low']) |
        (df['high'] < df['open']) |
        (df['high'] < df['close']) |
        (df['low'] > df['open']) |
        (df['low'] > df['close'])
    )
    if invalid_ohlc.any():
        raise ValueError(f"Invalid OHLC relationships found in {invalid_ohlc.sum()} rows")
    
    # Sort by datetime
    self._data = df.copy()
    self._data = self._data.sort_values('datetime').reset_index(drop=True)
    
    # Check for duplicate timestamps
    if self._data['datetime'].duplicated().any():
        logger.warning(f"Found {self._data['datetime'].duplicated().sum()} duplicate timestamps")
        self._data = self._data.drop_duplicates(subset=['datetime'], keep='last')
    
    # Calculate factors
    self._factors = self.calculate_factors(self._data)
    self._is_initialized = True
    
    logger.info(f"Strategy '{self.name}' loaded {len(self._data)} bars")
```

#### 2. 缺少边界检查 (Line 166-177, 198-208)
**严重程度**: ⚠️ Warning  
**问题**: `generate_signal()` 和 `get_latest_signal()` 不检查 index 是否越界

**修复建议**:
```python
def generate_signal(self, index: int) -> Optional[Signal]:
    if not self.is_ready:
        raise RuntimeError("Strategy not initialized. Call set_data() first.")
    
    if index < 0 or index >= len(self._data):
        raise IndexError(f"Index {index} out of range [0, {len(self._data)})")
    
    # ... 原有逻辑

def get_latest_signal(self) -> Optional[Signal]:
    if not self.is_ready:
        return None
    
    if len(self._data) == 0:
        return None
    
    return self.generate_signal(len(self._data) - 1)
```

### Info 问题

#### 3. 缺少因子缓存机制
**建议**: 如果数据未变化，可以缓存因子计算结果

#### 4. 缺少因子验证
**建议**: 在 `calculate_factors()` 后验证因子是否包含 NaN 或异常值

---

## 🔴 文件 2: `strategies/ambush.py`

### Critical 问题

#### 1. OBV 计算错误 (Line 101)
**严重程度**: 🔴 Critical  
**问题**: OBV (On-Balance Volume) 计算公式不正确

**当前代码**:
```python
df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
```

**问题**: 
- `np.sign()` 返回 -1, 0, 1，但 OBV 应该是：
  - 如果今日收盘 > 昨日收盘：OBV = 昨日OBV + 今日成交量
  - 如果今日收盘 < 昨日收盘：OBV = 昨日OBV - 今日成交量
  - 如果今日收盘 = 昨日收盘：OBV = 昨日OBV

**修复建议**:
```python
# Correct OBV calculation
df['price_change'] = df['close'].diff()
df['obv'] = 0.0
for i in range(1, len(df)):
    if df.iloc[i]['price_change'] > 0:
        df.iloc[i, df.columns.get_loc('obv')] = df.iloc[i-1]['obv'] + df.iloc[i]['volume']
    elif df.iloc[i]['price_change'] < 0:
        df.iloc[i, df.columns.get_loc('obv')] = df.iloc[i-1]['obv'] - df.iloc[i]['volume']
    else:
        df.iloc[i, df.columns.get_loc('obv')] = df.iloc[i-1]['obv']

# Or using vectorized approach (more efficient)
df['obv'] = (np.sign(df['close'].diff()).replace(0, np.nan).fillna(method='ffill') * df['volume']).cumsum()
df['obv'] = df['obv'].fillna(0)  # First row will be NaN
```

**更好的实现**:
```python
def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume correctly."""
    obv = pd.Series(0.0, index=close.index)
    price_change = close.diff()
    
    for i in range(1, len(close)):
        if price_change.iloc[i] > 0:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif price_change.iloc[i] < 0:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv

df['obv'] = calculate_obv(df['close'], df['volume'])
```

#### 2. 时间穿越风险 (Line 104-113)
**严重程度**: 🔴 Critical  
**问题**: `obv_slope` 和 `price_slope` 使用 `rolling().apply()`，可能包含未来数据

**当前代码**:
```python
df['obv_slope'] = df['obv'].rolling(washout_days).apply(
    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == washout_days else np.nan,
    raw=True
)
```

**问题**: 
- `rolling().apply()` 默认是"中心窗口"（center=True），会使用未来数据
- 即使 `raw=True`，如果窗口未满，可能使用不完整数据

**修复建议**:
```python
# Ensure forward-looking is disabled
df['obv_slope'] = df['obv'].rolling(
    window=washout_days, 
    min_periods=washout_days
).apply(
    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == washout_days else np.nan,
    raw=True
)

# Or use shift to ensure we only use past data
def calculate_slope_series(series: pd.Series, window: int) -> pd.Series:
    """Calculate slope using only past data."""
    slopes = pd.Series(np.nan, index=series.index)
    for i in range(window, len(series)):
        window_data = series.iloc[i-window:i]
        if len(window_data) == window:
            slopes.iloc[i] = np.polyfit(range(window), window_data.values, 1)[0]
    return slopes

df['obv_slope'] = calculate_slope_series(df['obv'], washout_days)
df['price_slope'] = calculate_slope_series(df['close'], washout_days)
```

### Warning 问题

#### 3. 除零风险 (Line 84, 94, 123)
**严重程度**: ⚠️ Warning  
**问题**: 多个地方可能出现除零

**修复建议**:
```python
# Line 84
df['volume_ratio'] = df['volume'] / (df['volume_ma20'] + 1e-9)  # 已有 +1，但可以更明确

# Line 94
df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (df['sma20'] + 1e-9)

# Line 123
df['relative_pos'] = (df['close'] - df['price_min5']) / (df['price_max5'] - df['price_min5'] + 1e-9)
```

#### 4. NaN 处理不完整 (Line 143-144)
**严重程度**: ⚠️ Warning  
**问题**: 只检查了部分因子的 NaN，其他因子未检查

**修复建议**:
```python
# Check all critical factors
critical_factors = ['volume_ratio', 'bb_width', 'intraday_range', 'price_change_n', 'obv_divergence']
if any(pd.isna(row.get(factor)) for factor in critical_factors):
    return None
```

#### 5. 阈值设置缺少验证
**严重程度**: ⚠️ Warning  
**问题**: 配置参数没有范围验证

**修复建议**: 在 `AmbushConfig` 中添加 `__post_init__()` 验证

#### 6. 置信度计算逻辑可能有问题 (Line 172-179)
**严重程度**: ⚠️ Warning  
**问题**: 如果 OBV 背离存在，置信度可能超过 1.0

**修复建议**:
```python
base_confidence = passed_checks / total_checks

# Boost confidence if OBV divergence is present (key signal)
if checks['obv_divergence']:
    base_confidence = min(1.0, base_confidence + 0.15)  # 已有 min(1.0, ...)，但可以更保守
```

### Info 问题

#### 7. 因子计算可以优化
**建议**: 使用 `ta-lib` 或 `pandas_ta` 库计算技术指标，更可靠

#### 8. 缺少因子重要性分析
**建议**: 记录每个因子的贡献度，便于策略优化

---

## 🔴 文件 3: `strategies/ignition.py`

### Critical 问题

#### 1. VWAP 计算错误 (Line 120)
**严重程度**: 🔴 Critical  
**问题**: VWAP 应该按日计算，不应该跨日累加

**当前代码**:
```python
df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
```

**问题**: 
- VWAP (Volume Weighted Average Price) 应该每天重新计算
- 当前实现会跨日累加，导致 VWAP 失真

**修复建议**:
```python
# Calculate VWAP per day
df['vwap'] = np.nan
for date, group in df.groupby('date'):
    # VWAP for this day
    cum_price_volume = (group['close'] * group['volume']).cumsum()
    cum_volume = group['volume'].cumsum()
    vwap_daily = cum_price_volume / (cum_volume + 1e-9)
    
    # Assign back to original dataframe
    date_mask = df['date'] == date
    df.loc[date_mask, 'vwap'] = vwap_daily.values

# Or using groupby transform (more efficient)
def calculate_vwap(group):
    cum_pv = (group['close'] * group['volume']).cumsum()
    cum_v = group['volume'].cumsum()
    return cum_pv / (cum_v + 1e-9)

df['vwap'] = df.groupby('date').apply(calculate_vwap).reset_index(level=0, drop=True)
```

#### 2. 5日高点计算可能包含未来数据 (Line 104)
**严重程度**: 🔴 Critical  
**问题**: `rolling(240 * 5)` 在分钟级数据上可能跨越多个交易日，需要按日计算

**当前代码**:
```python
df['high5'] = df['high'].rolling(240 * 5, min_periods=240).max()
```

**问题**: 
- 240 * 5 = 1200 分钟，但实际交易日可能不是连续的
- 应该使用交易日而非分钟数

**修复建议**:
```python
# Calculate 5-day high using daily aggregation
df['daily_high'] = df.groupby('date')['high'].transform('max')
df['high5'] = df.groupby('date')['daily_high'].transform(
    lambda x: x.rolling(5, min_periods=1).max()
)

# For minute-level comparison, use the 5-day high from the same day
df['price_vs_high5'] = (df['close'] - df['high5']) / (df['high5'] + 1e-9)
```

### Warning 问题

#### 3. 交易时段计算不准确 (Line 97-101)
**严重程度**: ⚠️ Warning  
**问题**: `minute_of_day` 计算没有考虑午休时间

**当前代码**:
```python
df['minute_of_day'] = (
    df['datetime'].dt.hour * 60 + df['datetime'].dt.minute - 9 * 60 - 30
)
df['minute_of_day'] = df['minute_of_day'].clip(0, 240)
```

**问题**: 
- 没有跳过 11:30-13:00 的午休时间
- 下午时段应该从 240 继续计算，而不是重置

**修复建议**:
```python
def calculate_trading_minute(dt: pd.Timestamp) -> int:
    """Calculate trading minute of day (0-240, skipping lunch break)."""
    hour = dt.hour
    minute = dt.minute
    
    # Morning session: 9:30 - 11:30 (120 minutes)
    if 9 <= hour < 11 or (hour == 11 and minute < 30):
        if hour == 9:
            return minute - 30  # 9:30 = 0, 9:31 = 1, ...
        elif hour == 10:
            return 30 + minute  # 10:00 = 30, 10:01 = 31, ...
        elif hour == 11:
            return 90 + minute  # 11:00 = 90, 11:29 = 119
    # Afternoon session: 13:00 - 15:00 (120 minutes)
    elif hour >= 13:
        if hour == 13:
            return 120 + minute  # 13:00 = 120, 13:01 = 121, ...
        elif hour == 14:
            return 180 + minute  # 14:00 = 180, 14:59 = 239
        elif hour == 15:
            return 240  # 15:00 = 240 (market close)
    
    return np.nan  # Outside trading hours

df['minute_of_day'] = df['datetime'].apply(calculate_trading_minute)
```

#### 4. 时间窗口检查逻辑 (Line 125-127)
**严重程度**: ⚠️ Warning  
**问题**: `_is_preferred_time()` 使用 `<=` 比较，但 `time` 对象比较可能不准确

**修复建议**:
```python
def _is_preferred_time(self, t: time) -> bool:
    """Check if current time is in preferred trading window."""
    if t is None or pd.isna(t):
        return False
    
    # Convert to minutes since midnight for accurate comparison
    t_minutes = t.hour * 60 + t.minute
    start_minutes = self._start_time.hour * 60 + self._start_time.minute
    end_minutes = self._end_time.hour * 60 + self._end_time.minute
    
    return start_minutes <= t_minutes <= end_minutes
```

#### 5. 量比计算可能不准确 (Line 91)
**严重程度**: ⚠️ Warning  
**问题**: `volume_ma20` 可能包含非交易时段的零成交量

**修复建议**: 过滤掉零成交量或非交易时段的数据

### Info 问题

#### 6. 缺少交易时段验证
**建议**: 验证数据是否包含完整的交易时段

---

## 🔴 文件 4: `engines/backtest.py`

### Critical 问题

#### 1. Look-ahead Bias (时间穿越) (Line 181)
**严重程度**: 🔴 Critical  
**问题**: 策略生成信号时可能使用了未来数据

**当前代码**:
```python
# Line 181
signal = strategy.generate_signal(i)

# 但在策略中，calculate_factors() 可能使用了未来数据
# 例如：rolling window 默认是中心窗口
```

**问题**: 
- `strategy.generate_signal(i)` 调用时，策略内部的因子计算可能使用了 `i` 之后的数据
- 虽然 `set_data()` 时计算了因子，但如果因子计算使用了 `rolling(center=True)`，就会包含未来数据

**修复建议**:
```python
def run(self, strategy: BaseStrategy, data: pd.DataFrame, symbol: str = "BACKTEST") -> BacktestResult:
    # ...
    
    # Bar-by-bar simulation
    for i in range(strategy.config.lookback_days, len(data)):
        row = data.iloc[i]
        current_time = pd.to_datetime(row['datetime'])
        current_price = row['close']
        
        # CRITICAL: Only use data up to current bar (exclusive of future)
        # Strategy should only see data[0:i+1] when generating signal for bar i
        historical_data = data.iloc[:i+1].copy()
        
        # Recalculate factors with only historical data (if needed)
        # Note: This is expensive, so strategies should cache factors properly
        strategy.set_data(historical_data)
        
        # Generate signal using only past data
        signal = strategy.generate_signal(i)
        
        # ... rest of the logic
```

**更好的方案**: 在策略基类中确保因子计算不使用未来数据：
```python
# In BaseStrategy.calculate_factors()
# Ensure all rolling operations use only past data
df['sma20'] = df['close'].rolling(20, min_periods=1).mean()  # Not center=True
```

#### 2. 交易成本计算不完整 (Line 233, 241, 296, 300)
**严重程度**: 🔴 Critical  
**问题**: 
- 买入时只计算了佣金，没有计算印花税
- 卖出时没有计算印花税（A股卖出有0.1%印花税）

**当前代码**:
```python
# Line 241: Buy commission only
commission = quantity * entry_price * self.config.commission_rate

# Line 300: Sell commission only
commission = pos.quantity * actual_exit_price * self.config.commission_rate
```

**修复建议**:
```python
@dataclass
class BacktestConfig:
    # ...
    commission_rate: float = 0.0003  # 万三
    stamp_tax_rate: float = 0.001  # 0.1% (only on sell)
    slippage_pct: float = 0.001  # 0.1% slippage

def _process_buy_signal(self, ...):
    # ...
    # Buy: commission only (no stamp tax)
    commission = quantity * entry_price * self.config.commission_rate
    actual_cost = quantity * entry_price + commission
    # ...

def _close_position(self, ...):
    # ...
    # Sell: commission + stamp tax
    commission = pos.quantity * actual_exit_price * self.config.commission_rate
    stamp_tax = pos.quantity * actual_exit_price * self.config.stamp_tax_rate
    total_cost = commission + stamp_tax
    
    # Calculate P&L
    gross_pnl = (actual_exit_price - pos.entry_price) * pos.quantity
    net_pnl = gross_pnl - commission - stamp_tax  # Deduct both
    
    # Return capital
    self._capital += pos.quantity * actual_exit_price - total_cost
    # ...
```

#### 3. 参数扫描可能导致过拟合 (Line 393-444)
**严重程度**: 🔴 Critical  
**问题**: `run_parameter_sweep()` 没有使用样本外验证，容易过拟合

**当前代码**:
```python
def run_parameter_sweep(self, ...):
    # ...
    for combo in combinations:
        # Run backtest on same data
        result = self.run(strategy, data, symbol)
        # ...
    # Sort by Sharpe ratio (best on training data)
    results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
```

**问题**: 
- 在相同数据上优化参数，然后选择最佳参数，这是典型的过拟合
- 没有使用 walk-forward 或样本外验证

**修复建议**:
```python
def run_parameter_sweep(
    self,
    strategy_class: Type[BaseStrategy],
    config_class: Type[StrategyConfig],
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    symbol: str = "BACKTEST",
    use_walk_forward: bool = True,
    train_ratio: float = 0.7
) -> List[BacktestResult]:
    """
    Run parameter sweep with walk-forward validation to avoid overfitting.
    """
    results = []
    
    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    logger.info(f"Running parameter sweep: {len(combinations)} combinations")
    
    for combo in combinations:
        params = dict(zip(param_names, combo))
        
        try:
            config = config_class(**params)
            strategy = strategy_class(config)
            
            if use_walk_forward:
                # Use walk-forward to get out-of-sample performance
                train_result, test_result = self.run_walk_forward(
                    strategy, data, symbol, train_ratio
                )
                
                # Use test (out-of-sample) Sharpe as the metric
                result = test_result
                result.parameters = params
                result.train_sharpe = train_result.sharpe_ratio  # Keep for reference
            else:
                # Traditional approach (warning about overfitting)
                logger.warning("Parameter sweep without walk-forward may lead to overfitting")
                result = self.run(strategy, data, symbol)
                result.parameters = params
            
            results.append(result)
            
        except Exception as e:
            logger.warning(f"Sweep failed for params {params}: {e}")
    
    # Sort by out-of-sample Sharpe ratio
    results.sort(key=lambda r: r.sharpe_ratio, reverse=True)
    
    logger.info(
        f"Sweep complete. Best OOS Sharpe: {results[0].sharpe_ratio:.2f}" 
        if results else "No results"
    )
    
    return results
```

### Warning 问题

#### 4. 持仓更新时机问题 (Line 175, 178)
**严重程度**: ⚠️ Warning  
**问题**: 先更新持仓价格，再检查退出条件，可能导致使用未来价格

**当前代码**:
```python
# Update positions with current price
self._update_positions(current_price, current_time, row)

# Check for exit conditions
self._check_exits(current_price, current_time)
```

**问题**: 应该先检查退出条件（使用上一bar的价格），再更新持仓

**修复建议**:
```python
# Check exits first (using previous bar's price for positions)
if i > 0:
    prev_price = data.iloc[i-1]['close']
    self._check_exits(prev_price, current_time)

# Then update positions with current price
self._update_positions(current_price, current_time, row)
```

#### 5. 信号执行价格问题 (Line 186)
**严重程度**: ⚠️ Warning  
**问题**: 使用 `current_price`（当前bar的收盘价）执行信号，但实际应该用下一bar的开盘价

**当前代码**:
```python
signal = strategy.generate_signal(i)
if signal and signal.signal_type == SignalType.BUY:
    self._process_buy_signal(signal, current_price, current_time, symbol)
```

**修复建议**:
```python
# Signal generated at bar i, but executed at bar i+1 open
if signal and signal.signal_type == SignalType.BUY:
    if i + 1 < len(data):
        # Execute at next bar's open price
        execution_price = data.iloc[i+1]['open']
        execution_time = pd.to_datetime(data.iloc[i+1]['datetime'])
        self._process_buy_signal(signal, execution_price, execution_time, symbol)
    else:
        # Last bar, use current close
        self._process_buy_signal(signal, current_price, current_time, symbol)
```

#### 6. 权益曲线计算可能不准确 (Line 189)
**严重程度**: ⚠️ Warning  
**问题**: 使用当前价格计算权益，但持仓价格可能已经更新

**修复建议**: 确保权益计算使用一致的持仓价格

#### 7. 缺少风险检查
**严重程度**: ⚠️ Warning  
**问题**: 回测引擎没有集成 `RiskManager`

**修复建议**: 在 `_process_buy_signal()` 中添加风险检查

### Info 问题

#### 8. 缺少回测报告详细度
**建议**: 添加更多性能指标（如 Calmar Ratio, Sortino Ratio）

---

## 📊 总体建议

### 1. 添加单元测试
**优先级**: 🔴 Critical  
**建议**: 为每个策略和回测引擎添加单元测试

```python
# tests/test_ambush_strategy.py
def test_obv_calculation():
    """Test OBV calculation is correct."""
    df = pd.DataFrame({
        'close': [10, 11, 10, 12, 11],
        'volume': [1000, 2000, 1500, 3000, 2500]
    })
    
    strategy = AmbushStrategy()
    factors = strategy.calculate_factors(df)
    
    # Verify OBV calculation
    assert factors['obv'].iloc[1] == 2000  # Price up, add volume
    assert factors['obv'].iloc[2] == 500   # Price down, subtract volume
    # ...

def test_no_lookahead_bias():
    """Test that strategy doesn't use future data."""
    # ...
```

### 2. 添加集成测试
**优先级**: ⚠️ Warning  
**建议**: 添加端到端的回测测试

### 3. 性能优化
**优先级**: ℹ️ Info  
**建议**: 
- 缓存因子计算结果
- 使用向量化操作替代循环

---

## ✅ 符合项（优点）

1. **代码结构清晰**: 策略基类设计合理，易于扩展
2. **配置分离**: 策略参数通过 Config 类管理
3. **信号设计**: Signal 数据类设计完善
4. **回测框架**: 回测引擎框架完整

---

## 🎯 修复优先级建议

### 立即修复 (P0)
1. OBV 计算错误 (`ambush.py`)
2. VWAP 计算错误 (`ignition.py`)
3. Look-ahead Bias (`backtest.py`)
4. 交易成本计算不完整 (`backtest.py`)

### 尽快修复 (P1)
1. 时间穿越风险 (`ambush.py`)
2. 5日高点计算 (`ignition.py`)
3. 参数扫描过拟合 (`backtest.py`)
4. 信号执行价格 (`backtest.py`)

### 计划修复 (P2)
1. 数据验证 (`base.py`)
2. 边界检查 (`base.py`)
3. 交易时段计算 (`ignition.py`)

---

## 📝 总结

整体代码质量**良好**，但存在一些**关键的算法错误**和**时间穿越风险**需要立即修复。主要问题集中在：

1. **算法正确性**: OBV、VWAP 计算错误
2. **时间穿越**: 回测时可能使用未来数据
3. **交易成本**: 缺少印花税计算
4. **过拟合风险**: 参数扫描没有样本外验证

建议按照优先级逐步修复，并在修复后添加相应的单元测试。

---

**审查完成时间**: 2025-01-XX  
**下次审查建议**: 修复 Critical 问题后进行回归审查

