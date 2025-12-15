import sys
sys.path.append('/Users/wangfangchun/东风破/backend')

close_price = 35.4
high_price = 65.0
volume = 43615
amount = 196359280.0

print(f"收盘价: {close_price}")
print(f"最高价: {high_price}")
print(f"最高价/收盘价 = {high_price/close_price:.2f}倍")

print(f"\n成交量: {volume}")
print(f"成交额: {amount:,.2f}")

# 计算合理成交额
reasonable_amount = volume * close_price * 10
print(f"合理成交额: {reasonable_amount:,.2f}")
print(f"实际/合理 = {amount/reasonable_amount:.2f}倍")

# 检查条件
if high_price > close_price * 1.5:
    print(f"\n✓ 最高价超过收盘价150%，应该修正")
else:
    print(f"\n✗ 最高价未超过收盘价150%")

if amount > reasonable_amount * 10:
    print(f"✓ 成交额超过合理值10倍，应该修正")
else:
    print(f"✗ 成交额未超过合理值10倍")
