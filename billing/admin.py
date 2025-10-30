# billing/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Plan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        'workspace', 'bundle', 'term', 'active',
        'start_at', 'end_at', 'is_active_now',
        'includes_ai', 'includes_live', 'includes_qa'
    ]
    list_filter = ['bundle', 'term', 'active', 'workspace__approved']
    search_fields = ['workspace__name']
    actions = ['deactivate_expired', 'activate_selected', 'deactivate_selected']

    def is_active_now(self, obj):
        return obj.is_current_active
    is_active_now.boolean = True
    is_active_now.short_description = "Active Now"

    @admin.action(description="Deactivate expired (LIMITED) plans")
    def deactivate_expired(self, request, queryset):
        now = timezone.now()
        qs = queryset.filter(term='LIMITED', end_at__lt=now, active=True)
        count = qs.update(active=False)
        self.message_user(request, f"Deactivated {count} expired plan(s).")

    @admin.action(description="Activate selected plans (will fail if uniqueness violated)")
    def activate_selected(self, request, queryset):
        updated = 0
        for plan in queryset:
            plan.active = True
            try:
                plan.save()
                updated += 1
            except Exception as e:
                self.message_user(request, f"Failed to activate {plan}: {e}", level='error')
        self.message_user(request, f"Activated {updated} plan(s).")

    @admin.action(description="Deactivate selected plans")
    def deactivate_selected(self, request, queryset):
        count = queryset.update(active=False)
        self.message_user(request, f"Deactivated {count} plan(s).")