import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from .models import Notification

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get token from query string or cookies
        self.user = None
        self.user_role = None
        self.room_group_name = None
        
        # Try to get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        token = None
        
        # Parse query string for token
        if 'token=' in query_string:
            token = query_string.split('token=')[1].split('&')[0]
        else:
            # Try to get from cookies
            cookies = self.scope.get('cookies', {})
            token = cookies.get('access_token')
        
        if token:
            try:
                # Validate token
                user = await self.get_user_from_token(token)
                if user:
                    self.user = user
                    self.user_role = user.roles
                    # Create room group name based on user and role
                    self.room_group_name = f"notifications_{user.id}_{user.roles}"
                    
                    # Join room group
                    await self.channel_layer.group_add(
                        self.room_group_name,
                        self.channel_name
                    )
                    
                    # Also join role-based group
                    role_group_name = f"notifications_role_{user.roles}"
                    await self.channel_layer.group_add(
                        role_group_name,
                        self.channel_name
                    )
                    
                    await self.accept()
                    return
            except Exception:
                # If token validation fails, reject connection
                pass
        
        # If no valid token, reject connection
        await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.room_group_name:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            if self.user_role:
                role_group_name = f"notifications_role_{self.user_role}"
                await self.channel_layer.group_discard(
                    role_group_name,
                    self.channel_name
                )
    
    async def receive(self, text_data):
        """Handle messages received from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'mark_read':
                # Mark notification as read
                notification_id = text_data_json.get('notification_id')
                if notification_id and self.user:
                    await self.mark_notification_read(notification_id)
                    await self.send(text_data=json.dumps({
                        'type': 'notification_read',
                        'notification_id': notification_id
                    }))
            
            elif message_type == 'mark_all_read':
                # Mark all notifications as read
                if self.user:
                    await self.mark_all_notifications_read()
                    await self.send(text_data=json.dumps({
                        'type': 'all_notifications_read'
                    }))
            
            elif message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        
        except json.JSONDecodeError:
            pass
    
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        message = event['message']
        await self.send(text_data=json.dumps(message))
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        """Get user from JWT token"""
        try:
            # Decode token
            UntypedToken(token)
            decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get('user_id')
            
            if user_id:
                try:
                    return User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return None
        except (InvalidToken, TokenError, Exception) as e:
            return None
        return None
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            pass
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all user notifications as read"""
        Notification.objects.filter(user=self.user, is_read=False).update(is_read=True)

