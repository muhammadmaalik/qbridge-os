import asyncio
import json
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from backend.routers import auth, entropy, compute, finance, security, system
from backend.database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await db.connect()
        print("Connected to PostgreSQL")
        await db.ensure_demo_user()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
    yield
    # Shutdown
    await db.disconnect()

app = FastAPI(
    title="Quantum Bridge OS (QaaS)",
    description="High-performance, asynchronous QaaS REST API and Gateway.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(entropy.router, prefix="/api/v1/entropy")
app.include_router(security.router, prefix="/api/v1/security")
app.include_router(compute.router, prefix="/api/v1/compute")
app.include_router(system.router, prefix="/api/v1/system")
app.include_router(finance.router, prefix="/api/v1/finance")

@app.get("/")
async def root():
    return {"message": "Welcome to the Quantum Bridge OS API Gateway"}

# Simple Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Keep the socket warm during long quantum jobs: periodic JSON heartbeats + long receive timeout.

    Run Uvicorn with a generous keep-alive when proxying, e.g.:
    ``uvicorn backend.main:app --timeout-keep-alive 120``
    """
    await manager.connect(websocket)
    stop = asyncio.Event()

    async def heartbeat():
        while not stop.is_set():
            try:
                # Frequent enough to survive long server-side jobs (e.g. 21-point PES scans).
                await asyncio.sleep(15.0)
                await websocket.send_text(json.dumps({"type": "heartbeat", "channel": "qbridge"}))
            except Exception:
                break

    hb_task = asyncio.create_task(heartbeat())
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
            except asyncio.TimeoutError:
                await websocket.send_text(
                    json.dumps({"type": "heartbeat", "reason": "idle_timeout_refresh"})
                )
                continue
            await manager.broadcast(f"Server received: {data}")
    except WebSocketDisconnect:
        pass
    finally:
        stop.set()
        hb_task.cancel()
        try:
            await hb_task
        except asyncio.CancelledError:
            pass
        manager.disconnect(websocket)


class _UvicornReadyLogHandler(logging.Handler):
    """Print one system line when Uvicorn reports the API is listening (port 8000)."""

    def __init__(self) -> None:
        super().__init__()
        self._emitted = False

    def emit(self, record: logging.LogRecord) -> None:
        if self._emitted:
            return
        try:
            msg = record.getMessage()
        except Exception:
            return
        if "Uvicorn running on" in msg and "127.0.0.1:8000" in msg:
            self._emitted = True
            print(
                "[system] Quantum Engine Reloaded. Cache Purged. Ready for Simulation.",
                file=sys.stderr,
                flush=True,
            )


if __name__ == "__main__":
    import logging.config
    import os

    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(_root)
    if _root not in sys.path:
        sys.path.insert(0, _root)

    # Uvicorn's default run() applies LOGGING_CONFIG and would drop any pre-attached handlers.
    logging.config.dictConfig(LOGGING_CONFIG)
    _ready = _UvicornReadyLogHandler()
    _ready.setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").addHandler(_ready)

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        log_config=None,
        timeout_keep_alive=120,
    )
