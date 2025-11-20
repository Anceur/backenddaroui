from typing import Optional, Tuple

from django.contrib.auth.models import AbstractBaseUser
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken, RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authenticate using the JWT access token stored in an HttpOnly cookie named
    'access_token'. Automatically refreshes the token if it's about to expire.
    Returns (user, token) when present and valid; otherwise None.
    """

    def authenticate(self, request: Request) -> Optional[Tuple[AbstractBaseUser, UntypedToken]]:
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None

        try:
            # Try to validate the access token
            validated_token = self.get_validated_token(raw_token)
            access_token = AccessToken(raw_token)
            
            # Check if token is about to expire (within 5 minutes)
            import time
            
            # Get token expiration time
            exp_timestamp = access_token.get('exp', 0)
            current_timestamp = int(time.time())
            time_until_expiry = exp_timestamp - current_timestamp
            
            # If token expires within 5 minutes (300 seconds), refresh it
            if time_until_expiry < 300:  # 5 minutes
                logger.info(f"Access token expiring soon ({time_until_expiry}s), refreshing...")
                
                # Get refresh token from cookies
                refresh_token_str = request.COOKIES.get('refresh_token')
                if refresh_token_str:
                    try:
                        # Validate and use refresh token to get new access token
                        refresh_token = RefreshToken(refresh_token_str)
                        new_access_token = refresh_token.access_token
                        
                        # Store new access token in request for middleware to update cookie
                        request._new_access_token = str(new_access_token)
                        request._refresh_token = refresh_token_str
                        
                        logger.info("Successfully refreshed access token")
                        
                        # Use the new token for authentication
                        validated_token = self.get_validated_token(str(new_access_token))
                    except (InvalidToken, TokenError) as e:
                        logger.warning(f"Failed to refresh token: {e}")
                        # Continue with original token if refresh fails
                else:
                    logger.warning("No refresh token found, cannot refresh access token")
            
            return self.get_user(validated_token), validated_token
            
        except (InvalidToken, TokenError) as e:
            logger.warning(f"Token validation failed: {e}")
            # Try to refresh if token is invalid/expired
            refresh_token_str = request.COOKIES.get('refresh_token')
            if refresh_token_str:
                try:
                    logger.info("Access token invalid, attempting refresh...")
                    refresh_token = RefreshToken(refresh_token_str)
                    new_access_token = refresh_token.access_token
                    
                    # Store new access token in request for middleware to update cookie
                    request._new_access_token = str(new_access_token)
                    request._refresh_token = refresh_token_str
                    
                    logger.info("Successfully refreshed expired access token")
                    
                    # Use the new token for authentication
                    validated_token = self.get_validated_token(str(new_access_token))
                    return self.get_user(validated_token), validated_token
                except (InvalidToken, TokenError) as refresh_error:
                    logger.warning(f"Token refresh failed: {refresh_error}")
                    return None
            return None




