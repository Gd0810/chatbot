# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils import timezone

from accounts.models import Workspace
from billing.models import Plan
from bots.models import Bot
from knowledge.models import KnowledgeSource
from chat.models import Conversation, Message
from .website_crawler import crawl_site

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
        messages.error(request, "Access denied. Your workspace is not active or approved.")
        return redirect('accounts:not_allowed')
    messages.success(request, "Welcome to your dashboard!")
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
    
    messages.info(request, "Processing bot status change...")
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    bot.is_enabled = not bot.is_enabled
    bot.save()
    messages.success(request, f"Bot '{bot.name}' has been successfully {'enabled' if bot.is_enabled else 'disabled'}!")
    # Return the refreshed bots panel (HTMX)
    bots = Bot.objects.filter(workspace=ws).order_by('-id')
    plan = ws.active_plan
    return render(request, 'dashboard/partials/bots.html', {
        'workspace': ws, 'bots': bots, 'plan': plan
    })

# dashboard/views.py (updated bot_edit view)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from bots.models import Bot

# assumes you already have _require_operational helper

@login_required
def bot_edit(request, bot_id):
    ws, bounce = _require_operational(request)
    if bounce:
        return bounce

    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    plan = ws.active_plan

    # Pull choices for dropdown from model field
    ai_providers = list(Bot._meta.get_field('ai_provider').choices)
    available_bot_modes = ws.get_available_bot_modes() if ws else []  # [(value, label), ...]

    if request.method == 'POST':
        messages.info(request, "Processing bot update request...")

        name = (request.POST.get('name') or '').strip()
        if name:
            bot.name = name
        # Handle default_bot_mode (only for multi-bot plans)
        if len(available_bot_modes) > 1:
            default_bot_mode = request.POST.get('default_bot_mode', '').strip()
            if default_bot_mode in available_bot_modes:
                ws.default_bot_mode = default_bot_mode
            elif default_bot_mode == '':  # Empty means auto
                ws.default_bot_mode = None
            ws.save()
        if plan and plan.includes_ai:
            # Validate provider against choices
            selected_provider = request.POST.get('ai_provider') or bot.ai_provider
            valid_values = {v for v, _ in ai_providers}
            if selected_provider and selected_provider not in valid_values:
                messages.error(request, "Invalid AI provider selected.")
                return render(request, 'dashboard/partials/bot_edit.html', {
                    'bot': bot, 'plan': plan, 'ai_providers': ai_providers,
                    'available_bot_modes': available_bot_modes,
                })

            bot.ai_provider = selected_provider or bot.ai_provider
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
            messages.success(request, f"Bot '{bot.name}' has been successfully updated!")

            # If HTMX request, return refreshed bots list; else redirect
            if request.headers.get('HX-Request'):
                bots = Bot.objects.filter(workspace=ws).order_by('-id')
                return render(request, 'dashboard/partials/bots.html', {
                    'workspace': ws,
                    'bots': bots,
                    'plan': ws.active_plan,
                })
            return redirect('dashboard:partial_bots')
        except Exception as e:
            messages.error(request, f"Failed to update bot: {e}. Please check your input and try again.")

    return render(request, 'dashboard/partials/bot_edit.html', {
        'bot': bot, 'plan': plan, 'ai_providers': ai_providers,
        'available_bot_modes': available_bot_modes,
    })

# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest
from django.utils import timezone

import json

from accounts.models import Workspace
from bots.models import Bot
from knowledge.models import KnowledgeSource, Chunk


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
def knowledge_page(request):
    ws, bounce = _require_operational(request)
    if bounce:
        return bounce
    return render(request, 'dashboard/knowledge.html', {'workspace': ws})


@login_required
def partial_knowledge(request):
    ws, bounce = _require_operational(request)
    if bounce:
        return bounce
    plan = ws.active_plan
    bots = Bot.objects.filter(workspace=ws, is_enabled=True).order_by('name')
    sources = KnowledgeSource.objects.filter(bot__workspace=ws).select_related('bot').order_by('-created_at')
    return render(request, 'dashboard/partials/knowledge.html', {
        'workspace': ws, 'plan': plan, 'bots': bots, 'sources': sources
    })


