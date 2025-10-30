# bots/models.py
import uuid
from urllib.parse import urlparse

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from accounts.models import Workspace
from redbot.settings import FERNET  # you already have this

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

    # AI fields are optional — hidden/disabled when plan lacks AI
    ai_provider = models.CharField(max_length=50, choices=SUPPORTED_PROVIDERS, default='openrouter', blank=True, null=True)
    ai_model = models.CharField(max_length=255, default='gpt-4o', blank=True, null=True)
    _ai_api_key = models.BinaryField(null=True, blank=True)

    allowed_domains = models.TextField(
        blank=True,
        help_text="One domain per line or comma-separated. Examples: example.com, app.example.com"
    )
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    # Encryption proxy field
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
        return self.workspace.active_plan

    @property
    def is_operational(self) -> bool:
        """
        Bot is operational only if workspace is operational and bot is enabled.
        """
        return bool(self.is_enabled and self.workspace.is_operational)

    @property
    def plan_includes_ai(self) -> bool:
        ap = self.active_plan
        return bool(ap and ap.includes_ai)

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