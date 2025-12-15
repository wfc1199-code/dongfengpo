# 东风破优化实施计划

> 基于原版1.1.0功能借鉴  
> 聚焦核心技术检测功能

---

## 🎯 核心目标

实现4个关键功能模块：
1. **横盘突破检测** - 识别横盘后的放量突破
2. **异动状态机** - 完善5状态转换逻辑
3. **破峰突破报警** - 检测突破当日最高点
4. **连续异动统计** - 量化异动强度指标

---

## 📅 实施计划

### Phase 1: 后端核心算法（2-3天）

#### Day 1: 横盘突破检测

**文件**: `backend/core/consolidation_breakout.py`

```python
class ConsolidationBreakoutDetector:
    """横盘放量突破检测器"""
    
    def __init__(self):
        self.config = {
            'consolidation_range': 3.0,      # 横盘涨幅范围 ±3%
            'consolidation_minutes': 30,     # 横盘持续时长 30分钟
            'breakout_volume_ratio': 2.0,    # 突破量比 2倍
            'breakout_threshold': 2.0,       # 突破涨幅阈值 2%
        }
    
    async def detect(self, stock_code: str) -> dict:
        """
        检测横盘突破
        
        Returns:
            {
                'detected': True/False,
                'consolidation_duration': 35,  # 横盘时长（分钟）
                'consolidation_range': 2.5,    # 横盘波动范围（%）
                'breakout_volume_ratio': 2.8,  # 突破量比
                'breakout_price': 15.68,       # 突破价格
                'strength': 85                  # 突破强度 0-100
            }
        """
        # 1. 获取最近60分钟分时数据
        timeshare = await self.data_source.get_timeshare(stock_code, minutes=60)
        
        # 2. 识别横盘阶段
        consolidations = self._find_consolidation_periods(timeshare)
        
        # 3. 检测当前是否突破
        for period in consolidations:
            if self._is_breakout(period, timeshare[-1]):
                return self._format_result(period, timeshare[-1])
        
        return {'detected': False}
    
    def _find_consolidation_periods(self, timeshare: list) -> list:
        """
        识别横盘阶段
        
        算法：
        1. 滑动窗口检测价格波动
        2. 波动 < 3% 且持续 > 30分钟
        3. 记录横盘区间和平均成交量
        """
        periods = []
        window_size = self.config['consolidation_minutes']
        
        for i in range(len(timeshare) - window_size):
            window = timeshare[i:i + window_size]
            
            # 计算价格波动范围
            prices = [item['price'] for item in window]
            high = max(prices)
            low = min(prices)
            price_range = (high - low) / low * 100
            
            # 判断是否横盘
            if price_range <= self.config['consolidation_range']:
                periods.append({
                    'start_idx': i,
                    'end_idx': i + window_size - 1,
                    'duration': window_size,
                    'price_high': high,
                    'price_low': low,
                    'price_range': price_range,
                    'avg_volume': sum(item['volume'] for item in window) / len(window),
                    'prices': prices,
                    'volumes': [item['volume'] for item in window]
                })
        
        # 合并相邻的横盘区间
        return self._merge_periods(periods)
    
    def _is_breakout(self, period: dict, current: dict) -> bool:
        """
        判断是否突破
        
        条件：
        1. 当前价格 > 横盘高点 + 突破阈值
        2. 当前成交量 > 平均成交量 * 量比阈值
        """
        # 价格突破
        price_breakout_pct = (
            (current['price'] - period['price_high']) / 
            period['price_high'] * 100
        )
        
        # 量能突破
        volume_ratio = current['volume'] / period['avg_volume']
        
        return (
            price_breakout_pct >= self.config['breakout_threshold'] and
            volume_ratio >= self.config['breakout_volume_ratio']
        )
    
    def _calculate_strength(self, period: dict, current: dict) -> int:
        """
        计算突破强度
        
        考虑因素：
        1. 横盘时长（越长越强）
        2. 突破幅度（越大越强）
        3. 量比倍数（越大越强）
        4. 横盘波动（越小越强）
        """
        # 时长分数（0-25分）
        duration_score = min(period['duration'] / 60 * 25, 25)
        
        # 突破幅度分数（0-25分）
        breakout_pct = (current['price'] - period['price_high']) / period['price_high'] * 100
        breakout_score = min(breakout_pct / 5 * 25, 25)
        
        # 量比分数（0-25分）
        volume_ratio = current['volume'] / period['avg_volume']
        volume_score = min((volume_ratio - 1) / 2 * 25, 25)
        
        # 横盘稳定性分数（0-25分）
        stability_score = (1 - period['price_range'] / 5) * 25
        
        total_score = duration_score + breakout_score + volume_score + stability_score
        return int(max(0, min(100, total_score)))
```

