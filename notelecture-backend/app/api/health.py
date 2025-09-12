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
    Test database connectivity using both direct and HTTP approaches.
    """
    from app.db.http_client import supabase_http
    
    results = {}
    
    # Test HTTP approach (should work)
    try:
        logger.info("Testing HTTP-based database access")
        http_result = await supabase_http.test_connection()
        results["http_approach"] = http_result
    except Exception as e:
        results["http_approach"] = {"status": "error", "error": str(e)}
    
    # Test direct connection (likely to fail in Vercel)
    try:
        logger.info(f"Testing direct database connection to: {async_database_url.split('@')[1] if '@' in async_database_url else 'unknown'}")
        
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test, current_timestamp as now"))
            row = result.fetchone()
            
            results["direct_connection"] = {
                "status": "healthy",
                "test_query": row._asdict() if row else None
            }
            
    except Exception as e:
        logger.error(f"Direct database connection failed: {e}")
        results["direct_connection"] = {
            "status": "unhealthy",
            "error": str(e),
            "error_type": str(type(e))
        }
    
    # Overall status
    overall_status = "healthy" if results.get("http_approach", {}).get("status") == "connected" else "unhealthy"
    
    return JSONResponse({
        "status": overall_status,
        "approaches": results,
        "connection_info": {
            "url_host": async_database_url.split('@')[1].split('/')[0] if '@' in async_database_url else "unknown",
            "using_pooler": ":6543" in async_database_url,
            "recommendation": "HTTP approach" if results.get("http_approach", {}).get("status") == "connected" else "unknown"
        }
    }, status_code=200 if overall_status == "healthy" else 500)

@router.get("/")
async def app_health_check():
    """Basic application health check."""
    return {"status": "healthy", "service": "notelecture-backend"}