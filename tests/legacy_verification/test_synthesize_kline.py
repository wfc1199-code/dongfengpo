#!/usr/bin/env python3
"""测试从分时数据合成K线"""

def _synthesize_kline_from_minute_simple(minute_data: list, period_minutes: int, count: int) -> list:
    """从分时数据合成K线（简化版）
    
    Args:
        minute_data: 分时数据列表，格式: [{'time': '09:30', 'price': 255.88, ...}, ...]
        period_minutes: K线周期（分钟），如5、15、30
        count: 需要的K线条数
    
    Returns:
        合成的K线数据列表
    """
    if not minute_data or period_minutes <= 0:
        return []
    
    klines = []
    buffer = []  # 临时缓冲
    current_period_start = None
    
    for item in minute_data:
        time_str = item['time']  # "09:30"
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])
        
        # 计算从09:30开始的分钟数
        if hour < 13:
            # 上午: 09:30-11:30
            minutes_from_start = (hour - 9) * 60 + (minute - 30)
        else:
            # 下午: 13:00-15:00，加上120分钟（上午2小时）
            minutes_from_start = 120 + (hour - 13) * 60 + minute
        
        # 当前周期索引
        period_index = minutes_from_start // period_minutes
        
        if current_period_start is None:
            current_period_start = period_index
        
        # 检查是否进入新周期
        if period_index != current_period_start:
            # 完成当前K线
            if buffer:
                kline = _create_kline_from_buffer(buffer)
                if kline:
                    klines.append(kline)
            buffer = []
            current_period_start = period_index
        
        # 添加到缓冲
        buffer.append(item)
    
    # 处理最后一组
    if buffer:
        kline = _create_kline_from_buffer(buffer)
        if kline:
            klines.append(kline)
    
    # 返回最近count条
    return klines[-count:] if len(klines) > count else klines

def _create_kline_from_buffer(buffer: list) -> dict:
    """从缓冲数据创建一根K线"""
    if not buffer:
        return None
    
    open_price = buffer[0]['price']
    close_price = buffer[-1]['price']
    high_price = max(item['price'] for item in buffer)
    low_price = min(item['price'] for item in buffer)
    
    # 成交量求和（增量）
    volume = sum(item.get('volume', 0) for item in buffer)
    amount = sum(item.get('amount', 0) for item in buffer)
    
    # 时间=第一条的时间
    date_str = buffer[0]['time']
    
    return {
        'date': date_str,
        'open': round(open_price, 2),
        'close': round(close_price, 2),
        'high': round(high_price, 2),
        'low': round(low_price, 2),
        'volume': volume,
        'amount': amount
    }

# 测试
if __name__ == '__main__':
    # 模拟分时数据
    minute_data = [
        {'time': '09:30', 'price': 255.88, 'volume': 100, 'amount': 25588},
        {'time': '09:31', 'price': 256.00, 'volume': 120, 'amount': 30720},
        {'time': '09:32', 'price': 255.50, 'volume': 90, 'amount': 22995},
        {'time': '09:33', 'price': 256.20, 'volume': 110, 'amount': 28182},
        {'time': '09:34', 'price': 255.90, 'volume': 95, 'amount': 24310},
        # 新的5分钟周期
        {'time': '09:35', 'price': 256.50, 'volume': 130, 'amount': 33345},
        {'time': '09:36', 'price': 256.80, 'volume': 140, 'amount': 35952},
        {'time': '09:37', 'price': 256.30, 'volume': 100, 'amount': 25630},
        {'time': '09:38', 'price': 257.00, 'volume': 150, 'amount': 38550},
        {'time': '09:39', 'price': 256.70, 'volume': 120, 'amount': 30804},
    ]
    
    print('=== 测试5分钟K线合成 ===\n')
    klines_5min = _synthesize_kline_from_minute_simple(minute_data, 5, 10)
    
    print(f'合成了 {len(klines_5min)} 条5分钟K线:\n')
    for i, kline in enumerate(klines_5min, 1):
        print(f'{i}. {kline["date"]} - 开¥{kline["open"]} 高¥{kline["high"]} 低¥{kline["low"]} 收¥{kline["close"]} 量{kline["volume"]}')
    
    print('\n=== 验证 ===')
    if len(klines_5min) == 2:
        print('✅ 10条分时数据合成2条5分钟K线')
        k1 = klines_5min[0]
        if k1['open'] == 255.88 and k1['close'] == 255.90:
            print('✅ 第1条K线: 开盘=第1条分时价格, 收盘=第5条分时价格')
        if k1['high'] == 256.20 and k1['low'] == 255.50:
            print('✅ 第1条K线: 最高最低价正确')
