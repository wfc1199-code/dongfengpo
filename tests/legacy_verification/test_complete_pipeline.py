"""Test complete data pipeline flow.

Flow:
1. Publish clean ticks → Redis Stream (dfp:clean_ticks)
2. Feature-Pipeline consumes and computes features → Redis Pub/Sub (dfp:features)
3. Strategy-Engine evaluates strategies → Redis Stream (dfp:signals)
4. Signal-API exposes opportunities via REST API
"""

import asyncio
import json
import time
from datetime import datetime, timezone

import redis.asyncio as aioredis


async def main():
    print("=" * 80)
    print("🚀 Testing Complete Data Pipeline Flow")
    print("=" * 80)
    print()

    redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    # Step 1: Publish clean ticks to trigger the pipeline
    print("📤 Step 1: Publishing clean tick data to dfp:clean_ticks...")

    now = datetime.now(timezone.utc).isoformat()
    test_tick = {
        "source": "test_adapter",
        "symbol": "000001.SZ",
        "price": 15.50,
        "volume": 125000,
        "turnover": 1937500.0,
        "bid_price": 15.49,
        "bid_volume": 1000,
        "ask_price": 15.51,
        "ask_volume": 800,
        "timestamp": now,
        "ingested_at": now,
        "cleaned_at": now,
        "quality_flags": [],
        "raw": {"change_percent": 5.2},
    }

    payload = json.dumps(test_tick)
    stream_id = await redis_client.xadd(
        name="dfp:clean_ticks",
        fields={"payload": payload},
        maxlen=10000,
        approximate=True
    )
    print(f"✅ Published tick to dfp:clean_ticks (ID: {stream_id})")
    print(f"   Symbol: {test_tick['symbol']}, Price: {test_tick['price']}, Volume: {test_tick['volume']}")
    print()

    # Step 2: Wait for Feature-Pipeline to process and publish features
    print("⏳ Step 2: Waiting for Feature-Pipeline to compute features...")
    await asyncio.sleep(2)

    # Check if features were published to dfp:features channel
    # We'll check the Redis Pub/Sub stats
    pubsub_channels = await redis_client.pubsub_channels("dfp:features")
    print(f"   Feature channel exists: {len(pubsub_channels) > 0}")
    print()

    # Step 3: Check if Strategy-Engine generated signals
    print("🔍 Step 3: Checking for generated signals in dfp:signals stream...")
    await asyncio.sleep(2)

    signals = await redis_client.xread(
        streams={"dfp:signals": "0"},
        count=10
    )

    if signals:
        print(f"✅ Found {len(signals[0][1])} signal(s) in dfp:signals:")
        for stream_name, messages in signals:
            for message_id, message_data in messages:
                signal_payload = json.loads(message_data["payload"])
                print(f"   - Signal ID: {message_id}")
                print(f"     Strategy: {signal_payload.get('strategy')}")
                print(f"     Symbol: {signal_payload.get('symbol')}")
                print(f"     Type: {signal_payload.get('signal_type')}")
                print(f"     Confidence: {signal_payload.get('confidence'):.2%}")
                print(f"     Triggered: {signal_payload.get('triggered_at')}")
    else:
        print("⚠️  No signals found yet")
    print()

    # Step 4: Check Signal-API for opportunities
    print("🌐 Step 4: Querying Signal-API for opportunities...")
    await asyncio.sleep(1)

    import aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/opportunities", timeout=5) as response:
                if response.status == 200:
                    opportunities = await response.json()
                    print(f"✅ Signal-API returned {len(opportunities)} opportunity(ies):")
                    for opp in opportunities[:5]:  # Show first 5
                        print(f"   - {opp.get('symbol')}: {opp.get('signal_type')} "
                              f"(confidence: {opp.get('confidence'):.2%})")
                else:
                    print(f"⚠️  Signal-API returned status {response.status}")
        except Exception as e:
            print(f"❌ Error querying Signal-API: {e}")
    print()

    # Step 5: Verify via API Gateway
    print("🚪 Step 5: Verifying via API Gateway (http://localhost:8888)...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8888/opportunities", timeout=5) as response:
                if response.status == 200:
                    opportunities = await response.json()
                    print(f"✅ API Gateway returned {len(opportunities)} opportunity(ies)")
                else:
                    print(f"⚠️  API Gateway returned status {response.status}")
        except Exception as e:
            print(f"❌ Error querying API Gateway: {e}")
    print()

    # Summary
    print("=" * 80)
    print("📊 Pipeline Test Summary")
    print("=" * 80)
    print("✅ Step 1: Clean tick published to Redis")
    print("⏳ Step 2: Feature-Pipeline processing (check logs)")
    print(f"{'✅' if signals else '⚠️ '} Step 3: Strategy-Engine signal generation")
    print("🌐 Step 4-5: API layer verification")
    print()
    print("💡 Next Steps:")
    print("   1. Check Feature-Pipeline logs for feature computation")
    print("   2. Check Strategy-Engine logs for strategy evaluation")
    print("   3. Monitor Redis streams: dfp:clean_ticks → dfp:features → dfp:signals")
    print()

    await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())