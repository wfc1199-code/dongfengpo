# Data Models – signal-api

## Opportunity
- Fields: `id`, `symbol`, `state`, `created_at`, `updated_at`, `confidence`, `strength_score`, `notes: List[str]`
- Purpose: Aggregated opportunity signal.

## StrategySignalResponse
- Fields: `strategy`, `symbol`, `signal_type`, `confidence (0-1)`, `strength_score`, `reasons: List[str]`, `triggered_at`, `window`, `metadata: Dict`
- Example includes volume/volume_ratio context for anomaly detection.

## Config Favorites (router/config.py)
- Request model: `FavoriteRequest` with `code: str`, optional `name`.
- Stored in `backend/data/config.json` (self-managed JSON).

## Pending
- Other services’ schemas not yet extracted; to be generated per service.

