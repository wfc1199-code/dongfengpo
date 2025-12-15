#!/usr/bin/env python3
"""Test SDK integration with strategy-engine."""

import sys
import os

# Add project root to Python path to find strategies/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from strategy_engine.config import StrategyConfig
from strategy_engine.loader import load_strategies
from strategy_engine.models import FeatureSnapshot
from datetime import datetime


def test_load_sdk_strategy():
    """Test loading a strategy from SDK."""
    print("🧪 Testing SDK Strategy Loading...")

    # Configure SDK strategy
    config = StrategyConfig(
        name="rapid-rise-sdk",
        module="sdk:strategies.official.rapid_rise.strategy",
        class_name="RapidRiseStrategy",
        parameters={}  # SDK strategies use initialize() method, not __init__ parameters
    )

    try:
        strategies = load_strategies([config])
        if not strategies:
            print("❌ Failed to load SDK strategy")
            return False

        print(f"✅ Successfully loaded {len(strategies)} strategy(ies)")
        print(f"   Strategy names: {list(strategies.keys())}")

        # Test evaluation
        strategy = strategies["rapid-rise-sdk"]
        test_feature = FeatureSnapshot(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            window="300s",  # 5 minutes
            price=100.0,
            change_percent=5.5,
            volume_sum=5000000,
            avg_price=99.0,
            max_price=101.0,
            min_price=98.0,
            turnover_sum=500000000.0,
            sample_size=100
        )

        print("\n🔍 Testing Strategy Evaluation...")
        signal = strategy.evaluate(test_feature)

        if signal:
            print(f"✅ Strategy generated signal:")
            print(f"   Type: {signal.signal_type}")
            print(f"   Symbol: {signal.symbol}")
            print(f"   Confidence: {signal.confidence}")
        else:
            print("ℹ️  Strategy did not generate signal (expected if conditions not met)")

        return True

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_traditional_strategy():
    """Test loading a traditional strategy-engine strategy."""
    print("\n🧪 Testing Traditional Strategy Loading...")

    config = StrategyConfig(
        name="rapid-rise-traditional",
        module="strategy_engine.strategies.rapid_rise",
        class_name="RapidRiseStrategy",
        parameters={"min_change": 2.0, "min_volume": 50000}
    )

    try:
        strategies = load_strategies([config])
        if strategies:
            print(f"✅ Successfully loaded traditional strategy")
            return True
        else:
            print("❌ Failed to load traditional strategy")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Strategy Engine - SDK Integration Test")
    print("=" * 60)

    test1_passed = test_traditional_strategy()
    test2_passed = test_load_sdk_strategy()

    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Traditional Strategy: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  SDK Strategy: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print("=" * 60)

    sys.exit(0 if (test1_passed and test2_passed) else 1)