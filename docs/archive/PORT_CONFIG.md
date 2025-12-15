# 🌪️ 东风破系统端口配置说明

## 📍 固定端口配置

### 东风破系统（当前项目）
- **前端服务**: `http://localhost:3000`
- **后端API**: `http://localhost:9000`
- **API文档**: `http://localhost:9000/docs`

### clean_quant_system（其他项目）
- **前端服务**: `http://localhost:3600`
- **后端API**: `http://localhost:8000`

## 🚨 防混淆注意事项

1. **使用启动脚本**
   ```bash
   # 启动东风破系统
   ./start_dongfeng.sh
   
   # 停止东风破系统
   ./stop_dongfeng.sh
   ```

2. **环境变量固定**
   - 前端已固定端口：`PORT=3000 react-scripts start`
   - 后端启动指定端口：`uvicorn main:app --port 9000`

3. **脚本自动检查**
   - 启动前自动清理端口冲突
   - 显示明确的端口信息
   - 保存PID文件便于管理

4. **记忆口诀**
   ```
   东风破 = 3000端口 (前端)
   clean_quant = 3600端口 (前端)
   
   东风破后端 = 9000
   clean_quant后端 = 8000
   ```

## 🛠️ 端口冲突解决

如果遇到端口占用，可以手动清理：

```bash
# 查看端口占用
lsof -i :3000
lsof -i :9000

# 强制清理（如果需要）
pkill -f "react-scripts.*start"
pkill -f "uvicorn.*main:app.*port.*9000"
```

## 📝 配置文件位置

- `frontend/package.json` - 前端端口固定为3000
- `start_dongfeng.sh` - 启动脚本端口配置
- `backend/main.py` - 后端端口可通过命令行指定

---

**最后提醒：** 请务必使用提供的启动脚本，避免手动启动导致的端口混淆！ 