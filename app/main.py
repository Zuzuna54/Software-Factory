# app/main.py
import logging
from fastapi import FastAPI
from .api.endpoints import hello

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


@app.get("/healthz", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    logger.info("Health check requested.")
    return {"status": "ok"}


# Add more routers as the application grows
# from .api.endpoints import items, users
# app.include_router(items.router, prefix="/api/v1", tags=["items"])
# app.include_router(users.router, prefix="/api/v1", tags=["users"])

logger.info("FastAPI application initialized.")
