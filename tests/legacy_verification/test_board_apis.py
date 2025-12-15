"""列出所有板块相关API"""
import akshare as ak

print("查找所有包含'board'的API:")
board_apis = [attr for attr in dir(ak) if 'board' in attr.lower()]
for api in board_apis[:20]:
    print(f"  - {api}")

print("\n查找所有包含'concept'的API:")
concept_apis = [attr for attr in dir(ak) if 'concept' in attr.lower()]
for api in concept_apis[:20]:
    print(f"  - {api}")

print("\n查找所有包含'industry'的API:")
industry_apis = [attr for attr in dir(ak) if 'industry' in attr.lower()]
for api in industry_apis[:20]:
    print(f"  - {api}")
