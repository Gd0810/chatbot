from django import forms
from .models import Bot

class BotForm(forms.ModelForm):
    ai_api_key = forms.CharField(max_length=255, required=False, help_text="Enter OpenAI API Key")

    class Meta:
        model = Bot
        fields = ['workspace', 'name', 'preferred_mode', 'ai_provider', 'ai_model', 'ai_api_key', 'allowed_domains', 'is_enabled']


class BotStyleForm(forms.ModelForm):
    """A small ModelForm to expose UI styling fields for admin or other editors.

    This form intentionally only includes UI-related fields so it can be used
    where styling controls are needed without touching other bot settings.
    """

    class Meta:
        model = Bot
        fields = [
            'ui_primary_color', 'ui_bg_color', 'ui_font_family', 'ui_font_size',
            'ui_welcome_message', 'ui_sound_enabled', 'ui_animation_speed', 'ui_widget_position'
        ]