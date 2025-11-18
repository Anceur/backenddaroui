"""
Notification API views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer
from django.db.models import Q
from django.utils import timezone


class NotificationListView(APIView):
    """Get user's notifications"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
            limit = request.query_params.get('limit', None)
            
            queryset = Notification.objects.filter(
                Q(user=user) | Q(role=user.roles, user__isnull=True)
            )
            
            if unread_only:
                queryset = queryset.filter(is_read=False)
            
            queryset = queryset.order_by('-created_at')
            
            if limit:
                try:
                    limit = int(limit)
                    queryset = queryset[:limit]
                except ValueError:
                    pass
            
            serializer = NotificationSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching notifications: {e}", exc_info=True)
            # Return empty list if there's an error (e.g., Notification model doesn't exist yet)
            return Response([], status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    """Get count of unread notifications"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            count = Notification.objects.filter(
                Q(user=user) | Q(role=user.roles, user__isnull=True),
                is_read=False
            ).count()
            
            return Response({'count': count}, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching unread count: {e}", exc_info=True)
            # Return 0 if there's an error (e.g., Notification model doesn't exist yet)
            return Response({'count': 0}, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    """Mark a notification as read"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        notification_id = request.data.get('notification_id')
        if not notification_id:
            return Response(
                {'error': 'notification_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.is_read = True
            notification.save()
            
            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationMarkAllReadView(APIView):
    """Mark all user notifications as read"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        count = Notification.objects.filter(
            Q(user=user) | Q(role=user.roles, user__isnull=True),
            is_read=False
        ).update(is_read=True)
        
        return Response(
            {'message': f'{count} notifications marked as read'},
            status=status.HTTP_200_OK
        )


class NotificationDetailView(APIView):
    """Get, update, or delete a specific notification"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            serializer = NotificationSerializer(notification)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.delete()
            return Response(
                {'message': 'Notification deleted'},
                status=status.HTTP_200_OK
            )
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )

