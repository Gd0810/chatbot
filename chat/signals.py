from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Message

@receiver(post_save, sender=Message)
def broadcast_message(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        conversation = instance.conversation
        bot = conversation.bot
        
        room_group_name = f'chat_{bot.public_key}_{conversation.session_id}'
        
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'text': instance.text,
                'sender': instance.sender,
                'timestamp': str(instance.timestamp)
            }
        )
