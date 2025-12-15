# TODO清理实施方案

## 概述
项目中共发现10个TODO注释，分布在3个核心文件中。本方案提供具体的实施步骤和代码示例。

## 一、高优先级TODO修复

### 1.1 数据源集成（market_capture.py - Line 165）

**当前代码：**
```python
async def _fetch_market_data(self):
    # TODO: 从data_manager获取实时数据
    # 现在返回模拟数据
```

**修复方案：**
```python
async def _fetch_market_data(self):
    """从数据管理器获取实时市场数据"""
    try:
        # 获取数据源实例
        from ..core.hybrid_data_source import HybridDataSource
        data_source = HybridDataSource()
        
        # 获取市场概览数据
        market_overview = await data_source.get_market_overview()
        
        # 获取涨跌分布
        distribution = await data_source.get_market_distribution()
        
        return {
            'overview': market_overview,
            'distribution': distribution,
            'timestamp': datetime.now()
        }
    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        # 降级到模拟数据
        return self._get_mock_market_data()
```

### 1.2 WebSocket推送实现（realistic_updater.py - Line 261）

**当前代码：**
```python
async def push_updates(self, updates: List[Dict]):
    # TODO: 实现WebSocket推送
    pass
```

**修复方案：**
```python
async def push_updates(self, updates: List[Dict]):
    """通过WebSocket推送更新"""
    try:
        from ..api.websocket_routes import get_ws_manager
        ws_manager = get_ws_manager()
        
        for update in updates:
            # 构造推送消息
            message = {
                'type': 'stock_update',
                'data': update,
                'timestamp': datetime.now().isoformat()
            }
            
            # 推送到订阅了该股票的客户端
            await ws_manager.broadcast(
                json.dumps(message),
                channel=f"stock:{update['code']}"
            )
            
        logger.info(f"成功推送 {len(updates)} 条更新")
        
    except Exception as e:
        logger.error(f"WebSocket推送失败: {e}")
```

### 1.3 真实数据源切换（limit_up_predictor_enhanced.py - Line 51）

**修复方案：**
```python
async def _get_realtime_market_data(self) -> List[Dict[str, Any]]:
    """获取实时市场数据"""
    try:
        # 从配置决定是否使用真实数据
        use_real_data = os.getenv('USE_REAL_DATA', 'false').lower() == 'true'
        
        if use_real_data and HAS_AKSHARE:  # 检查akshare是否可用
            import asyncio
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(None, ak.stock_zh_a_spot_em)
            
            # 筛选涨幅在5%以上但未涨停的股票
            df_filtered = df[(df['涨跌幅'] >= 5.0) & (df['涨跌幅'] < 9.8)]
            
            # 转换数据格式
            return self._convert_akshare_data(df_filtered)
        else:
            # 使用模拟数据
            return self._get_mock_prediction_data()
            
    except Exception as e:
        logger.error(f"获取实时数据失败: {e}")
        return self._get_mock_prediction_data()
```

## 二、中优先级TODO修复

### 2.1 市场情绪分析（market_capture.py - Line 181）

**修复方案：**
```python
async def _analyze_market_sentiment(self, market_data: Dict) -> Dict:
    """分析市场情绪"""
    try:
        # 获取涨跌家数
        up_count = market_data.get('up_count', 0)
        down_count = market_data.get('down_count', 0)
        limit_up_count = market_data.get('limit_up_count', 0)
        limit_down_count = market_data.get('limit_down_count', 0)
        
        # 计算市场宽度
        total_stocks = up_count + down_count
        breadth = (up_count - down_count) / max(total_stocks, 1)
        
        # 计算情绪分数
        sentiment_score = (
            breadth * 40 +  # 市场宽度权重40%
            (limit_up_count / max(total_stocks, 1)) * 30 +  # 涨停比例30%
            (1 - limit_down_count / max(total_stocks, 1)) * 30  # 跌停比例30%
        ) * 100
        
        # 判断情绪等级
        if sentiment_score >= 80:
            sentiment_level = 'extreme_greed'
        elif sentiment_score >= 60:
            sentiment_level = 'greed'
        elif sentiment_score >= 40:
            sentiment_level = 'neutral'
        elif sentiment_score >= 20:
            sentiment_level = 'fear'
        else:
            sentiment_level = 'extreme_fear'
        
        return {
            'score': round(sentiment_score, 2),
            'level': sentiment_level,
            'breadth': round(breadth, 4),
            'up_down_ratio': f"{up_count}:{down_count}",
            'limit_up_count': limit_up_count,
            'limit_down_count': limit_down_count
        }
        
    except Exception as e:
        logger.error(f"市场情绪分析失败: {e}")
        return {'score': 50, 'level': 'neutral'}
```

