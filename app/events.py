# app/events.py

import logging
import socketio

logger = logging.getLogger(__name__)

# --- Socket.IO Server Setup ---
sio = socketio.AsyncServer(
    async_mode="asgi", cors_allowed_origins=[]  # Allow all origins for development
)
sio_app = socketio.ASGIApp(sio)
# -----------------------------


# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    logger.info(f"Socket.IO client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"Socket.IO client disconnected: {sid}")


# --- Event Emitter Function ---
async def emit_event(event_name: str, data: dict):
    """Emit a Socket.IO event to all connected clients."""
    try:
        await sio.emit(event_name, data)
        logger.debug(f"Emitted Socket.IO event: {event_name}")
    except Exception as e:
        logger.error(
            f"Failed to emit Socket.IO event '{event_name}': {e}", exc_info=True
        )


# -----------------------------
