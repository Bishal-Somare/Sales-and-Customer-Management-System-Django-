# notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync # For sync calls from async context if needed

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # For simplicity, all authenticated users join the same group.
        # You could make this user-specific if needed: self.user.username or self.user.id
        if self.scope["user"].is_authenticated:
            self.room_group_name = 'notifications_group' # A general group for all notifications

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"User {self.scope['user']} connected to notifications.")
        else:
            await self.close()
            print("Unauthenticated user tried to connect to notifications.")


    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"User {self.scope['user']} disconnected from notifications.")

    # Receive message from WebSocket (not used in this scenario as notifications are server-pushed)
    # async def receive(self, text_data):
    #     pass

    # Receive message from room group (pushed by the scheduler)
    async def send_notification(self, event):
        notification = event['notification']
        print(f"Consumer: Sending notification to client: {notification}")
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'new_notification', # Client-side handler will look for this type
            'notification': notification
        }))