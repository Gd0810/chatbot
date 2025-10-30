# billing/models.py
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Plan(models.Model):
    BUNDLES = (
        ('FULL', 'Full (AI + Live + Q&A)'),
        ('LIVE_QA', 'Live + Q&A'),
        ('AI_ONLY', 'AI Only'),
        ('LIVE_ONLY', 'Live Only'),
        ('QA_ONLY', 'Q&A Only'),
    )
    TERMS = (
        ('LIFETIME', 'Lifetime'),
        ('LIMITED', 'Limited Time Window'),
    )

    workspace = models.ForeignKey('accounts.Workspace', on_delete=models.CASCADE, related_name='plans')
    bundle = models.CharField(max_length=20, choices=BUNDLES, default='AI_ONLY')
    term = models.CharField(max_length=20, choices=TERMS, default='LIFETIME')

    # Use DateTime for accurate timing
    start_at = models.DateTimeField(default=timezone.now, help_text="When the plan starts being active.")
    end_at = models.DateTimeField(null=True, blank=True, help_text="Required if term is LIMITED.")
    active = models.BooleanField(default=True, help_text="Set inactive to pause this plan immediately.")

    class Meta:
        constraints = [
            # Enforce at most one 'active' plan per workspace at a time
            models.UniqueConstraint(
                fields=['workspace'],
                condition=Q(active=True),
                name='unique_active_plan_per_workspace'
            )
        ]

    def __str__(self):
        return f"{self.workspace.name}: {self.get_bundle_display()} ({self.get_term_display()})"

    @property
    def includes_ai(self) -> bool:
        return self.bundle in ('FULL', 'AI_ONLY')

    @property
    def includes_live(self) -> bool:
        return self.bundle in ('FULL', 'LIVE_ONLY', 'LIVE_QA')

    @property
    def includes_qa(self) -> bool:
        return self.bundle in ('FULL', 'QA_ONLY', 'LIVE_QA')

    @property
    def is_current_active(self) -> bool:
        """
        True only if:
        - active == True
        - term == LIFETIME -> always active
        - term == LIMITED -> now within [start_at, end_at]
        """
        if not self.active:
            return False
        if self.term == 'LIFETIME':
            return True
        # LIMITED
        if not self.end_at:
            return False
        now = timezone.now()
        return (self.start_at or now) <= now <= self.end_at

    def clean(self):
        from django.core.exceptions import ValidationError
        # Validate LIMITED has end_at and that it is after start_at
        if self.term == 'LIMITED':
            if not self.end_at:
                raise ValidationError({"end_at": "end_at is required for LIMITED term."})
            if self.start_at and self.end_at <= self.start_at:
                raise ValidationError({"end_at": "end_at must be after start_at."})

    def save(self, *args, **kwargs):
        # Ensure model-level validation always runs
        self.full_clean()
        super().save(*args, **kwargs)