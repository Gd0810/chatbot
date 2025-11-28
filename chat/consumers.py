# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.utils import timezone
# from .models import Conversation, Message
# from bots.models import Bot

# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.public_key = self.scope['url_route']['kwargs']['public_key']
        
#         # For live chat, session_id is not in URL, generate one from query params or create new
#         self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        
#         if not self.session_id:
#             # Live chat route - get session from query params or generate
#             query_string = self.scope.get('query_string', b'').decode()
#             params = dict(param.split('=') for param in query_string.split('&') if '=' in param)
#             self.session_id = params.get('session_id', f'live_{self.public_key}_{timezone.now().timestamp()}')
        
#         self.room_group_name = f'chat_{self.public_key}_{self.session_id}'

#         # Join room group
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()
#         print(f"[ChatConsumer] WebSocket connected: {self.room_group_name}")

#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )
#         print(f"[ChatConsumer] WebSocket disconnected: {self.room_group_name}, code: {close_code}")

#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         try:
#             text_data_json = json.loads(text_data)
#             message_type = text_data_json.get('type', 'chat_message')
#             text = text_data_json.get('message', text_data_json.get('text', ''))
            
#             if text and message_type == 'chat_message':
#                 # Determine sender (default to USER for widget, BOT for dashboard)
#                 sender = text_data_json.get('sender', 'USER')
                
#                 # Save message to database
#                 # The post_save signal will handle broadcasting to the group
#                 await self.save_message(text, sender)

#         except json.JSONDecodeError as e:
#             print(f"[ChatConsumer] JSON decode error: {e}")
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': 'Invalid JSON format'
#             }))
#         except Exception as e:
#             print(f"[ChatConsumer] Error in receive: {e}")
#             await self.send(text_data=json.dumps({
#                 'type': 'error',
#                 'message': str(e)
#             }))

#     # Receive message from room group
#     async def chat_message(self, event):
#         text = event['text']
#         sender = event['sender']
#         timestamp = event.get('timestamp')

#         # Send message to WebSocket
#         await self.send(text_data=json.dumps({
#             'type': 'chat_message',
#             'text': text,
#             'sender': sender,
#             'timestamp': timestamp
#         }))

#     @database_sync_to_async
#     def save_message(self, text, sender):
#         try:
#             bot = Bot.objects.get(public_key=self.public_key)
#             conversation, created = Conversation.objects.get_or_create(
#                 bot=bot,
#                 session_id=self.session_id
#             )
            
#             if created:
#                 print(f"[ChatConsumer] Created new conversation: {conversation.id}")
            
#             # Switch to LIVE mode when user sends first message
#             if sender == 'USER' and conversation.effective_mode != 'LIVE':
#                 conversation.effective_mode = 'LIVE'
#                 conversation.save()
            
#             message = Message.objects.create(
#                 conversation=conversation,
#                 sender=sender,
#                 text=text
#             )
#             print(f"[ChatConsumer] Saved message: {message.id} from {sender}")
#             return message
#         except Bot.DoesNotExist:
#             print(f"[ChatConsumer] Bot not found: {self.public_key}")
#             raise Exception("Bot not found")
#         except Exception as e:
#             print(f"[ChatConsumer] Error saving message: {e}")
#             raise



import json
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Conversation, Message
from bots.models import Bot

# Track active dashboard agents per bot
ACTIVE_AGENTS = defaultdict(set)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.public_key = self.scope['url_route']['kwargs']['public_key']
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')

        # Parse query params
        query_string = self.scope.get('query_string', b'').decode()
        self.params = dict(q.split('=') for q in query_string.split('&') if '=' in q)

        # Determine if this connection is from dashboard agent
        self.is_agent = self.params.get('role') == 'agent'

        # Generate session id for live widget if not provided
        if not self.session_id:
            self.session_id = self.params.get(
                'session_id',
                f'live_{self.public_key}_{timezone.now().timestamp()}'
            )

        self.room_group_name = f'chat_{self.public_key}_{self.session_id}'
        self.status_group_name = f'bot_status_{self.public_key}'

        # Join chat group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Join status group
        await self.channel_layer.group_add(
            self.status_group_name,
            self.channel_name
        )

        await self.accept()

        print(f"[ChatConsumer] Connected: {self.room_group_name}")

        # Register agent as online
        if self.is_agent:
            ACTIVE_AGENTS[self.public_key].add(self.channel_name)
            await self.broadcast_status(True)
        
        # Send current status to the new connection
        is_online = bool(ACTIVE_AGENTS[self.public_key])
        await self.send(text_data=json.dumps({
            'type': 'agent_status',
            'online': is_online
        }))

    async def disconnect(self, close_code):

        # Leave chat group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Leave status group
        await self.channel_layer.group_discard(
            self.status_group_name,
            self.channel_name
        )

        # Handle agent disconnect
        if self.is_agent:
            ACTIVE_AGENTS[self.public_key].discard(self.channel_name)

            if not ACTIVE_AGENTS[self.public_key]:
                await self.broadcast_status(False)

        print(f"[ChatConsumer] Disconnected: {self.room_group_name} ({close_code})")

    # ===============================
    # RECEIVE FROM WEBSOCKET
    # ===============================
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get('type', 'chat_message')
            text = data.get('message', data.get('text', ''))

            if msg_type == 'chat_message' and text:
                sender = data.get('sender', 'USER')
                await self.save_message(text, sender)
            
            elif msg_type == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_typing',
                        'sender': data.get('sender', 'USER'),
                        'agent_name': data.get('agent_name', 'Bot')
                    }
                )

        except json.JSONDecodeError as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    # ===============================
    # CHAT MESSAGE BROADCAST
    # ===============================
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'text': event['text'],
            'sender': event['sender'],
            'timestamp': event.get('timestamp')
        }))

    async def chat_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender': event['sender'],
            'agent_name': event['agent_name']
        }))

    # ===============================
    # STATUS BROADCAST HANDLER
    # ===============================
    async def bot_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'online': event['online']
        }))

    async def broadcast_status(self, online):
        await self.channel_layer.group_send(
            self.status_group_name,
            {
                'type': 'bot_status',
                'online': online
            }
        )

    async def bot_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'agent_status',
            'online': event['online']
        }))

    # ===============================
    # DATABASE SAVE
    # ===============================
    @database_sync_to_async
    def save_message(self, text, sender):
        try:
            bot = Bot.objects.get(public_key=self.public_key)

            conversation, created = Conversation.objects.get_or_create(
                bot=bot,
                session_id=self.session_id
            )

            if sender == 'USER' and conversation.effective_mode != 'LIVE':
                conversation.effective_mode = 'LIVE'
                conversation.save()

            message = Message.objects.create(
                conversation=conversation,
                sender=sender,
                text=text
            )

            return message

        except Bot.DoesNotExist:
            raise Exception("Bot not found")
