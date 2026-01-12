from django.db import models
from bots.models import Bot

class Conversation(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255)  # Unique per user session
    effective_mode = models.CharField(max_length=10, default='AI')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def last_message(self):
        msg = self.message_set.order_by('-timestamp').first()
        return msg.text if msg else None

    @property
    def updated_at(self):
        msg = self.message_set.order_by('-timestamp').first()
        return msg.timestamp if msg else self.created_at

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    sender = models.CharField(max_length=10, choices=(('USER', 'User'), ('BOT', 'Bot')))
    text = models.TextField()
    sources = models.TextField(blank=True)  # JSON of RAG sources
    timestamp = models.DateTimeField(auto_now_add=True)