# signal-streamer

信号实时推送服务：
- 订阅 Redis 频道 `dfp:opportunities:ws`，通过 WebSocket 推送最新机会。
- WebSocket 地址 `/ws/opportunities`，默认监听 `0.0.0.0:8100`。
- 可扩展将机会流复制到频道，以实现实时广播。

## 运行

```bash
pip install -r requirements.txt
python -m signal_streamer.main
```

## 配置

- 环境变量前缀 `SIGNAL_STREAMER_`
- `REDIS_URL`：Redis 连接串。
- `CHANNEL_NAME`：订阅的发布频道（默认 `dfp:opportunities:ws`）。

## 开发

```bash
pip install -r requirements-dev.txt
python -m compileall services/signal-streamer
```
