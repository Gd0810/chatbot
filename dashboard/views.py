# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone

from accounts.models import Workspace
from billing.models import Plan
from bots.models import Bot
from knowledge.models import KnowledgeSource

def _get_user_workspace(user):
    return Workspace.objects.filter(owner=user).order_by('-created_at').first()

def _require_operational(request):
    ws = _get_user_workspace(request.user)
    if not ws:
        messages.error(request, "No workspace found.")
        return None, redirect('accounts:not_allowed')
    if not ws.approved or not ws.is_operational:
        messages.error(request, "Workspace not active.")
        return ws, redirect('accounts:not_allowed')
    return ws, None

@login_required
def index(request):
    ws = _get_user_workspace(request.user)
    if not ws or not ws.approved or not ws.is_operational:
        return redirect('accounts:not_allowed')
    return render(request, 'dashboard/index.html', {'workspace': ws})

# Partials

@login_required
def partial_account(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    return render(request, 'dashboard/partials/account.html', {
        'user': request.user,
        'workspace': ws
    })

@login_required
def partial_plan(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    plan = ws.active_plan
    remaining = None
    if plan and plan.term == 'LIMITED' and plan.end_at:
        delta = plan.end_at - timezone.now()
        remaining = delta if delta.total_seconds() > 0 else None
    return render(request, 'dashboard/partials/plan.html', {
        'workspace': ws,
        'plan': plan,
        'remaining': remaining,
    })

@login_required
def partial_bots(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bots = Bot.objects.filter(workspace=ws).order_by('-id')
    plan = ws.active_plan
    return render(request, 'dashboard/partials/bots.html', {
        'workspace': ws,
        'bots': bots,
        'plan': plan,
    })

@login_required
def partial_knowledge(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    plan = ws.active_plan
    bots = Bot.objects.filter(workspace=ws, is_enabled=True).order_by('name')
    sources = KnowledgeSource.objects.filter(bot__workspace=ws).select_related('bot').order_by('-created_at')
    return render(request, 'dashboard/partials/knowledge.html', {
        'workspace': ws,
        'plan': plan,
        'bots': bots,
        'sources': sources
    })

@login_required
def partial_live(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    # Only show if plan includes LIVE
    plan = ws.active_plan
    includes_live = bool(plan and plan.includes_live)
    return render(request, 'dashboard/partials/live.html', {
        'workspace': ws,
        'includes_live': includes_live
    })

# Actions

@login_required
def toggle_bot(request, bot_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    bot.is_enabled = not bot.is_enabled
    bot.save()
    messages.success(request, f"Bot {'enabled' if bot.is_enabled else 'disabled'}.")
    # Return the refreshed bots panel (HTMX)
    bots = Bot.objects.filter(workspace=ws).order_by('-id')
    plan = ws.active_plan
    return render(request, 'dashboard/partials/bots.html', {
        'workspace': ws, 'bots': bots, 'plan': plan
    })

@login_required
def bot_edit(request, bot_id):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    plan = ws.active_plan

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            bot.name = name
        if plan and plan.includes_ai:
            bot.ai_provider = request.POST.get('ai_provider') or bot.ai_provider
            bot.ai_model = request.POST.get('ai_model') or bot.ai_model
            api_key = request.POST.get('ai_api_key', '')
            if api_key != '':
                bot.ai_api_key = api_key  # setter encrypts; empty string clears
        else:
            # Strip AI fields on non-AI bundles
            bot.ai_provider = None
            bot.ai_model = None
            bot.ai_api_key = None
        try:
            bot.full_clean()
            bot.save()
            messages.success(request, "Bot updated.")
        except Exception as e:
            messages.error(request, f"Failed to update bot: {e}")

    return render(request, 'dashboard/partials/bot_edit.html', {
        'bot': bot, 'plan': plan
    })

@login_required
def knowledge_add(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    plan = ws.active_plan
    if not plan or (not plan.includes_ai and not plan.includes_qa):
        messages.error(request, "Your plan does not include AI or Q&A.")
        return redirect('dashboard:partial_knowledge')

    if request.method == 'POST':
        bot_id = request.POST.get('bot_id')
        source_type = request.POST.get('source_type')
        content = request.POST.get('content', '')
        bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
        ks = KnowledgeSource(bot=bot, source_type=source_type, content=content)
        try:
            ks.full_clean()
            ks.save()
            messages.success(request, "Knowledge saved.")
        except Exception as e:
            messages.error(request, f"Failed to save knowledge: {e}")

    # Render refreshed list
    bots = Bot.objects.filter(workspace=ws, is_enabled=True).order_by('name')
    sources = KnowledgeSource.objects.filter(bot__workspace=ws).select_related('bot').order_by('-created_at')
    return render(request, 'dashboard/partials/knowledge.html', {
        'workspace': ws, 'plan': plan, 'bots': bots, 'sources': sources
    })

@login_required
def knowledge_edit(request, source_id):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)
    if request.method == 'POST':
        ks.source_type = request.POST.get('source_type') or ks.source_type
        ks.content = request.POST.get('content', ks.content)
        try:
            ks.full_clean()
            ks.save()
            messages.success(request, "Knowledge updated.")
        except Exception as e:
            messages.error(request, f"Failed to update knowledge: {e}")

    # Re-render the knowledge panel
    plan = ws.active_plan
    bots = Bot.objects.filter(workspace=ws, is_enabled=True).order_by('name')
    sources = KnowledgeSource.objects.filter(bot__workspace=ws).select_related('bot').order_by('-created_at')
    return render(request, 'dashboard/partials/knowledge.html', {
        'workspace': ws, 'plan': plan, 'bots': bots, 'sources': sources
    })