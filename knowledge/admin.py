from django.contrib import admin
from django import forms
from .models import KnowledgeSource, Chunk
from bots.models import Bot


# ---------------------------------------------
# KnowledgeSource Admin
# ---------------------------------------------
class KnowledgeSourceAdminForm(forms.ModelForm):
    class Meta:
        model = KnowledgeSource
        fields = ['bot','title','source_type', 'content', 'status']

    def clean(self):
        cleaned = super().clean()
        return cleaned


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    actions = ['delete_selected_sources']
    form = KnowledgeSourceAdminForm
    list_display = ['bot', 'workspace', 'source_type', 'status', 'created_at', 'text_preview']
    list_filter = ['source_type', 'status', 'bot__workspace__approved']
    search_fields = ['content', 'bot__name', 'bot__workspace__name']

    def workspace(self, obj):
        return obj.bot.workspace

    def text_preview(self, obj):
        txt = (obj.content or '').strip().replace('\n', ' ')
        return (txt[:80] + '...') if len(txt) > 80 else txt
    text_preview.short_description = 'Preview'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'bot':
            kwargs['queryset'] = Bot.objects.filter(workspace__approved=True, is_enabled=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    def delete_selected_sources(self, request, queryset):
        for src in queryset:
            src.delete()
        self.message_user(request, "Selected sources deleted (with Qdrant vectors).")
    delete_selected_sources.short_description = "Delete selected KnowledgeSources (cleanup vectors)"


# ---------------------------------------------
# Chunk Admin (Automated text + embedding + Qdrant upload)
# ---------------------------------------------

@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ['knowledge_source', 'vector_id', 'text_preview']
    search_fields = ['text', 'vector_id', 'knowledge_source__bot__name']
    readonly_fields = ['vector_id', 'created_at']
    fieldsets = (
        ("Knowledge Source", {'fields': ('knowledge_source',)}),
        ("Chunk Details", {'fields': ('text', 'embedding', 'vector_id')}),
        ("Qdrant Config", {'fields': ('qdrant_url', 'qdrant_api_key', )}),
        ("Timestamps", {'fields': ('created_at',)}),
    )

    def text_preview(self, obj):
        return (obj.text[:80] + "...") if obj.text and len(obj.text) > 80 else obj.text
    text_preview.short_description = "Preview"


    def save_model(self, request, obj, form, change):
        if obj.knowledge_source and not change:
            # Auto-fill from knowledge source
            obj.text = obj.knowledge_source.content
            if hasattr(obj.knowledge_source, 'embedding') and obj.knowledge_source.embedding:
                obj.embedding = obj.knowledge_source.embedding

        # Save locally first
        super().save_model(request, obj, form, change)

        # Push to Qdrant if API details are present
        if obj.qdrant_url and obj.qdrant_api_key and obj.embedding:
            try:
                obj.push_to_qdrant()   # ✅ call instance method
            except Exception as e:
                self.message_user(request, f"⚠️ Qdrant upload failed: {e}", level='error')

from .models import QAPair

@admin.register(QAPair)
class QAPairAdmin(admin.ModelAdmin):
    list_display = ['bot', 'question', 'parent', 'order', 'created_at']
    list_filter = ['bot', 'created_at']
    search_fields = ['question', 'answer', 'bot__name']
    ordering = ['bot', 'order', 'created_at']
