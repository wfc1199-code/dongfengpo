"""Debug script to inspect Redis streams and pub/sub."""

import asyncio
import redis.asyncio as aioredis


async def main():
    print("🔍 Inspecting Redis Data Flow\n")
    print("=" * 80)

    redis_client = await aioredis.from_url("redis://localhost:6379", decode_responses=True)

    # Check clean_ticks stream
    print("\n📊 dfp:clean_ticks Stream:")
    try:
        ticks = await redis_client.xread(streams={"dfp:clean_ticks": "0"}, count=5)
        if ticks:
            print(f"   ✅ Found {len(ticks[0][1])} message(s)")
            for stream_name, messages in ticks:
                for msg_id, msg_data in messages[-3:]:  # Show last 3
                    print(f"      - ID: {msg_id}")
        else:
            print("   ⚠️  Stream is empty")

        # Check consumer groups
        groups = await redis_client.xinfo_groups("dfp:clean_ticks")
        print(f"\n   Consumer Groups ({len(groups)}):")
        for group in groups:
            print(f"      - {group['name']}: {group['consumers']} consumers, {group['pending']} pending")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check signals stream
    print("\n📊 dfp:signals Stream:")
    try:
        signals = await redis_client.xread(streams={"dfp:signals": "0"}, count=5)
        if signals:
            print(f"   ✅ Found {len(signals[0][1])} signal(s)")
        else:
            print("   ⚠️  Stream is empty")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Check pub/sub channel
    print("\n📡 Pub/Sub Channels:")
    try:
        channels = await redis_client.pubsub_channels("dfp:*")
        print(f"   Active channels: {len(channels)}")
        for ch in channels:
            numsub = await redis_client.pubsub_numsub(ch)
            print(f"      - {ch}: {numsub[0][1]} subscribers")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Try to consume from dfp:clean_ticks with the feature-pipeline group
    print("\n🔄 Simulating Feature-Pipeline Consumer:")
    try:
        # Read pending messages
        pending = await redis_client.xpending("dfp:clean_ticks", "feature-pipeline-group")
        print(f"   Pending messages: {pending['pending']}")

        # Try to read new messages
        result = await redis_client.xreadgroup(
            groupname="feature-pipeline-group",
            consumername="test-consumer",
            streams={"dfp:clean_ticks": ">"},
            count=1,
            block=100
        )
        if result:
            print(f"   ✅ Successfully read {len(result[0][1])} new message(s)")
        else:
            print("   ⚠️  No new messages available")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "=" * 80)
    print()

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())