**测试用例**:
```python
# tests/test_consolidation_breakout.py

async def test_detect_consolidation_breakout():
    detector = ConsolidationBreakoutDetector()
    
    # 模拟数据：横盘30分钟后放量突破
    result = await detector.detect('300123')
    
    assert result['detected'] == True
    assert result['consolidation_duration'] >= 30
    assert result['breakout_volume_ratio'] >= 2.0
    assert result['strength'] >= 60
```

---

#### Day 2: 异动状态机完善

**文件**: `backend/core/anomaly_state_machine.py`

```python
from enum import Enum
from datetime import datetime, timedelta

class AnomalyState(Enum):
    IDLE = "空闲"           # 未异动
    STARTING = "开始拉升"   # 第一次异动
    CONTINUING = "持续拉升" # 连续异动
    NEAR_LIMIT = "快要涨停" # 接近涨停
    LIMIT_UP = "已涨停"     # 已涨停
    FALLING = "冲高回落"    # 回落状态

class AnomalyStateMachine:
    """异动状态机"""
    
    def __init__(self):
        self.states = {}           # {stock_code: current_state}
        self.anomaly_history = {}  # {stock_code: [anomaly_records]}
        self.state_history = {}    # {stock_code: [state_changes]}
    
    def update(self, stock_code: str, current_data: dict) -> dict:
        """
        更新股票状态
        
        Args:
            stock_code: 股票代码
            current_data: 当前数据 {
                'price': 15.68,
                'change_percent': 5.23,
                'volume': 1000000,
                'is_anomaly': True,
                'timestamp': datetime
            }
        
        Returns:
            {
                'state': '开始拉升',
                'previous_state': '空闲',
                'state_changed': True,
                'continuous_count': 3,     # 连续异动次数
                'last_10_count': 7,        # 最近10次中异动次数
                'total_count': 15,         # 总异动次数
                'should_alert': True       # 是否触发报警
            }
        """
        current_state = self.states.get(stock_code, AnomalyState.IDLE)
        new_state = self._calculate_new_state(stock_code, current_state, current_data)
        
        # 记录异动点
        if current_data.get('is_anomaly'):
            self._record_anomaly(stock_code, current_data)
        
        # 状态转换
        state_changed = new_state != current_state
        if state_changed:
            self._record_state_change(stock_code, current_state, new_state, current_data)
            self.states[stock_code] = new_state
        
        # 计算统计指标
        stats = self._calculate_statistics(stock_code)
        
        return {
            'state': new_state.value,
            'previous_state': current_state.value,
            'state_changed': state_changed,
            'continuous_count': stats['continuous'],
            'last_10_count': stats['last_10'],
            'total_count': stats['total'],
            'should_alert': self._should_alert(current_state, new_state)
        }
    
    def _calculate_new_state(self, stock_code: str, 
                            current_state: AnomalyState,
                            data: dict) -> AnomalyState:
        """
        计算新状态
        
        状态转换规则：
        1. IDLE → STARTING: 检测到第一次异动
        2. STARTING → CONTINUING: 5分钟内再次异动
        3. CONTINUING → NEAR_LIMIT: 涨幅超过8%（创业板18%）
        4. NEAR_LIMIT → LIMIT_UP: 涨幅超过9.8%（创业板19.8%）
        5. ANY → FALLING: 价格回落超过2%
        6. FALLING → IDLE: 回落后平稳
        """
        change_pct = data['change_percent']
        is_gem = self._is_gem_or_star_market(stock_code)
        
        # 判断涨停状态
        if change_pct >= (19.8 if is_gem else 9.8):
            return AnomalyState.LIMIT_UP
        
        # 判断快要涨停
        if change_pct >= (18.0 if is_gem else 8.0):
            return AnomalyState.NEAR_LIMIT
        
        # 判断回落
        if self._is_falling(stock_code, data):
            return AnomalyState.FALLING
        
        # 判断是否新的异动开始
        if data.get('is_anomaly'):
            last_anomaly = self._get_last_anomaly(stock_code)
            if not last_anomaly:
                return AnomalyState.STARTING
            
            # 检查时间间隔
            time_diff = (data['timestamp'] - last_anomaly['timestamp']).total_seconds()
            if time_diff > 300:  # 5分钟
                return AnomalyState.STARTING
            else:
                return AnomalyState.CONTINUING
        
        # 保持当前状态或回到空闲
        if current_state in [AnomalyState.STARTING, AnomalyState.CONTINUING]:
            return current_state
        
        return AnomalyState.IDLE
    
    def _calculate_statistics(self, stock_code: str) -> dict:
        """
        计算统计指标
        
        Returns:
            {
                'continuous': 3,  # 连续异动次数
                'last_10': 7,     # 最近10次中异动次数
                'total': 15       # 总异动次数
            }
        """
        anomalies = self.anomaly_history.get(stock_code, [])
        
        if not anomalies:
            return {'continuous': 0, 'last_10': 0, 'total': 0}
        
        # 连续异动次数
        continuous = 1
        for i in range(len(anomalies) - 1, 0, -1):
            time_diff = (anomalies[i]['timestamp'] - 
                        anomalies[i-1]['timestamp']).total_seconds()
            if time_diff <= 300:  # 5分钟内
                continuous += 1
            else:
                break
        
        # 最近10次中的异动次数
        last_10_anomalies = anomalies[-10:] if len(anomalies) >= 10 else anomalies
        last_10_count = len(last_10_anomalies)
        
        return {
            'continuous': continuous,
            'last_10': last_10_count,
            'total': len(anomalies)
        }
    
    def _should_alert(self, old_state: AnomalyState, 
                     new_state: AnomalyState) -> bool:
        """
        判断是否应该报警
        
        报警条件：
        1. 转换到 STARTING（开始拉升）
        2. 转换到 NEAR_LIMIT（快要涨停）
        """
        return new_state in [AnomalyState.STARTING, AnomalyState.NEAR_LIMIT]
    
    def _record_anomaly(self, stock_code: str, data: dict):
        """记录异动点"""
        if stock_code not in self.anomaly_history:
            self.anomaly_history[stock_code] = []
        
        self.anomaly_history[stock_code].append({
            'timestamp': data['timestamp'],
            'price': data['price'],
            'change_percent': data['change_percent'],
            'volume': data['volume']
        })
    
    def _record_state_change(self, stock_code: str, old_state: AnomalyState,
                            new_state: AnomalyState, data: dict):
        """记录状态变化"""
        if stock_code not in self.state_history:
            self.state_history[stock_code] = []
        
        self.state_history[stock_code].append({
            'timestamp': data['timestamp'],
            'old_state': old_state.value,
            'new_state': new_state.value,
            'price': data['price'],
            'change_percent': data['change_percent']
        })
```