@login_required
def knowledge_add(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")

    ws, bounce = _require_operational(request)
    if bounce:
        return bounce

    plan = ws.active_plan
    if not plan or (not plan.includes_ai and not plan.includes_qa):
        messages.error(request, "Cannot add knowledge: Your current plan does not include AI or Q&A features. Please upgrade your plan.")
        return redirect('dashboard:knowledge_page')

    bot_id = request.POST.get('bot_id')
    source_type = request.POST.get('source_type')
    content = (request.POST.get('content') or '').strip()
    title = (request.POST.get('title') or '').strip()
    qdrant_url = (request.POST.get('qdrant_url') or '').strip()
    qdrant_api_key = (request.POST.get('qdrant_api_key') or '').strip()

    if source_type == 'JSON':
        try:
            json.loads(content or '')
        except Exception as e:
            messages.error(request, f"Invalid JSON content: {e}")
            if request.headers.get('HX-Request'):
                return partial_knowledge(request)
            return redirect('dashboard:knowledge_page')

    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)

    ks = KnowledgeSource(bot=bot, source_type=source_type, content=content, title=title or None)
    try:
        ks.full_clean()
        ks.save()

        if qdrant_url and qdrant_api_key:
            for ch in ks.chunks.all():
                ch.qdrant_url = qdrant_url
                ch.qdrant_api_key = qdrant_api_key
                ch.push_to_qdrant()

        messages.success(request, "Knowledge saved.")
    except Exception as e:
        messages.error(request, f"Failed to save knowledge: {e}")

    if request.headers.get('HX-Request'):
        return partial_knowledge(request)
    return redirect('dashboard:knowledge_page')


@login_required
def knowledge_edit_form(request, source_id):
    ws, bounce = _require_operational(request)
    if bounce:
        return bounce
    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)

    first_chunk = ks.chunks.order_by('id').first()
    initial_qdrant_url = first_chunk.qdrant_url if first_chunk else ''
    initial_qdrant_api_key = first_chunk.qdrant_api_key if first_chunk else ''

    return render(request, 'dashboard/partials/knowledge_edit.html', {
        'workspace': ws, 'ks': ks,
        'qdrant_url': initial_qdrant_url,
        'qdrant_api_key': initial_qdrant_api_key,
    })


@login_required
def knowledge_update(request, source_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")

    ws, bounce = _require_operational(request)
    if bounce:
        return bounce

    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)

    ks.title = request.POST.get('title', ks.title)
    ks.source_type = request.POST.get('source_type') or ks.source_type
    ks.content = request.POST.get('content', ks.content)

    qdrant_url = (request.POST.get('qdrant_url') or '').strip()
    qdrant_api_key = (request.POST.get('qdrant_api_key') or '').strip()

    if ks.source_type == 'JSON':
        try:
            json.loads(ks.content or '')
        except Exception as e:
            messages.error(request, f"Invalid JSON content: {e}")
            if request.headers.get('HX-Request'):
                return knowledge_edit_form(request, source_id)
            return redirect('dashboard:knowledge_page')

    try:
        ks.full_clean()
        ks.save()

        if qdrant_url and qdrant_api_key:
            for ch in ks.chunks.all():
                ch.qdrant_url = qdrant_url
                ch.qdrant_api_key = qdrant_api_key
                ch.push_to_qdrant()

        messages.success(request, "Knowledge updated.")
    except Exception as e:
        messages.error(request, f"Failed to update knowledge: {e}")

    if request.headers.get('HX-Request'):
        return partial_knowledge(request)
    return redirect('dashboard:knowledge_page')


@login_required
def knowledge_delete(request, source_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")

    ws, bounce = _require_operational(request)
    if bounce:
        return bounce

    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)
    try:
        ks.delete()
        messages.success(request, "Knowledge deleted.")
    except Exception as e:
        messages.error(request, f"Failed to delete knowledge: {e}")

    if request.headers.get('HX-Request'):
        return partial_knowledge(request)
    return redirect('dashboard:knowledge_page')


@login_required
def chunks_list(request, source_id):
    ws, bounce = _require_operational(request)
    if bounce:
        return bounce
    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)
    chunks = ks.chunks.order_by('id')
    return render(request, 'dashboard/partials/chunks.html', {
        'workspace': ws, 'ks': ks, 'chunks': chunks,
    })


@login_required
def chunk_edit_form(request, source_id, chunk_id):
    ws, bounce = _require_operational(request)
    if bounce:
        return bounce
    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)
    ch = get_object_or_404(Chunk, id=chunk_id, knowledge_source=ks)
    return render(request, 'dashboard/partials/chunk_edit.html', {
        'workspace': ws, 'ks': ks, 'chunk': ch
    })


@login_required
def chunk_update(request, source_id, chunk_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")

    ws, bounce = _require_operational(request)
    if bounce:
        return bounce

    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)
    ch = get_object_or_404(Chunk, id=chunk_id, knowledge_source=ks)

    new_text = (request.POST.get('text') or '').strip()
    qdrant_url = (request.POST.get('qdrant_url') or '').strip()
    qdrant_api_key = (request.POST.get('qdrant_api_key') or '').strip()

    try:
        if new_text and new_text != ch.text:
            ch.text = new_text
            ch.embedding = None  # triggers re-embed on save()

        if qdrant_url:
            ch.qdrant_url = qdrant_url
        if qdrant_api_key:
            ch.qdrant_api_key = qdrant_api_key

        ch.save()

        if ch.qdrant_url and ch.qdrant_api_key:
            ch.push_to_qdrant()

        messages.success(request, "Chunk updated.")
    except Exception as e:
        messages.error(request, f"Failed to update chunk: {e}")

    return chunks_list(request, source_id)


