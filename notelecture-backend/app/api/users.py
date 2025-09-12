# app/api/users.py
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.core.config import settings
from app.db.http_client import supabase_http

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

async def get_current_user_http(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user using HTTP approach to avoid database connection issues"""
    try:
        # Decode JWT token with relaxed validation to match fastapi-users
        token = credentials.credentials
        
        # Decode without audience validation since fastapi-users doesn't set it
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={
                "verify_aud": False,  # fastapi-users doesn't use audience
                "verify_iss": False,  # fastapi-users doesn't use issuer
            }
        )
        user_id = payload.get("sub")
        logger.info(f"JWT payload: {payload}")
        logger.info(f"Extracted user_id: {user_id}")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user via HTTP with better error handling
        logger.info(f"Looking up user with ID: {user_id}")
        user = await supabase_http.get_user_by_id(user_id)
        logger.info(f"User lookup result: {user}")
        
        if not user:
            logger.error(f"User not found in database for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, jwt.DecodeError, AttributeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=500, detail="Authentication error")

@router.get("/me")
async def get_current_user_info(current_user = Depends(get_current_user_http)):
    """Get current user information"""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "is_active": current_user.get("is_active", True),
        "is_verified": current_user.get("is_verified", True),
        "first_name": current_user.get("first_name"),
        "last_name": current_user.get("last_name"),
        "created_at": current_user.get("created_at"),
        "free_lectures_used": current_user.get("free_lectures_used", 0)
    }