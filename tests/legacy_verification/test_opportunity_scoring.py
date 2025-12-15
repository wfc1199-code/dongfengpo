#!/usr/bin/env python3
"""测试机会评分和筛选逻辑"""

import redis
import json
from typing import Dict, List

def calculate_score(opportunity: Dict) -> int:
    """计算综合评分 - 与前端逻辑保持一致"""
    score = 0

    # 1. 信心度权重 40%
    confidence = opportunity.get('confidence', 0)
    score += confidence * 40

    # 2. 强度分权重 30%
    strength = opportunity.get('strength_score', 0)
    score += (strength / 100) * 30

    # 3. 信号数量加分 15%
    signals = opportunity.get('signals', [])
    signal_bonus = min(len(signals) * 3, 15)
    score += signal_bonus

    # 4. 趋势加分 15%
    score += 15  # 当前固定15分

    return round(score)

def calculate_predicted_gain(opportunity: Dict) -> float:
    """计算预期涨幅"""
    confidence = opportunity.get('confidence', 0)
    strength = opportunity.get('strength_score', 0)
    base_gain = (confidence * strength) / 10
    return round(base_gain * 10) / 10

def assess_risk_level(opportunity: Dict) -> str:
    """评估风险等级"""
    confidence = opportunity.get('confidence', 0)
    if confidence >= 0.8:
        return 'low'
    elif confidence >= 0.6:
        return 'medium'
    return 'high'

def get_stars(score: int) -> str:
    """获取星级评价"""
    if score >= 90:
        return '⭐⭐⭐⭐⭐'
    elif score >= 80:
        return '⭐⭐⭐⭐'
    elif score >= 70:
        return '⭐⭐⭐'
    elif score >= 60:
        return '⭐⭐'
    return '⭐'

def main():
    """主测试函数"""
    print("=" * 80)
    print("🧮 机会评分和筛选功能测试")
    print("=" * 80)
    print()

    # 连接Redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # 获取交易机会
    opportunities = r.xread({'dfp:opportunities': '0'}, count=100)

    if not opportunities:
        print("❌ 暂无交易机会数据")
        return

    print(f"📊 共获取 {len(opportunities[0][1])} 条机会数据\n")

    # 解析和评分
    scored_opportunities = []
    for msg_id, data in opportunities[0][1]:
        try:
            # 优先尝试 'payload' 字段，其次尝试 'data' 字段
            opp_data = json.loads(data.get('payload') or data.get('data', '{}'))

            # 计算各项指标
            score = calculate_score(opp_data)
            predicted_gain = calculate_predicted_gain(opp_data)
            risk_level = assess_risk_level(opp_data)
            stars = get_stars(score)
            is_hot = score >= 90

            # 保存结果
            result = {
                'symbol': opp_data.get('symbol', 'N/A'),
                'confidence': opp_data.get('confidence', 0),
                'strength_score': opp_data.get('strength_score', 0),
                'signals': opp_data.get('signals', []),
                'score': score,
                'predicted_gain': predicted_gain,
                'risk_level': risk_level,
                'stars': stars,
                'is_hot': is_hot
            }
            scored_opportunities.append(result)
        except Exception as e:
            print(f"⚠️  解析数据失败: {e}")

    if not scored_opportunities:
        print("❌ 没有有效的机会数据")
        return

    # 按评分排序
    scored_opportunities.sort(key=lambda x: x['score'], reverse=True)

    print("🏆 评分排行榜 (Top 10)")
    print("-" * 80)
    for i, opp in enumerate(scored_opportunities[:10], 1):
        hot_badge = "🔥 " if opp['is_hot'] else "   "
        print(f"{hot_badge}{i:2d}. {opp['symbol']:12s} | "
              f"评分:{opp['score']:3d} {opp['stars']} | "
              f"信心:{opp['confidence']:.2f} | "
              f"强度:{opp['strength_score']:3.0f} | "
              f"涨幅:+{opp['predicted_gain']:.1f}% | "
              f"风险:{opp['risk_level']}")

    print()
    print("=" * 80)
    print("📈 筛选功能测试")
    print("=" * 80)
    print()

    # 测试筛选功能
    high_confidence = [o for o in scored_opportunities if o['confidence'] >= 0.8]
    high_score = [o for o in scored_opportunities if o['score'] >= 85]
    low_risk = [o for o in scored_opportunities if o['risk_level'] == 'low']

    print(f"🎯 筛选结果:")
    print(f"   - 高信心 (≥80%): {len(high_confidence)} 个")
    print(f"   - 高评分 (≥85):  {len(high_score)} 个")
    print(f"   - 低风险:        {len(low_risk)} 个")
    print()

    # 组合筛选
    combo_filter = [o for o in scored_opportunities
                    if o['confidence'] >= 0.8 and o['score'] >= 85 and o['risk_level'] == 'low']

    print(f"🔥 三重筛选 (高信心 + 高评分 + 低风险): {len(combo_filter)} 个")
    if combo_filter:
        print("-" * 80)
        for opp in combo_filter:
            print(f"   🚀 {opp['symbol']} | "
                  f"评分:{opp['score']} | "
                  f"涨幅:+{opp['predicted_gain']}% | "
                  f"{opp['stars']}")

    print()
    print("=" * 80)
    print("📊 统计分析")
    print("=" * 80)
    print()

    # 统计分析
    avg_score = sum(o['score'] for o in scored_opportunities) / len(scored_opportunities)
    avg_confidence = sum(o['confidence'] for o in scored_opportunities) / len(scored_opportunities)
    avg_gain = sum(o['predicted_gain'] for o in scored_opportunities) / len(scored_opportunities)

    risk_dist = {
        'low': len([o for o in scored_opportunities if o['risk_level'] == 'low']),
        'medium': len([o for o in scored_opportunities if o['risk_level'] == 'medium']),
        'high': len([o for o in scored_opportunities if o['risk_level'] == 'high'])
    }

    star_dist = {}
    for opp in scored_opportunities:
        stars = len(opp['stars']) // 3  # 每个星3个字符
        star_dist[stars] = star_dist.get(stars, 0) + 1

    print(f"📈 平均指标:")
    print(f"   - 平均评分: {avg_score:.1f}")
    print(f"   - 平均信心: {avg_confidence:.1%}")
    print(f"   - 平均预期涨幅: +{avg_gain:.1f}%")
    print()

    print(f"⚠️  风险分布:")
    print(f"   - 低风险: {risk_dist['low']} ({risk_dist['low']/len(scored_opportunities):.1%})")
    print(f"   - 中风险: {risk_dist['medium']} ({risk_dist['medium']/len(scored_opportunities):.1%})")
    print(f"   - 高风险: {risk_dist['high']} ({risk_dist['high']/len(scored_opportunities):.1%})")
    print()

    print(f"⭐ 星级分布:")
    for stars in sorted(star_dist.keys(), reverse=True):
        count = star_dist[stars]
        percentage = count / len(scored_opportunities)
        star_str = '⭐' * stars
        print(f"   - {star_str}: {count} ({percentage:.1%})")

    print()
    print("=" * 80)
    print("✅ 测试完成")
    print("=" * 80)

if __name__ == '__main__':
    main()