"""
AI Quant Platform - Quant API Router
API endpoints for AI quantitative trading engine control and monitoring.

Endpoints:
- GET  /status     - Engine status
- POST /start      - Start engine
- POST /stop       - Stop engine
- GET  /positions  - Current positions
- WS   /signals    - Real-time signal stream
- POST /sync       - Manual data sync
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quant", tags=["AI Quant"])

# Configuration
HEARTBEAT_INTERVAL_SECONDS = 30  # Configurable heartbeat interval


# ==================== Request/Response Models ====================

class StartEngineRequest(BaseModel):
    """Request to start the quant engine."""
    symbols: List[str] = Field(default=["000001", "600000"], description="Stock symbols to monitor")
    strategies: List[str] = Field(default=["Ambush"], description="Strategies to run")
    mode: Literal["simulation", "live"] = Field(default="simulation", description="Engine mode")
    
    @field_validator('symbols')
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        """Validate stock symbol format (6 digits)."""
        for symbol in v:
            if not symbol.isdigit() or len(symbol) != 6:
                raise ValueError(f"Invalid symbol format: {symbol}. Must be 6 digits.")
        return v
    
    @field_validator('strategies')
    @classmethod
    def validate_strategies(cls, v: List[str]) -> List[str]:
        """Validate strategy names."""
        valid_strategies = {"Ambush", "Ignition"}
        for strategy in v:
            if strategy not in valid_strategies:
                raise ValueError(f"Unknown strategy: {strategy}. Valid: {valid_strategies}")
        return v


class StartEngineResponse(BaseModel):
    """Response after starting the engine."""
    success: bool
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class StopEngineResponse(BaseModel):
    """Response after stopping the engine."""
    success: bool
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class SyncRequest(BaseModel):
    """Request for data sync."""
    symbol: Optional[str] = Field(default=None, description="Specific symbol to sync, or all if None")


class SyncResponse(BaseModel):
    """Response after data sync."""
    success: bool
    synced: int
    validation_passed: bool
    message: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PositionInfo(BaseModel):
    """Position information."""
    symbol: str
    name: Optional[str] = None
    entry_price: float
    current_price: float
    quantity: int
    pnl: float
    pnl_pct: float


class PositionsResponse(BaseModel):
    """Response with current positions."""
    positions: List[PositionInfo]
    total_value: float = 0.0
    total_pnl: float = 0.0


class EngineStatusResponse(BaseModel):
    """Response with engine status."""
    engine_running: bool
    mode: str
    capital: float
    position_count: int
    daily_pnl: float
    daily_pnl_pct: float
    max_drawdown: float
    strategies: List[str]
    last_signal: Optional[str] = None
    data_status: dict = Field(default_factory=dict)


# ==================== Engine State (In-memory singleton) ====================

class QuantEngineState:
    """Singleton state for the quant engine (thread-safe with locks)."""
    
    def __init__(self):
        self.running = False
        self.mode = "simulation"
        self.capital = 1_000_000.0
        self.positions: dict = {}
        self.strategies: List[str] = ["Ambush", "Ignition"]
        self.symbols: List[str] = []
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.last_signal_time: Optional[str] = None
        self.last_sync_time: Optional[str] = None
        self.sync_count = 0
        self.validation_passed = True
        
        # WebSocket connections with lock
        self._ws_connections: List[WebSocket] = []
        self._ws_lock = asyncio.Lock()
        
        # State lock for thread-safety
        self._state_lock = asyncio.Lock()
    
    @property
    def ws_connections(self) -> List[WebSocket]:
        """Get a copy of WebSocket connections list (safe for iteration)."""
        return list(self._ws_connections)
    
    async def add_ws_connection(self, ws: WebSocket):
        """Add WebSocket connection (thread-safe)."""
        async with self._ws_lock:
            self._ws_connections.append(ws)
    
    async def remove_ws_connection(self, ws: WebSocket):
        """Remove WebSocket connection (thread-safe)."""
        async with self._ws_lock:
            if ws in self._ws_connections:
                self._ws_connections.remove(ws)
    
    def to_status(self) -> dict:
        """Convert to status response."""
        return {
            "engine_running": self.running,
            "mode": self.mode,
            "capital": self.capital,
            "position_count": len(self.positions),
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.capital * 100) if self.capital > 0 else 0,
            "max_drawdown": self.max_drawdown,
            "strategies": list(self.strategies),  # Return copy
            "last_signal": self.last_signal_time,
            "data_status": {
                "last_sync": self.last_sync_time,
                "symbols_synced": self.sync_count,
                "validation_passed": self.validation_passed
            }
        }


# Global engine state
_engine_state = QuantEngineState()


def get_engine_state() -> QuantEngineState:
    """Get the global engine state."""
    return _engine_state


# ==================== API Endpoints ====================

@router.get("/status", response_model=EngineStatusResponse)
async def get_status():
    """
    Get current quant engine status.
    
    Returns engine running state, capital, positions, P&L, and data sync status.
    """
    state = get_engine_state()
    return EngineStatusResponse(**state.to_status())


@router.post("/start", response_model=StartEngineResponse)
async def start_engine(request: StartEngineRequest):
    """
    Start the quant engine.
    
    Configures symbols and strategies, then starts the engine loop.
    """
    state = get_engine_state()
    
    async with state._state_lock:
        if state.running:
            return StartEngineResponse(
                success=False,
                message="Engine is already running"
            )
        
        # Update configuration
        state.symbols = list(request.symbols)
        state.strategies = list(request.strategies)
        state.mode = request.mode
        state.running = True
    
    logger.info(f"Quant engine started: mode={request.mode}, symbols={request.symbols}")
    
    return StartEngineResponse(
        success=True,
        message=f"Engine started in {request.mode} mode with {len(request.symbols)} symbols"
    )


@router.post("/stop", response_model=StopEngineResponse)
async def stop_engine():
    """
    Stop the quant engine.
    
    Gracefully stops the engine and preserves state.
    """
    state = get_engine_state()
    
    async with state._state_lock:
        if not state.running:
            return StopEngineResponse(
                success=False,
                message="Engine is not running"
            )
        
        state.running = False
    
    logger.info("Quant engine stopped")
    
    return StopEngineResponse(
        success=True,
        message="Engine stopped successfully"
    )


@router.get("/positions", response_model=PositionsResponse)
async def get_positions():
    """
    Get current positions.
    
    Returns list of all open positions with P&L information.
    """
    state = get_engine_state()
    
    positions = []
    total_value = 0.0
    total_pnl = 0.0
    
    for symbol, pos in state.positions.items():
        pos_info = PositionInfo(
            symbol=symbol,
            name=pos.get("name"),
            entry_price=pos.get("entry_price", 0),
            current_price=pos.get("current_price", 0),
            quantity=pos.get("quantity", 0),
            pnl=pos.get("pnl", 0),
            pnl_pct=pos.get("pnl_pct", 0)
        )
        positions.append(pos_info)
        total_value += pos.get("current_price", 0) * pos.get("quantity", 0)
        total_pnl += pos.get("pnl", 0)
    
    return PositionsResponse(
        positions=positions,
        total_value=total_value,
        total_pnl=total_pnl
    )


@router.post("/sync", response_model=SyncResponse)
async def sync_data(request: SyncRequest = None):
    """
    Manually trigger data synchronization.
    
    Syncs minute and daily data from Tushare to local DuckDB cache.
    """
    state = get_engine_state()
    
    try:
        # Import DataManager lazily to avoid circular imports
        from ..core.quant.data import DataManager
        
        data_manager = DataManager()
        
        if request and request.symbol:
            # Sync specific symbol
            logger.info(f"Syncing data for {request.symbol}")
            daily_df = data_manager.get_daily(request.symbol, days=30)
            synced = 1 if len(daily_df) > 0 else 0
            validation_passed = data_manager.validate_minute_data(
                request.symbol, 
                datetime.now().strftime("%Y-%m-%d")
            )
        else:
            # Sync all tracked symbols
            symbols = state.symbols or ["000001", "600000"]
            logger.info(f"Syncing data for {len(symbols)} symbols")
            
            # Use sync_today for batch sync
            result = await data_manager.sync_today()
            synced = result.get("synced", 0)
            
            # Validate
            validation_result = await data_manager.validate_today()
            validation_passed = validation_result.get("failed", 0) == 0
        
        state.last_sync_time = datetime.now().isoformat()
        state.sync_count = synced
        state.validation_passed = validation_passed
        
        return SyncResponse(
            success=True,
            synced=synced,
            validation_passed=validation_passed,
            message=f"Synced {synced} symbols" + ("" if validation_passed else " (validation failed)")
        )
        
    except ImportError as e:
        logger.warning(f"DataManager not available, using mock: {e}")
        # Fallback to mock sync
        synced = len(state.symbols) or 50
        state.last_sync_time = datetime.now().isoformat()
        state.sync_count = synced
        state.validation_passed = True
        
        return SyncResponse(
            success=True,
            synced=synced,
            validation_passed=True,
            message=f"Mock synced {synced} symbols (DataManager not available)"
        )
        
    except Exception as e:
        logger.error(f"Sync failed: {type(e).__name__}: {e}")
        return SyncResponse(
            success=False,
            synced=0,
            validation_passed=False,
            message=f"Sync failed: {type(e).__name__}"
        )


@router.websocket("/signals")
async def websocket_signals(websocket: WebSocket):
    """
    WebSocket endpoint for real-time signal streaming.
    
    Sends signals in format:
    {
        "type": "quant_signal",
        "payload": {
            "symbol": "000001",
            "signal_type": "buy",
            "confidence": 0.85,
            ...
        }
    }
    """
    await websocket.accept()
    state = get_engine_state()
    await state.add_ws_connection(websocket)
    
    logger.info(f"WebSocket connected. Total connections: {len(state.ws_connections)}")
    
    try:
        while True:
            # Keep connection alive and wait for messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=HEARTBEAT_INTERVAL_SECONDS
                )
                # Handle ping/pong or other messages
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat", 
                    "timestamp": datetime.now().isoformat(),
                    "engine_running": state.running
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await state.remove_ws_connection(websocket)
        logger.info(f"WebSocket removed. Total connections: {len(state.ws_connections)}")


async def broadcast_signal(signal: dict):
    """
    Broadcast a signal to all connected WebSocket clients.
    
    Args:
        signal: Signal data to broadcast
    """
    state = get_engine_state()
    
    message = {
        "type": "quant_signal",
        "payload": signal,
        "timestamp": datetime.now().isoformat()
    }
    
    # Get a copy of connections for safe iteration
    connections = state.ws_connections
    disconnected = []
    
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        await state.remove_ws_connection(ws)


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """Health check endpoint for the quant module."""
    state = get_engine_state()
    return {
        "status": "ok",
        "engine_running": state.running,
        "ws_connections": len(state.ws_connections)
    }
