"""
Shared模块测试
"""

import pytest
from shared.strategies.base import BaseStrategy, SignalResult
from shared.indicators.base import BaseIndicator
from shared.models.market import MarketData, BarData
from shared.models.signal import Signal, SignalType
from datetime import datetime


class TestBaseStrategy:
    """测试策略基类"""
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        # 创建测试策略
        class TestStrategy(BaseStrategy):
            name = "TestStrategy"
            params = {
                'threshold': {'type': 'float', 'range': [1.0, 10.0], 'default': 5.0}
            }
            
            def generate_signal(self, data):
                return None
        
        # 使用默认参数
        strategy = TestStrategy()
        assert strategy.threshold == 5.0
        
        # 使用自定义参数
        strategy2 = TestStrategy(threshold=7.0)
        assert strategy2.threshold == 7.0
    
    def test_signal_result(self):
        """测试信号结果"""
        signal = SignalResult(
            action='BUY',
            confidence=85.0,
            reason='Test signal'
        )
        assert signal.action == 'BUY'
        assert signal.confidence == 85.0


class TestModels:
    """测试数据模型"""
    
    def test_market_data(self):
        """测试市场数据"""
        data = MarketData(
            code='000001',
            name='平安银行',
            current_price=10.5,
            open=10.0,
            high=10.8,
            low=9.9,
            volume=1000000,
            amount=10500000,
            turnover=5.2,
            timestamp=datetime.now()
        )
        assert data.code == '000001'
        assert data.current_price == 10.5
    
    def test_signal(self):
        """测试信号"""
        signal = Signal(
            code='000001',
            name='平安银行',
            signal_type=SignalType.BUY,
            confidence=85.0,
            reason='测试信号',
            strategy='TestStrategy',
            timestamp=datetime.now()
        )
        assert signal.signal_type == SignalType.BUY
        
        # 测试to_dict
        signal_dict = signal.to_dict()
        assert signal_dict['signal_type'] ==  'BUY'
