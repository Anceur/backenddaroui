"""
Middleware to automatically update access token cookie when it's refreshed
"""
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RefreshTokenMiddleware(MiddlewareMixin):
    """
    Middleware that updates the access_token cookie when a new token is generated
    during authentication.
    """
    
    def process_response(self, request, response):
        # Check if a new access token was generated during authentication
        if hasattr(request, '_new_access_token'):
            new_token = request._new_access_token
            refresh_token = getattr(request, '_refresh_token', None)
            
            # Determine secure settings
            is_secure = not settings.DEBUG  # Only secure in production
            
            # Update access token cookie
            response.set_cookie(
                "access_token",
                new_token,
                httponly=True,
                samesite="Lax" if settings.DEBUG else "None",
                secure=is_secure,
            )
            
            # Also update refresh token if it was rotated (optional - simplejwt doesn't rotate by default)
            if refresh_token:
                response.set_cookie(
                    "refresh_token",
                    refresh_token,
                    httponly=True,
                    samesite="Lax" if settings.DEBUG else "None",
                    secure=is_secure,
                )
            
            logger.debug("Updated access_token cookie with refreshed token")
        
        return response

