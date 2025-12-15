"""Verify signal was created and accessible via API."""

import asyncio
import json

import redis.asyncio as aioredis


async def main():
    print("=" * 80)
    print("🔍 Verifying Signal Generation")
    print("=" * 80)
    print()

    redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    # Check signals in Redis stream
    print("📊 Checking dfp:signals stream...")
    signals = await redis_client.xread(streams={"dfp:signals": "0"}, count=20)

    if signals:
        print(f"✅ Found {len(signals[0][1])} total signal(s) in stream:\n")
        for stream_name, messages in signals:
            for message_id, message_data in messages[-5:]:  # Show last 5
                signal_payload = json.loads(message_data["payload"])
                print(f"   Signal ID: {message_id}")
                print(f"   ├─ Strategy: {signal_payload.get('strategy')}")
                print(f"   ├─ Symbol: {signal_payload.get('symbol')}")
                print(f"   ├─ Type: {signal_payload.get('signal_type')}")
                print(f"   ├─ Confidence: {signal_payload.get('confidence'):.2%}")
                print(f"   ├─ Strength: {signal_payload.get('strength_score'):.1f}")
                print(f"   ├─ Reasons: {', '.join(signal_payload.get('reasons', []))}")
                print(f"   └─ Triggered: {signal_payload.get('triggered_at')}")
                print()
    else:
        print("⚠️  No signals in stream")

    # Check Signal-API opportunities
    print("🌐 Querying Signal-API (http://localhost:8000/opportunities)...")
    import aiohttp
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/opportunities", timeout=5) as response:
                if response.status == 200:
                    opportunities = await response.json()
                    print(f"✅ Found {len(opportunities)} opportunity(ies):\n")
                    for opp in opportunities[:5]:
                        print(f"   {opp.get('symbol')}:")
                        print(f"   ├─ Type: {opp.get('signal_type')}")
                        print(f"   ├─ Confidence: {opp.get('confidence'):.2%}")
                        print(f"   ├─ Strength: {opp.get('strength_score'):.1f}")
                        print(f"   └─ Time: {opp.get('triggered_at')}")
                        print()
                else:
                    print(f"⚠️  API returned status {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

    # Check via API Gateway
    print("🚪 Querying via API Gateway (http://localhost:8888/opportunities)...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8888/opportunities", timeout=5) as response:
                if response.status == 200:
                    opportunities = await response.json()
                    print(f"✅ Found {len(opportunities)} opportunity(ies) via gateway")
                else:
                    print(f"⚠️  Gateway returned status {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 80)
    print("✅ Verification Complete")
    print("=" * 80)

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())