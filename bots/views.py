from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import BotForm
from .models import Bot
import uuid

@login_required
def create_bot(request):
    if request.method == 'POST':
        form = BotForm(request.POST)
        if form.is_valid():
            bot = form.save(commit=False)
            bot.workspace = request.user.workspace  # Assume user has workspace
            bot.public_key = uuid.uuid4().hex
            if form.cleaned_data['ai_api_key']:
                bot.ai_api_key = form.cleaned_data['ai_api_key']  # Encrypts via setter
            bot.save()
            return redirect('bots:list')
    else:
        form = BotForm()
    return render(request, 'bots/create.html', {'form': form})

from django.shortcuts import render
from .models import Bot

def bot_list(request):
    bots = Bot.objects.filter(workspace=request.user.workspace)
    return render(request, 'bots/list.html', {'bots': bots})

def edit(request, bot_id):
    bot = Bot.objects.get(id=bot_id, workspace=request.user.workspace)
    if request.method == 'POST':
        form = BotForm(request.POST, instance=bot)
        if form.is_valid():
            if form.cleaned_data['ai_api_key']:
                bot.ai_api_key = form.cleaned_data['ai_api_key']
            form.save()
            return redirect('bots:list')
    else:
        form = BotForm(instance=bot)
    return render(request, 'bots/edit.html', {'form': form, 'bot': bot})