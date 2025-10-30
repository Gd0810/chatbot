# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Workspace

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'is_staff', 'is_approved']
    list_filter = ['is_staff', 'is_approved']
    search_fields = ['username', 'email']


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'approved', 'operational', 'active_plan_bundle', 'created_at']
    list_filter = ['approved', 'owner']
    search_fields = ['name', 'owner__username']
    actions = ['approve_workspaces', 'reject_workspaces']

    def operational(self, obj):
        return obj.is_operational
    operational.boolean = True
    operational.short_description = 'Operational'

    def active_plan_bundle(self, obj):
        ap = obj.active_plan
        return ap.bundle if ap else '—'
    active_plan_bundle.short_description = 'Active Plan'

    def approve_workspaces(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f"{updated} workspace(s) approved.")
    approve_workspaces.short_description = "Approve selected workspaces"

    def reject_workspaces(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f"{updated} workspace(s) rejected.")
    reject_workspaces.short_description = "Reject selected workspaces"