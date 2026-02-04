from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import RestaurantInfo
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PublicRestaurantStatusView(APIView):
    """
    Public endpoint to check if the restaurant is currently open or closed.
    """
    permission_classes = [AllowAny]
    
    def get_authenticators(self):
        return []
    
    def get(self, request):
        try:
            info = RestaurantInfo.objects.first()
            if not info:
                # Default to open if not configured
                return Response({
                    'is_open': True,
                    'opening_time': None,
                    'closing_time': None,
                    'message': 'Always Open'
                })
            
            current_time = datetime.now().time()
            is_open = False
            
            if info.opening_time < info.closing_time:
                # Standard day (e.g. 09:00 - 22:00)
                if info.opening_time <= current_time <= info.closing_time:
                    is_open = True
            else:
                # Overnight (e.g. 18:00 - 02:00)
                if current_time >= info.opening_time or current_time <= info.closing_time:
                    is_open = True
            
            return Response({
                'is_open': is_open,
                'opening_time': info.opening_time.strftime("%H:%M"),
                'closing_time': info.closing_time.strftime("%H:%M"),
                'message': 'Open' if is_open else 'Closed'
            })
            
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            return Response({'error': str(e)}, status=500)
