from rest_framework import serializers
from .models import Message

class ChatSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    session_id = serializers.CharField(required=True)
    jwt = serializers.CharField(required=True)  # From widget