### 2.2 板块分析（market_capture.py - Line 193）

**修复方案：**
```python
async def _analyze_sectors(self, market_data: Dict) -> Dict:
    """分析板块表现"""
    try:
        # 获取板块数据
        sector_data = market_data.get('sectors', [])
        
        # 按涨幅排序
        sorted_sectors = sorted(
            sector_data, 
            key=lambda x: x.get('change_percent', 0), 
            reverse=True
        )
        
        # 获取领涨/领跌板块
        top_sectors = sorted_sectors[:5]
        bottom_sectors = sorted_sectors[-5:]
        
        # 计算板块轮动强度
        rotation_strength = self._calculate_rotation_strength(sector_data)
        
        return {
            'top_sectors': [
                {
                    'name': s['name'],
                    'change_percent': s['change_percent'],
                    'leading_stocks': s.get('leading_stocks', [])
                }
                for s in top_sectors
            ],
            'bottom_sectors': [
                {
                    'name': s['name'],
                    'change_percent': s['change_percent']
                }
                for s in bottom_sectors
            ],
            'rotation_strength': rotation_strength,
            'active_count': len([s for s in sector_data if abs(s.get('change_percent', 0)) > 1])
        }
        
    except Exception as e:
        logger.error(f"板块分析失败: {e}")
        return {}
```

### 2.3 资金流向分析（market_capture.py - Line 212）

**修复方案：**
```python
async def _analyze_money_flow(self, market_data: Dict) -> Dict:
    """分析资金流向"""
    try:
        # 获取资金流向数据
        money_flow = market_data.get('money_flow', {})
        
        # 计算主力资金净流入
        main_net_inflow = money_flow.get('main_net_inflow', 0)
        
        # 计算各类资金占比
        total_inflow = money_flow.get('total_inflow', 1)
        main_ratio = money_flow.get('main_inflow', 0) / total_inflow * 100
        retail_ratio = money_flow.get('retail_inflow', 0) / total_inflow * 100
        
        # 判断资金流向
        if main_net_inflow > 0:
            flow_direction = 'inflow'
            flow_strength = min(abs(main_net_inflow) / 1000000000, 1) * 100  # 亿为单位
        else:
            flow_direction = 'outflow'
            flow_strength = min(abs(main_net_inflow) / 1000000000, 1) * 100
        
        return {
            'main_net_inflow': round(main_net_inflow / 100000000, 2),  # 亿元
            'flow_direction': flow_direction,
            'flow_strength': round(flow_strength, 2),
            'main_ratio': round(main_ratio, 2),
            'retail_ratio': round(retail_ratio, 2),
            'sectors_inflow': money_flow.get('sectors_inflow', {})
        }
        
    except Exception as e:
        logger.error(f"资金流向分析失败: {e}")
        return {}
```

## 三、实施步骤

### 第一阶段（1-2天）
1. 实现数据源集成（market_capture.py）
2. 配置环境变量控制真实/模拟数据切换
3. 添加单元测试验证数据获取

### 第二阶段（2-3天）
1. 实现WebSocket推送功能
2. 集成前端WebSocket客户端
3. 测试实时数据推送

### 第三阶段（3-5天）
1. 实现所有分析逻辑（市场情绪、板块、资金流向等）
2. 添加异常处理和降级方案
3. 性能优化和压力测试

### 第四阶段（1-2天）
1. 集成测试
2. 文档更新
3. 代码审查和优化

## 四、测试计划

### 单元测试
- 每个TODO修复后立即添加对应的单元测试
- 测试覆盖率目标：85%以上

### 集成测试
- 测试真实数据源切换
- 测试WebSocket连接稳定性
- 测试各分析模块的准确性

### 性能测试
- 并发WebSocket连接测试（目标：1000+连接）
- 数据处理延迟测试（目标：<100ms）
- 内存占用测试

## 五、风险控制

1. **数据源风险**：保留模拟数据作为备份
2. **性能风险**：实现缓存和限流机制
3. **稳定性风险**：添加熔断和自动恢复机制
4. **兼容性风险**：使用特性开关逐步上线

## 六、完成标准

- [ ] 所有TODO注释被移除或转换为正式文档
- [ ] 每个实现都有对应的单元测试
- [ ] 代码通过lint检查
- [ ] 功能在生产环境验证通过
- [ ] 相关文档已更新

---
*创建时间：2025-08-19*  
*预计完成时间：7-10个工作日*