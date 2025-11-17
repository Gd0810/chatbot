# bots/admin.py
from django.contrib import admin
from django import forms
from django.utils.html import format_html

from .models import Bot, BotFooter, BotEnquiry


class BotAdminForm(forms.ModelForm):
    # Expose a plain text field for API key; stored encrypted
    ai_api_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text="Will be stored encrypted."
    )

    class Meta:
        model = Bot
        fields = [
            'workspace', 'name', 'preferred_mode',
            'ai_provider', 'ai_model', 'ai_api_key',
            'allowed_domains', 'is_enabled',
            # UI Styling fields
            'ui_primary_color', 'ui_bg_color', 'ui_font_family', 'ui_font_size',
            'ui_welcome_message', 'ui_sound_enabled', 'ui_animation_speed', 'ui_widget_position'
        ]

    def clean(self):
        cleaned = super().clean()
        # Let model.clean() enforce plan rules (AI fields req/forbidden)
        return cleaned



@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    form = BotAdminForm
    list_display = [
        'name', 'workspace', 'bundle', 'ai_display', 'enabled', 'operational', 'public_key_short'
    ]
    list_filter = ['is_enabled', 'workspace__approved', 'workspace__plans__bundle']
    search_fields = ['name', 'public_key', 'workspace__name']
    readonly_fields = ['public_key']
    actions = ['enable_bots', 'disable_bots']

    def ai_display(self, obj):
        if obj.ai_provider and obj.ai_model:
            return f"{obj.ai_provider} / {obj.ai_model}"
        return "—"
    ai_display.short_description = 'AI'

    def enabled(self, obj):
        return obj.is_enabled
    enabled.boolean = True

    def operational(self, obj):
        return obj.is_operational
    operational.boolean = True

    def bundle(self, obj):
        ap = obj.active_plan
        return ap.bundle if ap else '—'

    def public_key_short(self, obj):
        return f"{obj.public_key[:8]}..." if obj.public_key else "Not generated"
    public_key_short.short_description = 'Public Key'

    def get_form(self, request, obj=None, **kwargs):
        """
        Hide AI fields if the workspace active plan does not include AI.
        When adding (obj is None), we can't know until workspace chosen, so we show fields;
        model.clean() will still enforce rules on save.
        """
        form = super().get_form(request, obj, **kwargs)
        if obj:
            ap = obj.active_plan
            includes_ai = bool(ap and ap.includes_ai)
            if not includes_ai:
                # Dynamically remove AI-related fields
                if 'ai_provider' in form.base_fields:
                    form.base_fields['ai_provider'].widget = forms.HiddenInput()
                if 'ai_model' in form.base_fields:
                    form.base_fields['ai_model'].widget = forms.HiddenInput()
                if 'ai_api_key' in form.base_fields:
                    form.base_fields['ai_api_key'].widget = forms.HiddenInput()
        return form

    def save_model(self, request, obj, form, change):
        # Handle API key encryption on save
        api_key_input = form.cleaned_data.get('ai_api_key')
        if api_key_input is not None:
            # If empty string provided, clear key
            obj.ai_api_key = api_key_input or None
        obj.full_clean()
        super().save_model(request, obj, form, change)

    @admin.action(description="Enable selected bots")
    def enable_bots(self, request, queryset):
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f"Enabled {updated} bot(s).")

    @admin.action(description="Disable selected bots")
    def disable_bots(self, request, queryset):
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f"Disabled {updated} bot(s).")


@admin.register(BotFooter)
class BotFooterAdmin(admin.ModelAdmin):
    """Admin for BotFooter to allow creating/editing the powered-by footer per workspace."""
    list_display = ['c_name', 'c_url', 'workspace']
    search_fields = ['c_name', 'workspace__name']
    list_filter = ['workspace']
    raw_id_fields = ('workspace',)
    ordering = ('workspace__name', 'c_name')


@admin.register(BotEnquiry)
class BotEnquiryAdmin(admin.ModelAdmin):
    """Admin for viewing form submissions from chat visitors."""
    list_display = ['name', 'phone', 'email', 'workspace', 'created_at']
    list_filter = ['workspace', 'created_at']
    search_fields = ['name', 'phone', 'email', 'workspace__name']
    readonly_fields = ['created_at']
    raw_id_fields = ('workspace',)
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        """Prevent manual creation in admin; only stored from widget form."""
        return False