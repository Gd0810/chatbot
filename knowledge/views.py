# knowledge/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .forms import KnowledgeForm
from .models import KnowledgeSource, Chunk
from bots.models import Bot

def _get_user_workspace(user):
    from accounts.models import Workspace
    return Workspace.objects.filter(owner=user).order_by('-created_at').first()

@login_required
def add_knowledge(request, bot_id):
    ws = _get_user_workspace(request.user)
    if not ws or not ws.approved or not ws.is_operational:
        messages.error(request, "Workspace not active or approved.")
        return redirect('accounts:not_allowed')
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    if request.method == 'POST':
        form = KnowledgeForm(request.POST)
        if form.is_valid():
            source = form.save(commit=False)
            source.bot = bot
            source.save()
            # Optional: trigger ingest task
            # ingest_knowledge.delay(source.id)
            messages.success(request, "Knowledge added.")
            return redirect('knowledge:list', bot_id=bot_id)
    else:
        form = KnowledgeForm()
    return render(request, 'knowledge/add.html', {'form': form, 'bot': bot})

@login_required
def list(request, bot_id):
    ws = _get_user_workspace(request.user)
    if not ws or not ws.approved or not ws.is_operational:
        return redirect('accounts:not_allowed')
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    sources = KnowledgeSource.objects.filter(bot=bot)
    return render(request, 'knowledge/list.html', {'sources': sources, 'bot': bot})

@login_required
def detail(request, bot_id, source_id):
    ws = _get_user_workspace(request.user)
    if not ws or not ws.approved or not ws.is_operational:
        return redirect('accounts:not_allowed')
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    source = get_object_or_404(KnowledgeSource, id=source_id, bot=bot)
    chunks = Chunk.objects.filter(source=source)
    return render(request, 'knowledge/detail.html', {'source': source, 'chunks': chunks, 'bot': bot})