# app/api/health.py
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db.connection import async_engine, async_database_url

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/db")
async def database_health_check():
    """
    Test database connectivity in isolation to debug connection issues.
    """
    try:
        logger.info(f"Testing database connection to: {async_database_url.split('@')[1] if '@' in async_database_url else 'unknown'}")
        
        # Test basic connection
        async with async_engine.connect() as conn:
            # Simple query to test connection
            result = await conn.execute(text("SELECT 1 as test, current_timestamp as now"))
            row = result.fetchone()
            
            logger.info(f"Database connection successful: {row}")
            
            return JSONResponse({
                "status": "healthy",
                "database": "connected",
                "test_query": row._asdict() if row else None,
                "connection_info": {
                    "url_host": async_database_url.split('@')[1].split('/')[0] if '@' in async_database_url else "unknown",
                    "using_pooler": ":6543" in async_database_url
                }
            })
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        logger.error(f"Error type: {type(e)}")
        
        return JSONResponse({
            "status": "unhealthy", 
            "database": "disconnected",
            "error": str(e),
            "error_type": str(type(e)),
            "connection_info": {
                "url_host": async_database_url.split('@')[1].split('/')[0] if '@' in async_database_url else "unknown",
                "using_pooler": ":6543" in async_database_url
            }
        }, status_code=500)

@router.get("/")
async def app_health_check():
    """Basic application health check."""
    return {"status": "healthy", "service": "notelecture-backend"}