# Architecture – signal-streamer

## Purpose
- WebSocket server broadcasting opportunities/risk alerts to clients.
- Bridges Redis pubsub → WebSocket `/ws/opportunities`.

## Runtime
- App factory: `create_app(streamer)` in `signal_streamer/server.py`
- Subscribes Redis channels:
  - `channel_name` (opportunities)
  - `risk_channel` (optional)
- On message:
  - Decode JSON (fallback wraps raw)
  - Normalize type: `{"type": "opportunity"|"risk_alert", "payload": ...}`
  - Broadcast to all connected WebSocket clients

## WebSocket
- Endpoint: `/ws/opportunities`
- Behavior: accept, keep alive via receive_text loop; disconnect handled.

## Config (SignalStreamerSettings)
- `redis_url`
- `channel_name`
- `risk_channel` (optional)

## Notes
- In-memory client set; best-effort send, drops failed clients.
- Logging of subscribe and payload processing.

