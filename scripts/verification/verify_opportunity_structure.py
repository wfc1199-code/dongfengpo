#!/usr/bin/env python3
"""验证Redis中机会数据的结构"""

import redis
import json
from pprint import pprint

def main():
    print("=" * 80)
    print("🔍 机会数据结构验证")
    print("=" * 80)
    print()

    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # 获取一条机会数据
    opportunities = r.xread({'dfp:opportunities': '0'}, count=1)

    if not opportunities:
        print("❌ 暂无机会数据")
        return

    msg_id, data = opportunities[0][1][0]

    print(f"📊 消息ID: {msg_id}")
    print()
    print("📦 原始数据 (Redis Stream 格式):")
    print("-" * 80)
    for key, value in data.items():
        print(f"  {key}: {value[:100]}..." if len(value) > 100 else f"  {key}: {value}")
    print()

    # 解析JSON
    if 'payload' in data:
        opp_data = json.loads(data['payload'])
    else:
        opp_data = json.loads(data.get('data', '{}'))

    print("📋 解析后的机会数据结构:")
    print("-" * 80)
    pprint(opp_data, indent=2, width=80)
    print()

    print("📌 核心字段检查:")
    print("-" * 80)
    required_fields = ['id', 'symbol', 'state', 'confidence', 'strength_score', 'signals']
    for field in required_fields:
        value = opp_data.get(field, 'N/A')
        status = "✅" if field in opp_data else "❌"
        print(f"  {status} {field}: {value}")
    print()

    print("🎯 评分相关字段:")
    print("-" * 80)
    print(f"  - confidence (信心度): {opp_data.get('confidence', 0):.2f}")
    print(f"  - strength_score (强度分): {opp_data.get('strength_score', 0):.2f}")
    print(f"  - signals (信号列表): {len(opp_data.get('signals', []))} 个")
    print()

    # 计算评分
    confidence = opp_data.get('confidence', 0)
    strength = opp_data.get('strength_score', 0)
    signal_count = len(opp_data.get('signals', []))

    score = confidence * 40 + (strength / 100) * 30 + min(signal_count * 3, 15) + 15
    predicted_gain = (confidence * strength) / 10

    print("🧮 前端评分算法测试:")
    print("-" * 80)
    print(f"  - 信心度贡献: {confidence * 40:.1f} 分 (权重40%)")
    print(f"  - 强度分贡献: {(strength / 100) * 30:.1f} 分 (权重30%)")
    print(f"  - 信号数贡献: {min(signal_count * 3, 15):.1f} 分 (权重15%)")
    print(f"  - 趋势加分: 15.0 分 (权重15%)")
    print(f"  - 综合评分: {round(score)} 分")
    print(f"  - 预期涨幅: +{round(predicted_gain * 10) / 10:.1f}%")
    print()

    # 风险评估
    if confidence >= 0.8:
        risk = "低风险 🟢"
    elif confidence >= 0.6:
        risk = "中风险 🟡"
    else:
        risk = "高风险 🔴"

    print(f"⚠️  风险评估: {risk}")
    print()

    print("=" * 80)
    print("✅ 验证完成")
    print("=" * 80)

if __name__ == '__main__':
    main()