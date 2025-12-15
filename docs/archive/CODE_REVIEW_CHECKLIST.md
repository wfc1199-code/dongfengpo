# 代码审查检查清单

## 🎯 代码审查目标
- 提高代码质量
- 发现潜在问题
- 知识共享
- 统一编码风格

## ✅ 通用检查项

### 1. 功能性 Functionality
- [ ] 代码是否实现了需求描述的功能？
- [ ] 边界条件是否处理？
- [ ] 错误处理是否完善？
- [ ] 是否有遗漏的场景？

### 2. 代码质量 Code Quality
- [ ] 代码是否简洁易懂？
- [ ] 变量/函数命名是否清晰？
- [ ] 是否遵循DRY原则（Don't Repeat Yourself）？
- [ ] 是否遵循SOLID原则？
- [ ] 复杂度是否可以降低？

### 3. 性能 Performance
- [ ] 是否有明显的性能问题？
- [ ] 数据库查询是否优化（避免N+1）？
- [ ] 是否有不必要的循环或计算？
- [ ] 缓存使用是否合理？
- [ ] 异步处理是否恰当？

### 4. 安全性 Security
- [ ] 是否有SQL注入风险？
- [ ] 是否有XSS攻击风险？
- [ ] 敏感信息是否加密？
- [ ] 权限校验是否完整？
- [ ] 输入验证是否充分？

### 5. 测试 Testing
- [ ] 是否有对应的单元测试？
- [ ] 测试覆盖率是否足够（>70%）？
- [ ] 测试用例是否包含边界条件？
- [ ] 是否有集成测试？

### 6. 文档 Documentation
- [ ] 复杂逻辑是否有注释？
- [ ] API是否有文档？
- [ ] README是否更新？
- [ ] 变更日志是否记录？

## 🐍 Python特定检查项

### 代码风格
- [ ] 是否符合PEP 8规范？
- [ ] 使用black格式化？
- [ ] import语句是否规范？
- [ ] 类型注解是否完整？

### 最佳实践
```python
# ✅ 好的做法
def calculate_discount(price: float, discount_rate: float) -> float:
    """计算折扣后的价格
    
    Args:
        price: 原价
        discount_rate: 折扣率（0-1之间）
    
    Returns:
        折扣后的价格
    """
    if not 0 <= discount_rate <= 1:
        raise ValueError("折扣率必须在0-1之间")
    return price * (1 - discount_rate)

# ❌ 不好的做法
def calc(p, d):
    return p * (1 - d)
```

### 异步处理
- [ ] async/await使用是否正确？
- [ ] 是否有阻塞操作？
- [ ] 并发控制是否合理？

## ⚛️ React/TypeScript特定检查项

### 组件设计
- [ ] 组件职责是否单一？
- [ ] Props定义是否清晰？
- [ ] 是否过度渲染？
- [ ] Hooks使用是否规范？

### 最佳实践
```typescript
// ✅ 好的做法
interface StockCardProps {
  stock: Stock;
  onSelect?: (stock: Stock) => void;
}

const StockCard: React.FC<StockCardProps> = React.memo(({ stock, onSelect }) => {
  const handleClick = useCallback(() => {
    onSelect?.(stock);
  }, [stock, onSelect]);
  
  return (
    <div onClick={handleClick}>
      {stock.name}
    </div>
  );
});

// ❌ 不好的做法
const StockCard = ({ data, callback }) => {
  return <div onClick={() => callback(data)}>{data.n}</div>;
};
```

### 状态管理
- [ ] 状态是否最小化？
- [ ] 是否避免了不必要的状态？
- [ ] 副作用是否正确处理？

## 📊 严重程度分级

### 🔴 必须修复 (Blocker)
- 安全漏洞
- 数据丢失风险
- 系统崩溃
- 严重性能问题

### 🟡 建议修复 (Major)
- 代码质量问题
- 潜在bug
- 性能优化
- 代码规范

### 🟢 可选改进 (Minor)
- 代码风格
- 命名优化
- 注释完善
- 重构建议

## 📝 审查流程

### 1. 自查阶段
提交前开发者自查：
```bash
# 运行测试
./scripts/test_runner.sh

# 检查代码规范
black backend/
npm run lint

# 确认功能
手动测试主要流程
```

### 2. 审查阶段
审查者检查：
1. 阅读PR描述，理解变更背景
2. 查看文件变更列表
3. 逐行审查代码
4. 运行并测试功能
5. 提供反馈

### 3. 反馈格式
```markdown
## 总体评价
[总体评价和建议]

## 必须修复
- [ ] [问题描述] - [文件:行号]

## 建议改进
- [ ] [建议描述] - [文件:行号]

## 亮点
- ✨ [值得表扬的地方]
```

## 🚀 快速审查命令

```bash
# 查看变更统计
git diff --stat

# 查看具体变更
git diff main...feature-branch

# 检查代码质量
./scripts/test_runner.sh

# 检查性能影响
python backend/tests/performance_test.py
```

## 💡 审查技巧

### Do's ✅
- 保持友善和建设性
- 提供具体的改进建议
- 解释为什么需要修改
- 认可好的实践
- 及时响应

### Don'ts ❌
- 人身攻击
- 过度挑剔
- 忽视安全问题
- 延迟审查
- 强加个人偏好

## 📚 参考资源
- [Google代码审查指南](https://google.github.io/eng-practices/review/)
- [Python最佳实践](https://docs.python-guide.org/)
- [React最佳实践](https://react.dev/learn/thinking-in-react)
- [TypeScript手册](https://www.typescriptlang.org/docs/)

---

*版本: v1.0*  
*更新日期: 2025-08-09*