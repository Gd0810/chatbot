# accounts/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import Contact

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


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'gmail', 'whatsappnumber', 'business_name', 'plane']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CONTACT_INPUT = 'contact-input'
        
        self.fields['name'].widget.attrs.update({
            'class': CONTACT_INPUT,
            'placeholder': 'Enter your Name',
        })
        self.fields['gmail'].widget.attrs.update({
            'class': CONTACT_INPUT,
            'placeholder': 'Enter a valid email address',
            'type': 'email',
        })
        self.fields['whatsappnumber'].widget.attrs.update({
            'class': CONTACT_INPUT,
            'placeholder': 'Enter your WhatsApp Number',
        })
        self.fields['business_name'].widget.attrs.update({
            'class': CONTACT_INPUT,
            'placeholder': 'Your business name',
        })
        self.fields['plane'].widget.attrs.update({
            'class': CONTACT_INPUT,
            'placeholder': 'Select a plan',
        })