@login_required
def chunk_delete(request, source_id, chunk_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")

    ws, bounce = _require_operational(request)
    if bounce:
        return bounce

    ks = get_object_or_404(KnowledgeSource, id=source_id, bot__workspace=ws)
    ch = get_object_or_404(Chunk, id=chunk_id, knowledge_source=ks)
    try:
        ch.delete()
        messages.success(request, "Chunk has been successfully deleted!")
    except Exception as e:
        messages.error(request, f"Failed to delete chunk: {e}. Please try again or contact support if the issue persists.")
        
        
        
        
# dashboard/views.py (Bot Styling views)
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseBadRequest

from accounts.models import Workspace
from bots.models import Bot

def _get_user_workspace(user):
    return Workspace.objects.filter(owner=user).order_by('-created_at').first()

def _require_operational(request):
    ws = _get_user_workspace(request.user)
    if not ws or not ws.approved or not ws.is_operational:
        messages.error(request, "Workspace not active.")
        from django.shortcuts import redirect
        return ws, redirect('accounts:not_allowed')
    return ws, None

@login_required
def partial_bot_style(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bots = Bot.objects.filter(workspace=ws).order_by('name')
    return render(request, 'dashboard/partials/bot_style_list.html', {'workspace': ws, 'bots': bots})

@login_required
def bot_style_edit(request, bot_id):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    fonts = [
        ("Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", "Inter / System"),
        ("Segoe UI, Tahoma, Geneva, Verdana, sans-serif", "Segoe UI"),
        ("Roboto, Arial, sans-serif", "Roboto"),
        ("Poppins, Arial, sans-serif", "Poppins"),
        ("Arial, Helvetica, sans-serif", "Arial"),
        ("Georgia, serif", "Georgia"),
        ("'Times New Roman', Times, serif", "Times New Roman"),
        ("'Courier New', Courier, monospace", "Courier New"),
        ("monospace", "Monospace"),
    ]
    return render(request, 'dashboard/partials/bot_style_edit.html', {
        'bot': bot, 'fonts': fonts
    })

@login_required
def bot_style_save(request, bot_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)

    # Collect fields
    bot.ui_primary_color = (request.POST.get('ui_primary_color') or bot.ui_primary_color).strip()
    # Save reset button setting to workspace
    ws.enable_reset_button = True if request.POST.get('enable_reset_button') == '1' else False
    ws.save()
    bot.ui_bg_color = (request.POST.get('ui_bg_color') or getattr(bot, 'ui_bg_color', '#1E1E2E')).strip()
    bot.ui_font_family = (request.POST.get('ui_font_family') or bot.ui_font_family).strip()
    try:
        size_val = int(request.POST.get('ui_font_size') or bot.ui_font_size)
        bot.ui_font_size = max(12, min(20, size_val))
    except Exception:
        pass
    bot.ui_welcome_message = (request.POST.get('ui_welcome_message') or bot.ui_welcome_message).strip()
    bot.ui_sound_enabled = True if request.POST.get('ui_sound_enabled') == 'on' else False

    pos = (request.POST.get('ui_widget_position') or getattr(bot, 'ui_widget_position', 'bottom-right')).strip().lower()
    if pos not in ('bottom-right','bottom-left'):
        pos = 'bottom-right'
    bot.ui_widget_position = pos

    spd = (request.POST.get('ui_animation_speed') or getattr(bot, 'ui_animation_speed', 'normal')).strip().lower()
    if spd not in ('fast','normal','slow') and not (spd.endswith('ms') or spd.endswith('s')):
        spd = 'normal'
    bot.ui_animation_speed = spd

    try:
        bot.full_clean()
        bot.save()
        messages.success(request, "Bot styling updated.")
    except Exception as e:
        messages.error(request, f"Failed to save styling: {e}")

    bots = Bot.objects.filter(workspace=ws).order_by('name')
    return render(request, 'dashboard/partials/bot_style_list.html', {'workspace': ws, 'bots': bots})


@login_required
def partial_enquiries(request):
    """Display all enquiry form submissions for the workspace with pagination."""
    from bots.models import BotEnquiry
    from django.core.paginator import Paginator
    
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    # Handle POST to toggle enquiry form
    if request.method == 'POST':
        enable_form = request.POST.get('enable_enquiry_form') == '1'
        ws.enable_enquiry_form = enable_form
        try:
            ws.save()
            messages.success(request, f"Enquiry form {('enabled' if enable_form else 'disabled')}.")
        except Exception as e:
            messages.error(request, f"Failed to update setting: {e}")
    
    # Get all enquiries for this workspace
    all_enquiries = BotEnquiry.objects.filter(workspace=ws).order_by('-created_at')
    
    # Pagination - 10 items per page
    paginator = Paginator(all_enquiries, 10)
    page_num = request.GET.get('page', 1)
    
    try:
        page_num = int(page_num)
    except (ValueError, TypeError):
        page_num = 1
    
    page_obj = paginator.get_page(page_num)
    enquiries = page_obj.object_list
    
    return render(request, 'dashboard/partials/enquiries.html', {
        'workspace': ws,
        'enquiries': enquiries,
        'page_obj': page_obj,
        'enquiry_count': all_enquiries.count()
    })

@login_required
def live_chat_list(request):
    """List all live chat conversations for the workspace"""
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    # Get all conversations for this workspace's bots
    conversations = Conversation.objects.filter(bot__workspace=ws).order_by('-created_at')
    
    return render(request, 'dashboard/partials/live_list.html', {
        'workspace': ws,
        'conversations': conversations
    })
@login_required
def live_chat_detail(request, conversation_id):
    """Show detailed view of a specific conversation"""
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    messages_list = Message.objects.filter(conversation=conversation).order_by('timestamp')
    
    return render(request, 'dashboard/partials/live_detail.html', {
        'workspace': ws,
        'conversation': conversation,
        'messages': messages_list
    })
@login_required
def live_chat_messages(request, conversation_id):
    """Get messages for a conversation (used for HTMX updates)"""
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    messages_list = Message.objects.filter(conversation=conversation).order_by('timestamp')
    
    return render(request, 'dashboard/partials/live_messages.html', {
        'workspace': ws,
        'conversation': conversation,
        'messages': messages_list
    })
@login_required
def live_chat_reply(request, conversation_id):
    """Send a reply to a conversation"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    text = request.POST.get('text', '').strip()
    
    if text:
        Message.objects.create(
            conversation=conversation,
            sender='BOT',
            text=text
        )
        # Switch to LIVE mode if replying manually
        if conversation.effective_mode != 'LIVE':
            conversation.effective_mode = 'LIVE'
            conversation.save()
            
    return live_chat_messages(request, conversation_id)    
    
@login_required
def live_chat_delete(request, conversation_id):
    """Delete a live chat conversation"""
    if request.method != 'DELETE':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce

def _require_operational(request):
    ws = _get_user_workspace(request.user)
    if not ws or not ws.approved or not ws.is_operational:
        messages.error(request, "Workspace not active.")
        from django.shortcuts import redirect
        return ws, redirect('accounts:not_allowed')
    return ws, None

@login_required
def partial_bot_style(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bots = Bot.objects.filter(workspace=ws).order_by('name')
    return render(request, 'dashboard/partials/bot_style_list.html', {'workspace': ws, 'bots': bots})

@login_required
def bot_style_edit(request, bot_id):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    fonts = [
        ("Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif", "Inter / System"),
        ("Segoe UI, Tahoma, Geneva, Verdana, sans-serif", "Segoe UI"),
        ("Roboto, Arial, sans-serif", "Roboto"),
        ("Poppins, Arial, sans-serif", "Poppins"),
        ("Arial, Helvetica, sans-serif", "Arial"),
        ("Georgia, serif", "Georgia"),
        ("'Times New Roman', Times, serif", "Times New Roman"),
        ("'Courier New', Courier, monospace", "Courier New"),
        ("monospace", "Monospace"),
    ]
    return render(request, 'dashboard/partials/bot_style_edit.html', {
        'bot': bot, 'fonts': fonts
    })

@login_required
def bot_style_save(request, bot_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)

    # Collect fields
    bot.ui_primary_color = (request.POST.get('ui_primary_color') or bot.ui_primary_color).strip()
    # Save reset button setting to workspace
    ws.enable_reset_button = True if request.POST.get('enable_reset_button') == '1' else False
    # Save WhatsApp settings to workspace
    ws.enable_whatsapp_number_in_chat = True if request.POST.get('enable_whatsapp_number_in_chat') == 'on' else False
    whatsapp_num = (request.POST.get('whatsapp_number') or '').strip()
    ws.whatsapp_number = whatsapp_num if whatsapp_num else None
    ws.save()
    bot.ui_bg_color = (request.POST.get('ui_bg_color') or getattr(bot, 'ui_bg_color', '#1E1E2E')).strip()
    bot.ui_font_family = (request.POST.get('ui_font_family') or bot.ui_font_family).strip()
    try:
        size_val = int(request.POST.get('ui_font_size') or bot.ui_font_size)
        bot.ui_font_size = max(12, min(20, size_val))
    except Exception:
        pass
    bot.ui_welcome_message = (request.POST.get('ui_welcome_message') or bot.ui_welcome_message).strip()
    bot.ui_sound_enabled = True if request.POST.get('ui_sound_enabled') == 'on' else False

    pos = (request.POST.get('ui_widget_position') or getattr(bot, 'ui_widget_position', 'bottom-right')).strip().lower()
    if pos not in ('bottom-right','bottom-left'):
        pos = 'bottom-right'
    bot.ui_widget_position = pos

    spd = (request.POST.get('ui_animation_speed') or getattr(bot, 'ui_animation_speed', 'normal')).strip().lower()
    if spd not in ('fast','normal','slow') and not (spd.endswith('ms') or spd.endswith('s')):
        spd = 'normal'
    bot.ui_animation_speed = spd

    try:
        bot.full_clean()
        bot.save()
        messages.success(request, "Bot styling updated.")
    except Exception as e:
        messages.error(request, f"Failed to save styling: {e}")

    bots = Bot.objects.filter(workspace=ws).order_by('name')
    return render(request, 'dashboard/partials/bot_style_list.html', {'workspace': ws, 'bots': bots})


@login_required
def partial_enquiries(request):
    """Display all enquiry form submissions for the workspace with pagination."""
    from bots.models import BotEnquiry
    from django.core.paginator import Paginator
    
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    # Handle POST to toggle enquiry form
    if request.method == 'POST':
        enable_form = request.POST.get('enable_enquiry_form') == '1'
        ws.enable_enquiry_form = enable_form
        try:
            ws.save()
            messages.success(request, f"Enquiry form {('enabled' if enable_form else 'disabled')}.")
        except Exception as e:
            messages.error(request, f"Failed to update setting: {e}")
    
    # Get all enquiries for this workspace
    all_enquiries = BotEnquiry.objects.filter(workspace=ws).order_by('-created_at')
    
    # Pagination - 10 items per page
    paginator = Paginator(all_enquiries, 10)
    page_num = request.GET.get('page', 1)
    
    try:
        page_num = int(page_num)
    except (ValueError, TypeError):
        page_num = 1
    
    page_obj = paginator.get_page(page_num)
    enquiries = page_obj.object_list
    
    return render(request, 'dashboard/partials/enquiries.html', {
        'workspace': ws,
        'enquiries': enquiries,
        'page_obj': page_obj,
        'enquiry_count': all_enquiries.count()
    })

@login_required
def live_chat_list(request):
    """List all live chat conversations for the workspace"""
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    # Get all conversations for this workspace's bots
    conversations = Conversation.objects.filter(bot__workspace=ws).order_by('-created_at')
    
    return render(request, 'dashboard/partials/live_list.html', {
        'workspace': ws,
        'conversations': conversations
    })
@login_required
def live_chat_detail(request, conversation_id):
    """Show detailed view of a specific conversation"""
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    messages_list = Message.objects.filter(conversation=conversation).order_by('timestamp')
    
    return render(request, 'dashboard/partials/live_detail.html', {
        'workspace': ws,
        'conversation': conversation,
        'messages': messages_list
    })
@login_required
def live_chat_messages(request, conversation_id):
    """Get messages for a conversation (used for HTMX updates)"""
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    messages_list = Message.objects.filter(conversation=conversation).order_by('timestamp')
    
    return render(request, 'dashboard/partials/live_messages.html', {
        'workspace': ws,
        'conversation': conversation,
        'messages': messages_list
    })
@login_required
def live_chat_reply(request, conversation_id):
    """Send a reply to a conversation"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    text = request.POST.get('text', '').strip()
    
    if text:
        Message.objects.create(
            conversation=conversation,
            sender='BOT',
            text=text
        )
        # Switch to LIVE mode if replying manually
        if conversation.effective_mode != 'LIVE':
            conversation.effective_mode = 'LIVE'
            conversation.save()
            
    return live_chat_messages(request, conversation_id)    
    
@login_required
def live_chat_delete(request, conversation_id):
    """Delete a live chat conversation"""
    if request.method != 'DELETE':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    conversation = get_object_or_404(Conversation, id=conversation_id, bot__workspace=ws)
    conversation.delete()
    
    # Return updated conversation list
    return live_chat_list(request)    


# -------------------------------------------------------------------
# QA Management Views
# -------------------------------------------------------------------

@login_required
def partial_qa(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    plan = ws.active_plan
    # Check if plan includes QA
    if not plan or not plan.includes_qa:
        return HttpResponse("QA feature is not available in your current plan.", status=403)

    from knowledge.models import QAPair
    # Fetch all pairs for this workspace's bots
    # We might want to group by bot or just show all
    # For now, let's show all, ordered by bot and hierarchy
    qa_pairs = QAPair.objects.filter(bot__workspace=ws).select_related('bot', 'parent').order_by('bot', 'order', 'created_at')
    
    bots = Bot.objects.filter(workspace=ws, is_enabled=True)
    
    return render(request, 'dashboard/partials/qa_list.html', {
        'workspace': ws,
        'qa_pairs': qa_pairs,
        'bots': bots,
    })

@login_required
def qa_add(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    bot_id = request.POST.get('bot_id')
    question = (request.POST.get('question') or '').strip()
    answer = (request.POST.get('answer') or '').strip()
    parent_id = request.POST.get('parent_id')
    
    if not bot_id or not question:
        messages.error(request, "Bot and Question are required.")
        return partial_qa(request)
        
    bot = get_object_or_404(Bot, id=bot_id, workspace=ws)
    
    from knowledge.models import QAPair
    parent = None
    if parent_id:
        parent = get_object_or_404(QAPair, id=parent_id, bot=bot)
        
    try:
        QAPair.objects.create(
            bot=bot,
            question=question,
            answer=answer,
            parent=parent
        )
        messages.success(request, "Q&A Pair added.")
    except Exception as e:
        messages.error(request, f"Error adding Q&A: {e}")
        
    return partial_qa(request)

@login_required
def qa_edit_form(request, qa_id):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    from knowledge.models import QAPair
    qa = get_object_or_404(QAPair, id=qa_id, bot__workspace=ws)
    
    # Get potential parents (exclude self and children to avoid cycles)
    # Simple cycle prevention: just exclude self for now. 
    # Ideally should exclude subtree.
    potential_parents = QAPair.objects.filter(bot=qa.bot).exclude(id=qa.id)
    
    return render(request, 'dashboard/partials/qa_edit.html', {
        'qa': qa,
        'potential_parents': potential_parents
    })

@login_required
def qa_update(request, qa_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    from knowledge.models import QAPair
    qa = get_object_or_404(QAPair, id=qa_id, bot__workspace=ws)
    
    question = (request.POST.get('question') or '').strip()
    answer = (request.POST.get('answer') or '').strip()
    parent_id = request.POST.get('parent_id')
    
    if not question:
        messages.error(request, "Question is required.")
        return partial_qa(request)
        
    qa.question = question
    qa.answer = answer
    
    if parent_id:
        if int(parent_id) == qa.id:
            messages.error(request, "Cannot be parent of self.")
        else:
            parent = get_object_or_404(QAPair, id=parent_id, bot=qa.bot)
            qa.parent = parent
    else:
        qa.parent = None
        
    try:
        qa.save()
        messages.success(request, "Q&A Pair updated.")
    except Exception as e:
        messages.error(request, f"Error updating Q&A: {e}")
        
    return partial_qa(request)

@login_required
def qa_delete(request, qa_id):
    if request.method != 'DELETE' and request.method != 'POST':
        return HttpResponseBadRequest("Invalid method")
        
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    
    from knowledge.models import QAPair
    qa = get_object_or_404(QAPair, id=qa_id, bot__workspace=ws)
    
    try:
        qa.delete()
        messages.success(request, "Q&A Pair deleted.")
    except Exception as e:
        messages.error(request, f"Error deleting Q&A: {e}")
        
    return partial_qa(request)
@login_required
def partial_website_datafetcher(request):
    ws, bounce = _require_operational(request)
    if bounce: return bounce
    if not ws.enable_website_datafetcher:
        messages.error(request, 'Website data fetcher is not enabled.')
        return redirect('dashboard:index')
    return render(request, 'dashboard/partials/website_datafetcher.html', {'workspace': ws})

@login_required
def website_datafetcher_crawl(request):
    ws, bounce = _require_operational(request)
    if bounce: return JsonResponse({'error': 'Unauthorized'}, status=403)
    if not ws.enable_website_datafetcher:
        return JsonResponse({'error': 'Feature not enabled'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        url = request.POST.get('url', '').strip()
        max_pages = int(request.POST.get('max_pages', 30))
        if not url:
            return JsonResponse({'error': 'URL is required'}, status=400)
        if not url.startswith(('http://', 'https://')):
            return JsonResponse({'error': 'URL must start with http:// or https://'}, status=400)
        max_pages = min(max(1, max_pages), 100)
        from .website_crawler import crawl_site
        results = crawl_site(url, max_pages=max_pages)
        
        return render(request, 'dashboard/partials/website_crawl_results.html', {
            'success': True,
            'pages': results, 
            'total': len(results)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
