# accounts/views.py
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import Workspace, Contact
from .forms import TailwindPasswordChangeForm, ContactForm

def _get_user_workspace(user):
    # If you allow multiple, pick the latest; else first()
    return Workspace.objects.filter(owner=user).order_by('-created_at').first()

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            ws = _get_user_workspace(user)
            if not ws:
                messages.warning(request, "Your workspace is not created yet. Please contact support.")
                return redirect('accounts:not_allowed')
            if not ws.approved:
                messages.warning(request, "Your workspace is not approved yet.")
                return redirect('accounts:not_allowed')
            if not ws.is_operational:
                messages.warning(request, "Your plan is not active or expired.")
                return redirect('accounts:not_allowed')
            messages.success(request, f"Welcome, {user.username}!")
            return redirect('dashboard:index')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('accounts:login')

@login_required
def not_allowed(request):
    ws = _get_user_workspace(request.user)
    reason = "unknown"
    detail = "Access restricted."
    if not ws:
        reason = "no_workspace"
        detail = "No workspace found. Contact support."
    elif not ws.approved:
        reason = "not_approved"
        detail = "Your workspace is pending approval."
    elif not ws.is_operational:
        ap = ws.active_plan
        if ap and ap.term == 'LIMITED':
            reason = "out_of_plan"
            detail = "Your plan period has ended. Please renew."
        else:
            reason = "inactive_plan"
            detail = "Your plan is not active."
    return render(request, 'accounts/not_allowed.html', {
        'workspace': ws,
        'reason': reason,
        'detail': detail
    })
    
# accounts/views.py (add/replace this view)
@login_required
def password_change_view(request):
    """
    HTMX-friendly password change.
    - GET: returns the password change partial form.
    - POST (valid): updates password and returns the updated account panel.
    - POST (invalid): returns the form partial with errors.
    """
    if request.method == 'POST':
        form = TailwindPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # keep user logged in
            messages.success(request, "Your password has been updated.")

            # Re-render the account panel into #main
            ws = _get_user_workspace(request.user)
            return render(request, 'dashboard/partials/account.html', {
                'user': request.user,
                'workspace': ws
            })
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, 'accounts/partials/password_change.html', {'form': form})
    else:
        form = TailwindPasswordChangeForm(user=request.user)
        return render(request, 'accounts/partials/password_change.html', {'form': form})




def index(request):
    return render(request, "pages/index.html", {
        "meta_title": "AI, Live & FAQ Chatbot Services in Vellore | Chatbot Solutions",
        "meta_description": "We provide AI chatbot, live chat, and FAQ chatbot solutions for businesses in Vellore, Tamil Nadu. Automate support and boost customer engagement.",
        "meta_keywords": "chatbot services vellore, ai chatbot vellore, live chat support tamil nadu, faq chatbot solutions, business automation chatbot, customer support ai",
    })


def services(request):
    return render(request, "pages/service.html", {
        "meta_title": "Chatbot Development Services in Vellore | AI & Live Chat Solutions",
        "meta_description": "Explore our chatbot services including AI chatbots, live chat integration, and FAQ automation for businesses in Vellore and across Tamil Nadu.",
        "meta_keywords": "chatbot development services, ai chatbot development india, live chatbot integration, faq automation bots, vellore chatbot company",
    })


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you! Your contact information has been submitted. We will get back to you soon.")
            return redirect('accounts:contact')
        else:
            messages.error(request, "There was an error submitting the form. Please try again.")
    else:
        form = ContactForm()
    
    return render(request, "pages/contact.html", {
        "meta_title": "Contact Chatbot Experts in Vellore | Get AI Chatbot Solutions",
        "meta_description": "Contact our chatbot development team in Vellore, Tamil Nadu for AI chatbot, live chat or FAQ bot solutions tailored for your business.",
        "meta_keywords": "contact chatbot company vellore, ai chatbot consultation tamil nadu, chatbot support services, business automation contact",
        "form": form,
    })

def about(request):
    return render(request, "pages/about.html", {
        "meta_title": "About Us | My Django Website",
        "meta_description": "About our Django team",
        "meta_keywords": "about, django company",
    })      


def aibot(request):
    return render(request, "pages/ai-chatbot-provider-in-vellore.html", {
        "meta_title": "AI Chatbot Provider in Vellore | My Django Website",
        "meta_description": "AI Chatbot Provider in Vellore | My Django Website",
        "meta_keywords": "AI Chatbot Provider in Vellore | My Django Website",
    })      

def livebot(request):
    return render(request, "pages/live-chatbot-provider-in-vellore.html", {
        "meta_title": "Live Chatbot Provider in Vellore | My Django Website",
        "meta_description": "Live Chatbot Provider in Vellore | My Django Website",
        "meta_keywords": "Live Chatbot Provider in Vellore | My Django Website",
    })      

def faqbot(request):
    return render(request, "pages/faq-chatbot-provider-in-vellore.html", {
        "meta_title": "FAQ Chatbot Provider in Vellore | My Django Website",
        "meta_description": "FAQ Chatbot Provider in Vellore | My Django Website",
        "meta_keywords": "FAQ Chatbot Provider in Vellore | My Django Website",
    })         