# app/main.py
import logging
from fastapi import FastAPI

from .api.endpoints import hello
from .api.endpoints import dashboard  # Import dashboard endpoints
from agents.metrics.exporters import json_exporter  # Import metrics exporter

# Import the sio_app from the new events module
from .events import (
    sio_app,
    emit_event,
)  # Import emit_event here if needed globally, otherwise remove

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Autonomous Agent API",
    description="API for the application built by autonomous AI agents.",
    version="0.1.0",
)

# Include routers
app.include_router(hello.router, prefix="/hello", tags=["hello"])
app.include_router(
    json_exporter.router, prefix="", tags=["metrics"]
)  # Add metrics endpoint
app.include_router(
    dashboard.router, prefix="/api/dashboard", tags=["dashboard"]
)  # Add dashboard endpoints


@app.get("/healthz", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check requested.")
    return {"status": "ok"}


# Mount Socket.IO app
app.mount("/ws", sio_app)  # Mount the imported sio_app


# --- REMOVED Socket.IO Setup and Event Handlers (moved to app/events.py) ---
# --- REMOVED emit_event function (moved to app/events.py) ---

logger.info("FastAPI application initialized.")
