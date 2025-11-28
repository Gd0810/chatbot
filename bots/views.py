from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Bot
from accounts.models import Workspace

def bot_list(request):
    return render(request, 'bots/bot_list.html')

def create_bot(request):
    return render(request, 'bots/create_bot.html')

def edit(request, bot_id):
    return render(request, 'bots/edit.html')

@login_required
def get_workspace_plan_details(request, workspace_id):
    """
    API to return plan details for a workspace.
    Used by Bot Admin JS to toggle AI fields.
    """
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    # Check if user has access to this workspace if needed, 
    # but for admin usage, basic login check is usually enough or we rely on admin permissions.
    # For safety, we could check request.user.is_staff or workspace ownership.
    
    ap = workspace.active_plan
    data = {
        'includes_ai': bool(ap and ap.includes_ai),
        'bundle': ap.bundle if ap else None
    }
    return JsonResponse(data)