# app/main.py
import logging
from fastapi import FastAPI
import socketio  # Import socketio

from .api.endpoints import hello
from .api.endpoints import dashboard  # Import dashboard endpoints
from agents.metrics.exporters import json_exporter  # Import metrics exporter

# --- Socket.IO Server Setup ---
sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins=[]
)  # Allow all origins for now
sio_app = socketio.ASGIApp(sio)
# -----------------------------

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Autonomous Agent API",
    description="API for the application built by autonomous AI agents.",
    version="0.1.0",
)

# Include routers
app.include_router(hello.router, prefix="/api/v1", tags=["hello"])
app.include_router(
    json_exporter.router, prefix="/", tags=["metrics"]
)  # Add metrics endpoint
app.include_router(
    dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"]
)  # Add dashboard endpoints


@app.get("/healthz", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check requested.")
    return {"status": "ok"}


# Mount Socket.IO app
app.mount("/ws", sio_app)  # Mount the socket.io ASGI app


# --- Socket.IO Event Handlers (Example) ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Socket.IO client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO client disconnected: {sid}")


# Function to emit events (can be called from agents/tasks)
async def emit_event(event_name: str, data: dict):
    try:
        await sio.emit(event_name, data)
        logger.debug(f"Emitted Socket.IO event: {event_name}")
    except Exception as e:
        logger.error(
            f"Failed to emit Socket.IO event '{event_name}': {e}", exc_info=True
        )


# -----------------------------------------

logger.info("FastAPI application initialized with Socket.IO.")
