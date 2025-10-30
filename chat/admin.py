from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['bot', 'session_id', 'effective_mode', 'created_at']
    list_filter = ['effective_mode', 'bot__workspace']
    search_fields = ['session_id']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'sender', 'timestamp', 'text_preview']
    list_filter = ['sender', 'conversation__bot__workspace']
    search_fields = ['text']
    
    def text_preview(self, obj):
        return obj.text[:50] + "..."
    text_preview.short_description = 'Message Preview'