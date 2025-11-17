import uuid
from urllib.parse import urlparse

from django.db import models
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from accounts.models import Workspace
from redbot.settings import FERNET

def generate_public_key():
    return str(uuid.uuid4().hex)

SUPPORTED_PROVIDERS = [
    ('google', 'Google'),
    ('openai', 'OpenAI'),
    ('openrouter', 'OpenRouter'),
    ('anthropic', 'Anthropic'),
    ('xai', 'xAI'),
    ('cohere', 'Cohere'),
    ('huggingface', 'Hugging Face'),
    ('deepseek', 'DeepSeek'),
    ('meta', 'Meta AI'),
    ('mistral', 'Mistral AI'),
    ('groq', 'Groq'),
    ('togetherai', 'Together AI'),
    ('perplexity', 'Perplexity AI'),
    ('replicate', 'Replicate'),
    ('alezeia', 'Alezeia'),
]

class Bot(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default='Redbot')
    public_key = models.CharField(max_length=255, unique=True, default=generate_public_key)
    preferred_mode = models.CharField(max_length=10, default='AI')

    # AI config
    ai_provider = models.CharField(max_length=50, choices=SUPPORTED_PROVIDERS, default='openrouter', blank=True, null=True)
    ai_model = models.CharField(max_length=255, default='gpt-4o', blank=True, null=True)
    _ai_api_key = models.BinaryField(null=True, blank=True)

    # Embedding security
    allowed_domains = models.TextField(blank=True, help_text="One hostname per line, e.g., localhost, 127.0.0.1")

    # Enable/disable
    is_enabled = models.BooleanField(default=True)

    # UI Styling
    ui_primary_color = models.CharField(max_length=7, default="#2563eb")  # HEX
    ui_font_family = models.CharField(
        max_length=200,
        default="Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif"
    )
    ui_font_size = models.PositiveSmallIntegerField(default=14)  # px
    ui_welcome_message = models.CharField(max_length=255, default="Hi! I'm {name}. How can I help you?")
    ui_sound_enabled = models.BooleanField(default=True)
    ui_bg_color = models.CharField(
        max_length=7, 
        default='#f9fafb',
        help_text='Chat background color (hex)'
    )
    
    ui_animation_speed = models.CharField(
        max_length=10,
        default='normal',
        choices=[
            ('normal', 'Normal'),
            ('fast', 'Fast'),
            ('slow', 'Slow'),
            ('none', 'None (Accessibility)'),
        ]
    )
    
    ui_widget_position = models.CharField(
        max_length=15,
        default='bottom-right',
        choices=[
            ('bottom-right', 'Bottom Right'),
            ('bottom-left', 'Bottom Left'),
        ]
    )
    

    def __str__(self):
        return self.name

    # Encryption proxy
    @property
    def ai_api_key(self):
        if self._ai_api_key:
            return FERNET.decrypt(self._ai_api_key).decode()
        return None

    @ai_api_key.setter
    def ai_api_key(self, value):
        if value is None or value == '':
            self._ai_api_key = None
        else:
            self._ai_api_key = FERNET.encrypt(value.encode())

    @cached_property
    def active_plan(self):
        try:
            return self.workspace.active_plan
        except Exception:
            return None

    @property
    def plan_includes_ai(self) -> bool:
        ap = self.active_plan
        return bool(ap and getattr(ap, 'includes_ai', False))

    @property
    def plan_includes_live(self) -> bool:
        ap = self.active_plan
        return bool(ap and getattr(ap, 'includes_live', False))

    @property
    def plan_includes_qa(self) -> bool:
        ap = self.active_plan
        return bool(ap and getattr(ap, 'includes_qa', False))

    @property
    def is_operational(self) -> bool:
        try:
            return bool(self.is_enabled and self.workspace.is_operational)
        except Exception:
            return bool(self.is_enabled)

    def parsed_allowed_domains(self):
        if not self.allowed_domains:
            return []
        raw = self.allowed_domains.replace(',', '\n').splitlines()
        domains = [d.strip().lower() for d in raw if d.strip()]
        return list(dict.fromkeys(domains))

    def is_origin_allowed(self, origin: str) -> bool:
        try:
            host = (urlparse(origin).hostname or '').lower()
        except Exception:
            host = ''
        if not host:
            return False
        for rule in self.parsed_allowed_domains():
            r = rule.lstrip('.')
            if host == r or host.endswith('.' + r):
                return True
        return False
    
    def clean(self):
        # Workspace must be operational to create/enable bots
        if not self.workspace.approved:
            raise ValidationError("Workspace is not approved.")
        ap = self.active_plan
        if not ap or not ap.is_current_active:
            raise ValidationError("Workspace does not have an active plan.")

        # Enforce AI fields presence/absence based on plan
        if self.plan_includes_ai:
            if not self.ai_provider or not self.ai_model:
                raise ValidationError("ai_provider and ai_model are required for plans that include AI.")
        else:
            # Plans without AI must not store provider/model/API key
            if self.ai_provider or self.ai_model or self._ai_api_key:
                raise ValidationError("This workspace plan does not include AI. Remove ai_provider/ai_model/API key.")

    # Allowed domains helpers
    def parsed_allowed_domains(self):
        if not self.allowed_domains:
            return []
        raw = self.allowed_domains.replace(',', '\n').splitlines()
        domains = [d.strip().lower() for d in raw if d.strip()]
        return list(dict.fromkeys(domains))  # unique, preserve order

    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if an origin (e.g., http://app.example.com) is allowed by this bot.
        - Matches exact host or parent domain (example.com allows subdomains too).
        """
        try:
            host = urlparse(origin).hostname or ''
        except Exception:
            host = ''
        host = (host or '').lower()
        if not host:
            return False
        allowed = self.parsed_allowed_domains()
        if not allowed:
            # In dev, you might bypass this. In production, enforce non-empty list.
            return False
        for rule in allowed:
            rule = rule.lstrip('.')
            if host == rule or host.endswith(f".{rule}"):
                return True
        return False


class BotFooter(models.Model):
    """Footer configuration per workspace for showing a small "Powered by" link in the widget.

    Fields mirror the user's request names (c_name, c_url) and link to a Workspace.
    """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='bot_footers')
    c_name = models.CharField(max_length=255, default='Redback')
    c_url = models.URLField(default='https://redback.in/')

    class Meta:
        verbose_name = 'Bot Footer'
        verbose_name_plural = 'Bot Footers'

    def __str__(self):
        return f"{self.c_name} ({self.workspace})"


class BotEnquiry(models.Model):
    """Stores form submissions (name, phone, email) from users who chat with the bot.
    
    Each enquiry is linked to a workspace so the workspace owner can view all
    form submissions from their chatbot widget.
    """
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='bot_enquiries')
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bot Enquiry'
        verbose_name_plural = 'Bot Enquiries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name or 'Anonymous'} - {self.email or self.phone or 'No contact'} ({self.workspace})"