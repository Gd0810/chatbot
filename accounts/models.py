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