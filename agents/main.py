"""
Main entry point for the Autonomous AI Development Team API
"""

import os
from typing import Dict, Any

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.models import get_db

# Create FastAPI app
app = FastAPI(
    title="Autonomous AI Development Team",
    description="API for the Autonomous AI Development Team project",
    version="0.1.0",
)


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint - return API information"""
    return {
        "name": "Autonomous AI Development Team API",
        "version": "0.1.0",
        "status": "online",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Database connection check endpoint"""
    try:
        # Test database connection by executing a simple query
        result = await db.execute("SELECT 1")
        await db.commit()
        return {"status": "connected", "database": "PostgreSQL"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Include routers from other modules here
# app.include_router(some_module.router)

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    uvicorn.run("main:app", host=host, port=port, reload=True)
