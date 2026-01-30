"""Main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from .config import settings
from .database import init_db
from .scheduler import data_scheduler
from .api import events, sources, alerts, stats


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting OSINT Aggregator API")

    # Initialize database
    logger.info("Initializing database")
    init_db()

    # Start scheduler
    await data_scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down OSINT Aggregator API")
    await data_scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="OSINT Aggregator API",
    description="Multi-source OSINT data aggregation and analysis platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router)
app.include_router(sources.router)
app.include_router(alerts.router)
app.include_router(stats.router)


# WebSocket connections manager
class ConnectionManager:
    """Manage WebSocket connections for real-time event streaming."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket client: {e}")


manager = ConnectionManager()


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and wait for client messages
            data = await websocket.receive_text()
            # Echo back (you can implement specific commands here)
            await websocket.send_json({"type": "pong", "message": "Connected"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "OSINT Aggregator API",
        "version": "1.0.0",
        "status": "running",
        "scheduler_running": data_scheduler.is_running
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "scheduler": data_scheduler.is_running
    }


@app.post("/admin/collect")
async def trigger_collection():
    """Manually trigger data collection (admin endpoint)."""
    await data_scheduler.run_collection_now()
    return {"status": "Collection triggered"}


@app.post("/admin/process")
async def trigger_processing():
    """Manually trigger LLM processing (admin endpoint)."""
    await data_scheduler.run_processing_now()
    return {"status": "Processing triggered"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
