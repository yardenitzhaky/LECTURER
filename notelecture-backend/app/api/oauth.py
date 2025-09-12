# app/api/oauth.py
import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from httpx_oauth.oauth2 import OAuth2RequestError

from app.auth import google_oauth_client, auth_backend, get_user_manager
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/authorize")
async def google_authorize(request: Request):
    """Get Google OAuth authorization URL"""
    try:
        # Use consistent redirect URI that matches Google Console configuration
        redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/google/callback"
        logger.info(f"Authorization redirect_uri: {redirect_uri}")
        authorization_url = await google_oauth_client.get_authorization_url(
            redirect_uri,
            scope=["openid", "email", "profile"],
        )
        logger.info(f"Generated authorization URL: {authorization_url}")
        return {"authorization_url": authorization_url}
    except Exception as e:
        logger.error(f"OAuth authorization failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth authorization failed: {str(e)}")

@router.get("/callback")
async def google_callback(
    request: Request,
    user_manager = Depends(get_user_manager)
):
    """Handle Google OAuth callback and redirect to frontend"""
    try:
        logger.info(f"OAuth callback received: {request.url}")
        
        # Get access token from Google
        redirect_uri = f"{request.url.scheme}://{request.url.netloc}/api/auth/google/callback"
        logger.info(f"Using redirect_uri: {redirect_uri}")
        logger.info(f"Request URL query: {request.url.query}")
        logger.info(f"Full request URL: {request.url}")
        
        try:
            # Extract the authorization code from the query parameters
            from urllib.parse import parse_qs
            parsed_query = parse_qs(request.url.query)
            auth_code = parsed_query.get('code', [None])[0]
            logger.info(f"Extracted auth_code: {auth_code}")
            
            if not auth_code:
                raise ValueError("No authorization code received")
            
            access_token = await google_oauth_client.get_access_token(
                auth_code,
                redirect_uri
            )
        except Exception as token_error:
            logger.error(f"Token exchange error details: {token_error}")
            logger.error(f"Token exchange error type: {type(token_error)}")
            # Try to get more details from the error
            if hasattr(token_error, 'response'):
                logger.error(f"Error response: {token_error.response}")
                logger.error(f"Error response content: {getattr(token_error.response, 'content', 'No content')}")
            raise
        
        logger.info("Successfully obtained access token from Google")
        logger.info(f"Access token type: {type(access_token)}")
        logger.info(f"Access token (first 20 chars): {str(access_token)[:20]}...")
        
        # Get user info from Google using UserInfo endpoint instead of People API
        import httpx
        user_email = None
        user_id = None
        
        try:
            # The access_token might be a dict with token info, let's check
            token_to_use = access_token
            if isinstance(access_token, dict):
                token_to_use = access_token.get("access_token")
                logger.info(f"Extracted token from dict: {token_to_use[:20] if token_to_use else 'None'}...")
            
            # Use timeout and retry logic for better reliability
            timeout_config = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_to_use}"}
                )
                
                if response.status_code != 200:
                    logger.error(f"UserInfo API error: {response.status_code} - {response.text}")
                    raise HTTPException(status_code=400, detail="Failed to get user info from Google")
                
                user_data = response.json()
                user_email = user_data.get("email")
                user_id = user_data.get("id")
                logger.info(f"Got user info from Google: {user_email}")
                
                if not user_email:
                    raise HTTPException(status_code=400, detail="No email received from Google")
                    
        except httpx.ConnectError as e:
            logger.error(f"Network connection error during user info fetch: {e}")
            raise HTTPException(status_code=500, detail="Network error during authentication")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error during user info fetch: {e}")
            raise HTTPException(status_code=500, detail="Authentication timeout")
        except Exception as e:
            logger.error(f"Unexpected error during user info fetch: {e}")
            raise HTTPException(status_code=500, detail="Authentication error")
        
        # Get or create user
        try:
            user = await user_manager.get_by_email(user_email)
            logger.info(f"Found existing user: {user_email}")
        except:
            # Create new user if doesn't exist
            logger.info(f"Creating new user: {user_email}")
            from app.schemas import UserCreate
            user_create = UserCreate(
                email=user_email,
                password="oauth_user",  # OAuth users need some password
            )
            user = await user_manager.create(user_create)
        
        # Generate JWT token
        jwt_token = await auth_backend.get_strategy().write_token(user)
        logger.info("Generated JWT token for user")
        
        # Redirect to frontend with token
        redirect_url = f"{settings.FRONTEND_URL}/oauth/callback?token={jwt_token}"
        logger.info(f"Redirecting to: {redirect_url}")
        return RedirectResponse(
            url=redirect_url,
            status_code=302
        )
        
    except OAuth2RequestError as e:
        logger.error(f"OAuth2 request error: {e}")
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/callback?error={str(e)}",
            status_code=302
        )
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/oauth/callback?error=Authentication failed",
            status_code=302
        )