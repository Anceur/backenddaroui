"""
WebSocket token endpoint
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken
import logging

logger = logging.getLogger(__name__)


class WebSocketTokenView(APIView):
    """Get a WebSocket token for authenticated users"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return the access token for WebSocket connection"""
        try:
            # Check if user is authenticated
            if not request.user or not request.user.is_authenticated:
                logger.warning(f"WebSocket token request from unauthenticated user")
                return Response({
                    'error': 'Authentication required. Please log in.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # User is already authenticated (IsAuthenticated permission)
            # Generate a fresh access token for WebSocket use
            access_token = AccessToken.for_user(request.user)
            token_string = str(access_token)
            
            logger.info(f"Generated WebSocket token for user: {request.user.username} (ID: {request.user.id})")
            
            return Response({
                'token': token_string
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error generating WebSocket token for user {request.user.username if request.user else 'unknown'}: {e}", exc_info=True)
            return Response({
                'error': 'Failed to generate WebSocket token. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