---

#### Day 3: 破峰突破检测

**文件**: `backend/core/peak_breakout.py`

```python
class PeakBreakoutDetector:
    """破峰突破检测器"""
    
    async def detect(self, stock_code: str) -> dict:
        """
        检测破峰突破
        
        算法：
        1. 获取今日分时数据
        2. 使用局部极值算法识别所有峰值
        3. 找到最大峰值
        4. 判断当前是否突破最大峰值
        
        Returns:
            {
                'detected': True/False,
                'peak_price': 15.85,       # 峰值价格
                'peak_time': '10:35:00',   # 峰值时间
                'current_price': 16.02,    # 当前价格
                'breakout_percent': 1.07,  # 突破幅度（%）
                'peak_volume': 500000      # 峰值时成交量
            }
        """
        # 1. 获取今日分时数据
        timeshare = await self.data_source.get_today_timeshare(stock_code)
        
        if len(timeshare) < 10:
            return {'detected': False, 'reason': '数据不足'}
        
        # 2. 识别峰值
        peaks = self._find_peaks(timeshare)
        
        if not peaks:
            return {'detected': False, 'reason': '无峰值'}
        
        # 3. 最大峰值
        max_peak = max(peaks, key=lambda p: p['price'])
        
        # 4. 当前价格
        current = timeshare[-1]
        
        # 5. 判断突破
        if current['price'] > max_peak['price']:
            breakout_pct = (
                (current['price'] - max_peak['price']) / 
                max_peak['price'] * 100
            )
            
            return {
                'detected': True,
                'peak_price': max_peak['price'],
                'peak_time': max_peak['time'],
                'peak_index': max_peak['index'],
                'current_price': current['price'],
                'breakout_percent': breakout_pct,
                'peak_volume': max_peak['volume']
            }
        
        return {
            'detected': False,
            'reason': '未突破',
            'peak_price': max_peak['price'],
            'current_price': current['price'],
            'distance_to_peak': (max_peak['price'] - current['price']) / current['price'] * 100
        }
    
    def _find_peaks(self, timeshare: list, window: int = 5) -> list:
        """
        识别峰值点（局部最高点）
        
        算法：滑动窗口局部极值法
        - 在窗口内，如果某点是最高点，则认为是峰值
        
        Args:
            timeshare: 分时数据
            window: 窗口大小（默认5，即前后各5个点）
        
        Returns:
            [{'price': 15.85, 'time': '10:35', 'volume': 500000, 'index': 125}, ...]
        """
        peaks = []
        
        for i in range(window, len(timeshare) - window):
            current_price = timeshare[i]['price']
            is_peak = True
            
            # 检查前后窗口范围
            for j in range(i - window, i + window + 1):
                if j != i and timeshare[j]['price'] > current_price:
                    is_peak = False
                    break
            
            if is_peak:
                peaks.append({
                    'price': current_price,
                    'time': timeshare[i]['time'],
                    'volume': timeshare[i]['volume'],
                    'index': i
                })
        
        return peaks
    
    def get_peak_support_resistance(self, stock_code: str) -> dict:
        """
        获取峰值作为阻力位
        
        可用于支撑压力分析
        """
        timeshare = await self.data_source.get_today_timeshare(stock_code)
        peaks = self._find_peaks(timeshare)
        
        # 按价格排序
        peaks_sorted = sorted(peaks, key=lambda p: p['price'], reverse=True)
        
        return {
            'resistance_levels': [p['price'] for p in peaks_sorted[:3]],  # 前3个峰值作为阻力位
            'current_price': timeshare[-1]['price'],
            'all_peaks': peaks
        }
```

