from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
import logging

from .models import Order, OfflineOrder
from .serializers import OrderSerializer, OfflineOrderSerializer
from .permissions import IsCashier

logger = logging.getLogger(__name__)

class CashierOrderHistoryView(APIView):
    """
    Get order history for cashier with date filtering
    """
    permission_classes = [IsAuthenticated, IsCashier]
    
    def get(self, request):
        try:
            year = request.query_params.get('year')
            month = request.query_params.get('month')
            day = request.query_params.get('day')
            
            # Base filters
            online_filter = Q()
            offline_filter = Q()
            
            if year:
                online_filter &= Q(created_at__year=year)
                offline_filter &= Q(created_at__year=year)
            if month:
                online_filter &= Q(created_at__month=month)
                offline_filter &= Q(created_at__month=month)
            if day:
                online_filter &= Q(created_at__day=day)
                offline_filter &= Q(created_at__day=day)
            
            # Get orders
            online_orders = Order.objects.filter(online_filter).select_related('loyal_customer').order_by('-created_at')
            offline_orders = OfflineOrder.objects.filter(offline_filter).select_related('table').prefetch_related('items__item', 'items__size').order_by('-created_at')
            
            online_serializer = OrderSerializer(online_orders, many=True)
            offline_serializer = OfflineOrderSerializer(offline_orders, many=True)
            
            return Response({
                'online_orders': online_serializer.data,
                'offline_orders': offline_serializer.data,
                'count': online_orders.count() + offline_orders.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching order history: {e}")
            return Response({
                'error': 'Failed to fetch order history'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
