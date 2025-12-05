# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    is_approved = models.BooleanField(default=False)


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)
    # Toggle whether this workspace shows the bot footer in the embedded widget
    bot_footer = models.BooleanField(default=False)
    # Toggle whether chatbot shows enquiry form (name/phone/email) to visitors
    enable_enquiry_form = models.BooleanField(default=False, help_text="Show name/phone/email form to chat visitors")
    # Toggle whether the bot widget shows the Reset button
    enable_reset_button = models.BooleanField(default=True, help_text="Show the Reset button in the chat widget")
    # Default bot mode for multi-bot plans (FULL, LIVE_QA)
    DEFAULT_BOT_MODES = (
        ('AI', 'AI Bot'),
        ('LIVE', 'Live Chat'),
        ('QA', 'Q&A Bot'),
    )
    default_bot_mode = models.CharField(
        max_length=10,
        choices=DEFAULT_BOT_MODES,
        null=True,
        blank=True,
        help_text="Default bot to show for multi-bot plans (FULL/LIVE_QA)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({'approved' if self.approved else 'pending'})"

    @property
    def active_plan(self):
        """
        Returns the most recent Plan that is currently active (by dates + active flag).
        Uses reverse relation: workspace.plans (from billing.Plan.related_name='plans')
        """
        plans = list(self.plans.all())
        if not plans:
            return None
        # Sort by start_at desc, then pick first that is currently active
        plans.sort(key=lambda p: (p.start_at or timezone.now()), reverse=True)
        for p in plans:
            if p.is_current_active:
                return p
        return None

    @property
    def is_operational(self) -> bool:
        """
        Workspace can operate only if:
        - approved is True
        - has a currently active plan (active flag + within date window if LIMITED)
        """
        ap = self.active_plan
        return bool(self.approved and ap and ap.is_current_active)

    def get_available_bot_modes(self):
        """Get list of available bot modes based on active plan."""
        ap = self.active_plan
        if not ap:
            return []
        
        available = []
        if ap.includes_ai:
            available.append('AI')
        if ap.includes_live:
            available.append('LIVE')
        if ap.includes_qa:
            available.append('QA')
        
        return available
    
    def get_default_bot_mode(self):
        """Get default bot mode based on plan and workspace preference."""
        ap = self.active_plan
        if not ap:
            return 'AI'
        
        # If workspace has explicit preference, validate and use it
        if self.default_bot_mode:
            available = self.get_available_bot_modes()
            if self.default_bot_mode in available:
                return self.default_bot_mode
        
        # Auto-default based on plan bundle
        if ap.bundle == 'FULL':
            return 'AI'
        elif ap.bundle == 'LIVE_QA':
            return 'LIVE'
        elif ap.bundle == 'AI_ONLY':
            return 'AI'
        elif ap.bundle == 'LIVE_ONLY':
            return 'LIVE'
        elif ap.bundle == 'QA_ONLY':
            return 'QA'
        
        return 'AI'  # fallback    