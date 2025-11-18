from typing import Optional, Tuple

from django.contrib.auth.models import AbstractBaseUser
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authenticate using the JWT access token stored in an HttpOnly cookie named
    'access_token'. Returns (user, token) when present and valid; otherwise None.
    """

    def authenticate(self, request: Request) -> Optional[Tuple[AbstractBaseUser, UntypedToken]]:
        raw_token = request.COOKIES.get('access_token')
        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token