---

### Phase 2: API集成（1天）

#### 新增API端点

**文件**: `backend/modules/anomaly/module.py`

```python
@router.get("/consolidation-breakout")
async def detect_consolidation_breakout(
    stock_code: str = None,
    scan_all: bool = False
):
    """
    横盘突破检测
    
    Params:
        stock_code: 股票代码（可选）
        scan_all: 是否扫描全市场（默认False）
    
    Returns:
        {
            "code": 200,
            "data": {
                "breakouts": [
                    {
                        "code": "300123",
                        "name": "天龙光电",
                        "consolidation_duration": 35,
                        "breakout_volume_ratio": 2.8,
                        "strength": 85
                    }
                ]
            }
        }
    """
    detector = ConsolidationBreakoutDetector()
    
    if scan_all:
        # 扫描全市场
        stocks = await get_all_stocks()
        breakouts = []
        
        for stock in stocks:
            result = await detector.detect(stock['code'])
            if result['detected']:
                breakouts.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    **result
                })
        
        return {'code': 200, 'data': {'breakouts': breakouts}}
    else:
        # 单只股票
        result = await detector.detect(stock_code)
        return {'code': 200, 'data': result}


@router.get("/peak-breakout")
async def detect_peak_breakout(stock_code: str):
    """破峰突破检测"""
    detector = PeakBreakoutDetector()
    result = await detector.detect(stock_code)
    return {'code': 200, 'data': result}


@router.get("/state")
async def get_anomaly_state(stock_code: str):
    """
    获取股票异动状态
    
    Returns:
        {
            "code": 200,
            "data": {
                "state": "开始拉升",
                "continuous_count": 3,
                "last_10_count": 7,
                "total_count": 15,
                "state_history": [...]
            }
        }
    """
    state_machine = get_state_machine()  # 全局单例
    
    # 获取当前状态
    current_state = state_machine.states.get(stock_code, AnomalyState.IDLE)
    stats = state_machine._calculate_statistics(stock_code)
    history = state_machine.state_history.get(stock_code, [])
    
    return {
        'code': 200,
        'data': {
            'state': current_state.value,
            'continuous_count': stats['continuous'],
            'last_10_count': stats['last_10'],
            'total_count': stats['total'],
            'state_history': history[-10:]  # 最近10次状态变化
        }
    }
```

