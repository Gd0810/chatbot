# accounts/views.py
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import Workspace

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