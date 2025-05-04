from fastapi import APIRouter
from ..collector import metrics_collector  # Import the global instance

router = APIRouter()


@router.get("/metrics", tags=["metrics"])
async def get_metrics_json():
    """Endpoint to expose collected metrics in JSON format."""
    return metrics_collector.get_metrics()