---

### Phase 3: 前端展示（1-2天）

#### 1. 横盘突破监控组件

**文件**: `frontend/src/components/ConsolidationBreakoutMonitor.tsx`

```typescript
interface ConsolidationBreakout {
  code: string;
  name: string;
  consolidationDuration: number;
  consolidationRange: number;
  breakoutVolumeRatio: number;
  breakoutPrice: number;
  strength: number;
  detectedAt: string;
}

const ConsolidationBreakoutMonitor: React.FC = () => {
  const [breakouts, setBreakouts] = useState<ConsolidationBreakout[]>([]);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    const fetchBreakouts = async () => {
      const response = await fetch(
        'http://localhost:9000/api/anomaly/consolidation-breakout?scan_all=true'
      );
      const data = await response.json();
      setBreakouts(data.data.breakouts || []);
    };
    
    fetchBreakouts();
    const interval = setInterval(fetchBreakouts, 30000);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="consolidation-monitor">
      <div className="monitor-header">
        <h3>📊 横盘突破监控</h3>
        <span className="count">{breakouts.length} 个突破</span>
      </div>
      
      <div className="breakout-list">
        {breakouts.map(item => (
          <div key={item.code} className="breakout-card">
            <div className="card-header">
              <span className="stock-code">{item.code}</span>
              <span className="stock-name">{item.name}</span>
              <span className={`strength-badge strength-${getStrengthLevel(item.strength)}`}>
                强度 {item.strength}
              </span>
            </div>
            
            <div className="card-metrics">
              <div className="metric">
                <span className="label">横盘时长</span>
                <span className="value">{item.consolidationDuration}分钟</span>
              </div>
              <div className="metric">
                <span className="label">突破量比</span>
                <span className="value">{item.breakoutVolumeRatio.toFixed(1)}倍</span>
              </div>
              <div className="metric">
                <span className="label">突破价格</span>
                <span className="value">¥{item.breakoutPrice.toFixed(2)}</span>
              </div>
            </div>
            
            <div className="card-footer">
              <span className="time">{item.detectedAt}</span>
              <button onClick={() => handleStockSelect(item.code)}>
                查看详情
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

#### 2. 异动状态指示器

**文件**: `frontend/src/components/AnomalyStateIndicator.tsx`

```typescript
interface AnomalyStateInfo {
  state: string;
  continuousCount: number;
  last10Count: number;
  totalCount: number;
}

