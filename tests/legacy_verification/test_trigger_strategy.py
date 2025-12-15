"""Test script to trigger a strategy signal with realistic data."""

import asyncio
import json
from datetime import datetime, timezone, timedelta

import redis.asyncio as aioredis


async def send_rapid_rise_ticks():
    """Send a sequence of ticks showing rapid price rise."""
    print("🚀 Sending rapid price rise ticks to trigger strategy...\n")

    redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    # Simulate rapid 5% rise over 5 ticks
    base_time = datetime.now(timezone.utc)
    base_price = 10.00
    symbol = "000001.SZ"

    ticks = []
    for i in range(6):  # 6 ticks to show clear upward trend
        tick_time = (base_time + timedelta(seconds=i)).isoformat()
        price = base_price * (1 + 0.01 * i)  # 1% increase per tick = 5% total

        tick = {
            "source": "test_adapter",
            "symbol": symbol,
            "price": round(price, 2),
            "volume": 20000 + i * 5000,  # Increasing volume
            "turnover": round(price * (20000 + i * 5000) * 100, 2),
            "bid_price": round(price - 0.01, 2),
            "bid_volume": 1000,
            "ask_price": round(price + 0.01, 2),
            "ask_volume": 800,
            "timestamp": tick_time,
            "ingested_at": tick_time,
            "cleaned_at": tick_time,
            "quality_flags": [],
            "raw": {},
        }
        ticks.append(tick)

    # Send ticks with small delays
    for i, tick in enumerate(ticks):
        payload = json.dumps(tick)
        stream_id = await redis_client.xadd(
            name="dfp:clean_ticks",
            fields={"payload": payload},
            maxlen=10000,
            approximate=True
        )
        print(f"📤 Tick {i+1}/6: {symbol} @ {tick['price']:.2f} (volume: {tick['volume']:,})")
        await asyncio.sleep(0.2)  # Small delay between ticks

    print("\n✅ All ticks sent! Waiting for pipeline processing...")
    await asyncio.sleep(3)  # Wait for processing

    # Check for signals
    print("\n🔍 Checking for generated signals...")
    signals = await redis_client.xread(
        streams={"dfp:signals": "0"},
        count=10
    )

    if signals:
        print(f"✨ Found {len(signals[0][1])} signal(s):")
        for stream_name, messages in signals:
            for message_id, message_data in messages:
                signal_payload = json.loads(message_data["payload"])
                print(f"\n   📊 Signal Details:")
                print(f"      Strategy: {signal_payload.get('strategy')}")
                print(f"      Symbol: {signal_payload.get('symbol')}")
                print(f"      Type: {signal_payload.get('signal_type')}")
                print(f"      Confidence: {signal_payload.get('confidence'):.2%}")
                print(f"      Strength: {signal_payload.get('strength_score'):.1f}")
                print(f"      Reasons: {', '.join(signal_payload.get('reasons', []))}")
                print(f"      Triggered: {signal_payload.get('triggered_at')}")
    else:
        print("⚠️  No signals generated")

    # Check API
    print("\n🌐 Checking Signal-API...")
    import aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/opportunities", timeout=5) as response:
                if response.status == 200:
                    opportunities = await response.json()
                    print(f"   ✅ Found {len(opportunities)} opportunity(ies) in API")
                    for opp in opportunities[:3]:
                        print(f"      - {opp.get('symbol')}: {opp.get('signal_type')} "
                              f"(confidence: {opp.get('confidence'):.2%})")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("✅ Test complete!")
    print("=" * 80)

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(send_rapid_rise_ticks())