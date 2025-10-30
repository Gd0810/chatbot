from django import forms
from .models import KnowledgeSource

class KnowledgeForm(forms.ModelForm):
    class Meta:
        model = KnowledgeSource
        fields = ['source_type', 'content']