from django import forms
from .models import Bot

class BotForm(forms.ModelForm):
    ai_api_key = forms.CharField(max_length=255, required=False, help_text="Enter OpenAI API Key")

    class Meta:
        model = Bot
        fields = ['workspace', 'name', 'preferred_mode', 'ai_provider', 'ai_model', 'ai_api_key', 'allowed_domains', 'is_enabled']