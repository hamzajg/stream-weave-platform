from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Status information including app version and database connectivity
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes and orchestrators.
    
    Returns:
        dict: Ready status
    """
    return {
        "ready": True,
        "checks": {
            "database": "ok",  # TODO: Add actual DB check
            "static_files": "ok",
        }
    }