const AnomalyStateIndicator: React.FC<{code: string}> = ({ code }) => {
  const [stateInfo, setStateInfo] = useState<AnomalyStateInfo | null>(null);
  
  useEffect(() => {
    const fetchState = async () => {
      const response = await fetch(
        `http://localhost:9000/api/anomaly/state?stock_code=${code}`
      );
      const data = await response.json();
      setStateInfo(data.data);
    };
    
    fetchState();
    const interval = setInterval(fetchState, 5000);
    return () => clearInterval(interval);
  }, [code]);
  
  if (!stateInfo) return null;
  
  const stateConfig = {
    '空闲': { color: '#999', icon: '⚪' },
    '开始拉升': { color: '#52c41a', icon: '🟢' },
    '持续拉升': { color: '#ff6b35', icon: '🟠' },
    '快要涨停': { color: '#ff4d4f', icon: '🔴' },
    '已涨停': { color: '#f759ab', icon: '🟣' },
    '冲高回落': { color: '#faad14', icon: '🟡' }
  };
  
  const config = stateConfig[stateInfo.state] || stateConfig['空闲'];
  
  return (
    <div className="state-indicator">
      <div className="state-badge" style={{ borderColor: config.color }}>
        <span className="state-icon">{config.icon}</span>
        <span className="state-text" style={{ color: config.color }}>
          {stateInfo.state}
        </span>
      </div>
      
      <div className="state-stats">
        <span className="stat">
          连续 <strong>{stateInfo.continuousCount}</strong>
        </span>
        <span className="divider">|</span>
        <span className="stat">
          10中<strong>{stateInfo.last10Count}</strong>
        </span>
        <span className="divider">|</span>
        <span className="stat">
          总计 <strong>{stateInfo.totalCount}</strong>
        </span>
      </div>
    </div>
  );
};
```

#### 3. 在机会流中集成

**更新**: `frontend/src/components/SmartOpportunityFeed.tsx`

```typescript
// 在卡片中添加状态和统计信息
<div className="opportunity-card">
  <div className="stock-header">
    <span className="symbol">{opp.code}</span>
    <span className="name">{opp.name}</span>
    <AnomalyStateIndicator code={opp.code} />
  </div>
  
  <div className="metrics-row">
    <span className="metric change">{opp.changePercent}%</span>
    <span className="divider">|</span>
    <span className="metric">连续 {opp.continuousCount}</span>
    <span className="divider">|</span>
    <span className="metric">10中{opp.last10Count}</span>
  </div>
  
  {opp.hasConsolidationBreakout && (
    <div className="special-tag breakout">
      📊 横盘突破
    </div>
  )}
  
  {opp.hasPeakBreakout && (
    <div className="special-tag peak">
      🏔️ 破峰突破
    </div>
  )}
</div>
```

---

## 📋 验收标准

### 功能验收

- [ ] 横盘突破检测准确率 > 85%
- [ ] 状态机转换正确率 > 95%
- [ ] 破峰突破检测准确率 > 80%
- [ ] 连续异动统计准确性 100%

### 性能验收

- [ ] 单只股票检测耗时 < 500ms
- [ ] 全市场扫描耗时 < 30s
- [ ] 前端渲染流畅度 > 30fps
- [ ] 状态更新延迟 < 5s

### 代码质量

- [ ] 单元测试覆盖率 > 80%
- [ ] 代码注释完整
- [ ] API文档完善
- [ ] 无严重Bug

---

## 📝 实施时间线

| 日期 | 任务 | 负责人 | 状态 |
|------|------|--------|------|
| Day 1 | 横盘突破检测算法 | Backend | ⏳ |
| Day 2 | 异动状态机完善 | Backend | ⏳ |
| Day 3 | 破峰突破检测 | Backend | ⏳ |
| Day 4 | API集成与测试 | Backend | ⏳ |
| Day 5 | 前端组件开发 | Frontend | ⏳ |
| Day 6 | 集成测试与优化 | Full Stack | ⏳ |
| Day 7 | 文档与发布 | All | ⏳ |

---

**预计完成时间**: 7个工作日

**下一步**: 开始实施 Day 1 - 横盘突破检测算法
