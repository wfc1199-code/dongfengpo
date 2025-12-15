# Frontend WebSocket Hook (Example)

```ts
// useOpportunitiesStream.ts
import { useEffect, useRef, useState } from "react";

type Message =
  | { type: "opportunity"; payload: any }
  | { type: "risk_alert"; payload: any }
  | { type: string; payload: any };

export function useOpportunitiesStream(wsUrl: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send("ping");
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        setMessages((prev) => [...prev, msg]);
      } catch {
        // ignore malformed
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [wsUrl]);

  return { messages, connected };
}
```

用法示例：
```ts
const { messages, connected } = useOpportunitiesStream("ws://<host>/ws/opportunities");
```

说明：
- 兼容 signal-streamer 输出的 `type: "opportunity"` / `"risk_alert"`。
- 简单保留消息列表；生产环境可改用 zustand/observable，将列表截断防止内存膨胀。
```

