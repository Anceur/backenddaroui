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
        import logging
        logger = logging.getLogger(__name__)
        
        self.user = None
        self.user_role = None
        self.room_group_name = None
        
        # Get user from scope (set by JWTAuthMiddleware)
        user = self.scope.get('user')
        
        # If user is authenticated via middleware, use that
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            self.user = user
            self.user_role = user.roles
            logger.info(f"WebSocket: Authenticated user {user.username} (role: {user.roles})")
        else:
            # Fallback: Try JWT token from query string (if middleware didn't work)
            query_string = self.scope.get('query_string', b'').decode()
            token = None
            
            # Parse query string for token
            if 'token=' in query_string:
                # Extract and URL decode token
                from urllib.parse import unquote
                token_part = query_string.split('token=')[1].split('&')[0]
                token = unquote(token_part)
                logger.info(f"WebSocket: Trying token from query string (length: {len(token)})")
                
                if token:
                    try:
                        # Validate token
                        user = await self.get_user_from_token(token)
                        if user:
                            self.user = user
                            self.user_role = user.roles
                            logger.info(f"WebSocket: Authenticated via query token - user {user.username} (role: {user.roles})")
                        else:
                            logger.warning(f"WebSocket: Query token validation failed - token invalid or expired")
                    except Exception as e:
                        logger.error(f"WebSocket: Query token validation error: {e}", exc_info=True)
            else:
                logger.warning(f"WebSocket: No user found in scope and no token in query string. Query string: {query_string[:100]}")
        
        # If we have a user, accept connection
        if self.user and self.user_role:
            # Create room group name based on user and role
            self.room_group_name = f"notifications_{self.user.id}_{self.user_role}"
            
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # Also join role-based group
            role_group_name = f"notifications_role_{self.user_role}"
            await self.channel_layer.group_add(
                role_group_name,
                self.channel_name
            )
            
            await self.accept()
            logger.info(f"WebSocket: Connection accepted for user {self.user.username}")
            return
        
        # If no valid authentication, reject connection
        logger.warning(f"WebSocket: Rejecting connection - authentication failed")
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
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Validate token using rest_framework_simplejwt
            # This uses the correct signing key from SIMPLE_JWT settings
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token.get('user_id')
            
            if user_id:
                try:
                    return User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return None
        except (InvalidToken, TokenError) as e:
            logger.warning(f"Consumer: Token validation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Consumer: Unexpected error validating token: {e}", exc_info=True)
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

