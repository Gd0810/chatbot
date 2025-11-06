# accounts/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm

TAILWIND_INPUT = "border rounded px-2 py-1 w-full"

class TailwindPasswordChangeForm(PasswordChangeForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'class': TAILWIND_INPUT,
            'placeholder': 'Current password',
            'autocomplete': 'current-password',
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': TAILWIND_INPUT,
            'placeholder': 'New password',
            'autocomplete': 'new-password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': TAILWIND_INPUT,
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
        })