"""
Custom WebSocket authentication middleware for JWT tokens
"""
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken, AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token):
    """Get user from JWT token"""
    try:
        # Validate token using rest_framework_simplejwt
        # This will use the correct signing key from SIMPLE_JWT settings
        validated_token = UntypedToken(token)
        
        # Get user_id from validated token
        from rest_framework_simplejwt.tokens import AccessToken
        access_token = AccessToken(token)
        user_id = access_token.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                logger.debug(f"Successfully authenticated user {user.username} from token")
                return user
            except User.DoesNotExist:
                logger.warning(f"User with ID {user_id} not found")
                return None
    except (InvalidToken, TokenError) as e:
        logger.warning(f"JWT token validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}", exc_info=True)
        return None
    return None


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens from cookies or headers
    """
    
    async def __call__(self, scope, receive, send):
        token = None
        
        # Try to get token from cookies first
        cookies = scope.get('cookies', {})
        if cookies:
            token = cookies.get('access_token')
            if token:
                logger.debug(f"WebSocket: Found token in cookies")
        
        # If no token in cookies, try headers (some WebSocket clients send cookies as headers)
        if not token:
            headers = dict(scope.get('headers', []))
            # Convert bytes keys to strings
            headers = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v 
                      for k, v in headers.items()}
            
            # Check for cookie header
            cookie_header = headers.get('cookie', '') or headers.get('Cookie', '')
            if cookie_header:
                # Parse cookie header
                for cookie in cookie_header.split(';'):
                    cookie = cookie.strip()
                    if cookie.startswith('access_token='):
                        token = cookie.split('=', 1)[1]
                        logger.debug(f"WebSocket: Found token in cookie header")
                        break
        
        # If still no token, try query string as last resort
        if not token:
            query_string = scope.get('query_string', b'')
            if isinstance(query_string, bytes):
                query_string = query_string.decode()
            if 'token=' in query_string:
                # Extract token from query string (handle URL encoding)
                token_part = query_string.split('token=')[1].split('&')[0]
                # URL decode the token
                from urllib.parse import unquote
                token = unquote(token_part)
                logger.info(f"WebSocket: Found token in query string (length: {len(token)})")
        
        if token:
            logger.info(f"WebSocket: Found token, validating... (token length: {len(token)})")
            user = await get_user_from_token(token)
            if user:
                scope['user'] = user
                logger.info(f"WebSocket: ✅ Authenticated user {user.username} (role: {user.roles}, ID: {user.id})")
            else:
                logger.warning(f"WebSocket: ❌ JWT token validation failed - token invalid or expired")
                logger.debug(f"WebSocket: Token preview: {token[:50]}...")
                scope['user'] = None
        else:
            logger.warning(f"WebSocket: ❌ No access_token found in cookies, headers, or query string")
            logger.debug(f"WebSocket: Cookies available: {list(cookies.keys()) if cookies else 'None'}")
            logger.debug(f"WebSocket: Query string: {query_string[:200] if 'query_string' in locals() else 'N/A'}")
            scope['user'] = None
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Stack JWT auth middleware"""
    return JWTAuthMiddleware(inner)

