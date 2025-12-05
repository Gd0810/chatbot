# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from .models import User, Workspace

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'is_staff', 'is_approved']
    list_filter = ['is_staff', 'is_approved']
    search_fields = ['username', 'email']


class WorkspaceAdminForm(forms.ModelForm):
    """Custom form to dynamically filter default_bot_mode choices based on workspace plan."""
    
    class Meta:
        model = Workspace
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If editing an existing workspace, filter choices based on active plan
        if self.instance and self.instance.pk:
            available_modes = self.instance.get_available_bot_modes()
            
            # Only show the field if there are multiple bot modes available
            if len(available_modes) > 1:
                # Filter choices to only show available modes
                all_choices = [('', '-- Auto (based on plan) --')]
                for mode in available_modes:
                    # Find the matching choice from DEFAULT_BOT_MODES
                    for choice_value, choice_label in Workspace.DEFAULT_BOT_MODES:
                        if choice_value == mode:
                            all_choices.append((choice_value, choice_label))
                            break
                
                self.fields['default_bot_mode'].choices = all_choices
            else:
                # Hide the field for single-bot plans
                self.fields['default_bot_mode'].widget = forms.HiddenInput()
                self.fields['default_bot_mode'].required = False


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    form = WorkspaceAdminForm
    list_display = ['name', 'owner', 'approved', 'operational', 'active_plan_bundle', 'created_at', 'enable_reset_button']
    list_filter = ['approved', 'owner', 'enable_reset_button']
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