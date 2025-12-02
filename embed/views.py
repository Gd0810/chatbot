# embed/views.py (update: include jwt_exp in cfg and pre-render welcome_text)
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt

import jwt
from datetime import timedelta, datetime, timezone as dt_timezone
from urllib.parse import urlparse
import json

from bots.models import Bot
from chat.models import Conversation, Message
from chat.views import get_relevant_data
from chat.services import get_ai_response


def _host_from_url(url: str) -> str:
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def _is_local_host(host: str) -> bool:
    return host in ('localhost', '127.0.0.1')


@xframe_options_exempt
def widget_iframe(request, public_key):
    try:
        bot = Bot.objects.get(public_key=public_key)
        ws = bot.workspace

        # Check if plan includes Live Chat. If so, serve the live widget instead.
        # This ensures persistent chat history and dashboard visibility.
        ap = ws.active_plan
        if ap and ap.includes_live:
             return live_widget_iframe(request, public_key)
        
        # Check if plan is QA_ONLY or preferred_mode is QA
        if ap and (ap.bundle == 'QA_ONLY' or bot.preferred_mode == 'QA'):
             return qa_widget_iframe(request, public_key)

        origin = request.GET.get('origin', '') or ''
        origin_host = _host_from_url(origin)
        request_host = (request.get_host().split(':')[0] or '').lower()

        # Domain allowance
        allowed = False
        allowed_by = None
        if origin and bot.is_origin_allowed(origin):
            allowed = True; allowed_by = 'allowed_domains'
        elif origin_host and origin_host == request_host:
            allowed = True; allowed_by = 'same_origin'
        elif settings.DEBUG and origin_host and _is_local_host(origin_host):
            allowed = True; allowed_by = 'debug_local'
        elif settings.DEBUG and not origin:
            allowed = True; allowed_by = 'debug_no_origin'

        # Block reasons
        block_reason = None
        block_msg = None
        if not allowed:
            block_reason = 'domain'
            block_msg = "This domain is not allowed for this bot."
        elif not bot.is_enabled:
            block_reason = 'disabled'
            block_msg = "This bot is disabled by the owner."
        elif not ws.approved:
            block_reason = 'not_approved'
            block_msg = "Workspace is not approved yet."
        elif not ws.is_operational:
            if ap and ap.term == 'LIMITED' and ap.end_at and timezone.now() > ap.end_at:
                block_reason = 'out_of_plan'
                block_msg = "You’re out of plan."
            else:
                block_reason = 'inactive'
                block_msg = "Workspace is not active."

        # Token
        token = None
        exp_ts = None
        if block_reason is None:
            now = datetime.now(dt_timezone.utc)
            exp = now + timedelta(minutes=30)  # 30 min TTL
            payload = {
                'bot_id': bot.id,
                'public_key': public_key,
                'iat': int(now.timestamp()),
                'nbf': int((now - timedelta(seconds=5)).timestamp()),
                'exp': int(exp.timestamp()),
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            exp_ts = payload['exp']

        # Debug for page and server
        debug = {
            'origin': origin,
            'origin_host': origin_host,
            'request_host': request_host,
            'allowed': allowed,
            'allowed_by': allowed_by,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'bot_is_enabled': bot.is_enabled,
            'ws_approved': ws.approved,
            'ws_operational': ws.is_operational,
            'plan_bundle': ap.bundle if ap else None,
            'plan_term': ap.term if ap else None,
            'plan_active_now': ap.is_current_active if ap else None,
            'has_jwt': bool(token),
            'jwt_exp': exp_ts,
            'workspace_enable_reset_button': getattr(ws, 'enable_reset_button', False),
        }
        print(f"[embed.widget] pk={public_key} debug={debug}")

        # Welcome text (no template filter use)
        default_welcome = "Hi! I'm {name}. How can I help you?"
        welcome_raw = bot.ui_welcome_message or default_welcome
        welcome_text = welcome_raw.replace("{name}", bot.name)

        cfg = {
            'jwt': token or '',
            'botId': bot.id,
            'botName': bot.name,
            'publicKey': public_key,
            'origin': origin,
            'jwt_exp': exp_ts,                # pass exp for auto-refresh
            'sound': bot.ui_sound_enabled,    # for sound toggle
            # expose workspace-level UI toggles for client debug/fallback
            'workspace_enable_reset_button': getattr(ws, 'enable_reset_button', False),
        }

        # Bot footer: use workspace setting and first footer for workspace if available
        footer = None
        try:
            if getattr(ws, 'bot_footer', False):
                footer = getattr(ws, 'bot_footers', None)
                if footer is not None:
                    footer = footer.first()
        except Exception:
            footer = None

        # Enquiry form: check if workspace has enabled it
        enquiry_form_enabled = getattr(ws, 'enable_enquiry_form', False)

        # Render + no-cache headers
        response = render(request, 'embed/widget.html', {
            'public_key': public_key,
            'bot': bot,
            'workspace': ws,
            'bot_footer': footer,
            'enquiry_form_enabled': enquiry_form_enabled,
            'jwt': token,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'block_msg': block_msg,
            'origin': origin,
            'welcome_text': welcome_text,
            'cfg': cfg,
            'debug': debug,
            'debug_on': settings.DEBUG,
        })
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    except Bot.DoesNotExist:
        return HttpResponse("Bot not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


@xframe_options_exempt
def live_widget_iframe(request, public_key):
    """
    Serves the live chat widget iframe.
    Similar to widget_iframe but uses embed/live.html and might have different logic.
    """
    try:
        bot = Bot.objects.get(public_key=public_key)
        ws = bot.workspace

        origin = request.GET.get('origin', '') or ''
        origin_host = _host_from_url(origin)
        request_host = (request.get_host().split(':')[0] or '').lower()

        # Domain allowance logic (same as widget_iframe)
        allowed = False
        allowed_by = None
        if origin and bot.is_origin_allowed(origin):
            allowed = True; allowed_by = 'allowed_domains'
        elif origin_host and origin_host == request_host:
            allowed = True; allowed_by = 'same_origin'
        elif settings.DEBUG and origin_host and _is_local_host(origin_host):
            allowed = True; allowed_by = 'debug_local'
        elif settings.DEBUG and not origin:
            allowed = True; allowed_by = 'debug_no_origin'

        # Block reasons
        block_reason = None
        block_msg = None
        if not allowed:
            block_reason = 'domain'
            block_msg = "This domain is not allowed for this bot."
        elif not bot.is_enabled:
            block_reason = 'disabled'
            block_msg = "This bot is disabled by the owner."
        elif not ws.approved:
            block_reason = 'not_approved'
            block_msg = "Workspace is not approved yet."
        elif not ws.is_operational:
            ap = ws.active_plan
            if ap and ap.term == 'LIMITED' and ap.end_at and timezone.now() > ap.end_at:
                block_reason = 'out_of_plan'
                block_msg = "You’re out of plan."
            else:
                block_reason = 'inactive'
                block_msg = "Workspace is not active."

        # Token generation
        token = None
        exp_ts = None
        if block_reason is None:
            now = datetime.now(dt_timezone.utc)
            exp = now + timedelta(minutes=30)
            payload = {
                'bot_id': bot.id,
                'public_key': public_key,
                'iat': int(now.timestamp()),
                'nbf': int((now - timedelta(seconds=5)).timestamp()),
                'exp': int(exp.timestamp()),
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            exp_ts = payload['exp']

        # Debug info
        ap = ws.active_plan
        debug = {
            'origin': origin,
            'allowed': allowed,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'has_jwt': bool(token),
        }

        # Welcome text
        default_welcome = "Hi! I'm {name}. How can I help you?"
        welcome_raw = bot.ui_welcome_message or default_welcome
        welcome_text = welcome_raw.replace("{name}", bot.name)

        cfg = {
            'jwt': token or '',
            'botId': bot.id,
            'botName': bot.name,
            'publicKey': public_key,
            'origin': origin,
            'jwt_exp': exp_ts,
            'sound': bool(bot.ui_sound_enabled),
            'sound_enabled': bool(bot.ui_sound_enabled),
            'workspace_enable_reset_button': getattr(ws, 'enable_reset_button', False),
            'primary_color': bot.ui_primary_color or '',
            'bg_color': bot.ui_bg_color or '',
            'font_family': bot.ui_font_family or '',
            'font_size': bot.ui_font_size or 14,
            'animation_speed': bot.ui_animation_speed or 'normal',
            'widget_position': bot.ui_widget_position or 'bottom-right',
        }

        # Bot footer
        footer = None
        try:
            if getattr(ws, 'bot_footer', False):
                footer = getattr(ws, 'bot_footers', None)
                if footer is not None:
                    footer = footer.first()
        except Exception:
            footer = None

        enquiry_form_enabled = getattr(ws, 'enable_enquiry_form', False)

        response = render(request, 'embed/live.html', {
            'public_key': public_key,
            'bot': bot,
            'workspace': ws,
            'bot_footer': footer,
            'enquiry_form_enabled': enquiry_form_enabled,
            'jwt': token,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'block_msg': block_msg,
            'origin': origin,
            'welcome_text': welcome_text,
            'cfg': cfg,
            'debug': debug,
            'debug_on': settings.DEBUG,
        })
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

    except Bot.DoesNotExist:
        return HttpResponse("Bot not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


@csrf_exempt
def live_chat_send(request):
    """
    API to send a message in live chat.
    Expects JSON: { jwt, session_id, text }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        token = data.get('jwt')
        session_id = data.get('session_id')
        text = data.get('text', '').strip()

        if not token:
            return JsonResponse({'error': 'Missing JWT'}, status=401)
        
        # Decode JWT
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            bot_id = payload.get('bot_id')
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)

        bot = Bot.objects.get(id=bot_id)
        ws = bot.workspace
        ap = ws.active_plan

        # Find or create conversation
        conversation, created = Conversation.objects.get_or_create(
            bot=bot,
            session_id=session_id,
            defaults={'effective_mode': 'AI'} # Default to AI, can be switched
        )

        # Save User Message
        Message.objects.create(
            conversation=conversation,
            sender='USER',
            text=text
        )

        # Trigger AI response if in AI mode and plan includes AI
        if conversation.effective_mode == 'AI' and ap and ap.includes_ai:
            try:
                retrieved_data, source_ids = get_relevant_data(bot, text, top_k=1)
                answer = get_ai_response(
                    user_question=text,
                    retrieved_data=retrieved_data,
                    api_key=bot.ai_api_key,
                    model=bot.ai_model,
                    bot_id=bot.id,
                )
                
                # Save Bot Message
                Message.objects.create(
                    conversation=conversation,
                    sender='BOT',
                    text=answer,
                    sources=json.dumps(source_ids) if source_ids else ''
                )
            except Exception as e:
                print(f"AI generation failed: {e}")
                # Optionally save an error message or fail silently (user just sees no reply)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def live_chat_poll(request):
    """
    API to poll for new messages.
    Expects GET: jwt, session_id, last_id (optional)
    """
    token = request.GET.get('jwt')
    session_id = request.GET.get('session_id')
    last_id = request.GET.get('last_id', 0)

    if not token:
        return JsonResponse({'error': 'Missing JWT'}, status=401)

    try:
        # Decode JWT
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            bot_id = payload.get('bot_id')
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)

        bot = Bot.objects.get(id=bot_id)
        
        try:
            conversation = Conversation.objects.get(bot=bot, session_id=session_id)
        except Conversation.DoesNotExist:
             return JsonResponse({'messages': []})

        messages = Message.objects.filter(
            conversation=conversation,
            id__gt=last_id
        ).order_by('id')

        data = []
        for msg in messages:
            data.append({
                'id': msg.id,
                'sender': msg.sender,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
                'sources': msg.sources
            })

        return JsonResponse({'messages': data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@xframe_options_exempt
def bot_config_api(request, public_key):
    """
    JSON API endpoint that returns bot configuration for embedding.
    Client-side embed script calls this to get all bot settings dynamically.
    URL: /embed/config/<public_key>/ returns JSON with all UI settings
    """
    try:
        bot = Bot.objects.get(public_key=public_key)
        return HttpResponse(
            json.dumps({
                'public_key': bot.public_key,
                'primary_color': bot.ui_primary_color or '',
                'bg_color': bot.ui_bg_color or '',
                'font_family': bot.ui_font_family or '',
                'font_size': bot.ui_font_size or 14,
                'welcome_message': bot.ui_welcome_message or '',
                'sound_enabled': bool(bot.ui_sound_enabled),
                'animation_speed': bot.ui_animation_speed or 'normal',
                'widget_position': bot.ui_widget_position or 'bottom-right',
            }, default=str),
            content_type='application/json'
        )
    except Bot.DoesNotExist:
        return HttpResponse('{"error": "Bot not found"}', status=404, content_type='application/json')
    except Exception as e:
        return HttpResponse(f'{{"error": "{str(e)}"}}', status=500, content_type='application/json')


def test_embed_page(request, public_key=None):
    """
    Serve a minimal test page for the embed.
    User's actual page only needs a placeholder div + 2 lines of script.
    URL: /embed/test/ or /embed/test/<public_key>/
    """
    bot = None
    if public_key:
        try:
            bot = Bot.objects.get(public_key=public_key)
        except Bot.DoesNotExist:
            pass
    if not bot:
        try:
            bot = Bot.objects.first()
        except Exception:
            pass
    
    return render(request, 'embed/test.html', {'bot': bot})


@csrf_exempt
def save_enquiry(request):
    """
    API endpoint to save user enquiry (name/phone/email) from widget.
    Expects POST with: public_key, name, phone, email
    Returns JSON response.
    CSRF is exempted because this is called from an iframe (cross-origin context).
    Security is maintained by validating the bot's public_key exists.
    """
    if request.method != 'POST':
        return HttpResponse('{"error": "Method not allowed"}', status=405, content_type='application/json')
    
    try:
        data = json.loads(request.body)
        public_key = data.get('public_key', '')
        name = (data.get('name') or '').strip()
        phone = (data.get('phone') or '').strip()
        email = (data.get('email') or '').strip()
        
        # Find bot by public key
        bot = Bot.objects.get(public_key=public_key)
        ws = bot.workspace
        
        # Check if enquiry form is enabled for this workspace
        if not getattr(ws, 'enable_enquiry_form', False):
            return HttpResponse('{"error": "Enquiry form is not enabled"}', status=400, content_type='application/json')
        
        # Validation: At least two fields must be filled
        filled_count = 0
        if name: filled_count += 1
        if phone: filled_count += 1
        if email: filled_count += 1
        
        if filled_count >= 2:
            from bots.models import BotEnquiry
            enquiry = BotEnquiry.objects.create(
                workspace=ws,
                name=name or None,
                phone=phone or None,
                email=email or None
            )
            return HttpResponse(
                json.dumps({'success': True, 'enquiry_id': enquiry.id}),
                content_type='application/json'
            )
        else:
            return HttpResponse('{"error": "Please fill at least two fields"}', status=400, content_type='application/json')
    
    except Bot.DoesNotExist:
        return HttpResponse('{"error": "Bot not found"}', status=404, content_type='application/json')
    except Exception as e:
        return HttpResponse(f'{{"error": "{str(e)}"}}', status=500, content_type='application/json')


@xframe_options_exempt
def qa_widget_iframe(request, public_key):
    """
    Serves the QA-only widget iframe.
    """
    try:
        bot = Bot.objects.get(public_key=public_key)
        ws = bot.workspace

        origin = request.GET.get('origin', '') or ''
        origin_host = _host_from_url(origin)
        request_host = (request.get_host().split(':')[0] or '').lower()

        # Domain allowance (reused logic)
        allowed = False
        if origin and bot.is_origin_allowed(origin):
            allowed = True
        elif origin_host and origin_host == request_host:
            allowed = True
        elif settings.DEBUG and origin_host and _is_local_host(origin_host):
            allowed = True
        elif settings.DEBUG and not origin:
            allowed = True

        block_reason = None
        block_msg = None
        if not allowed:
            block_reason = 'domain'
            block_msg = "Domain not allowed."
        elif not bot.is_enabled:
            block_reason = 'disabled'
            block_msg = "Bot disabled."
        elif not ws.approved:
            block_reason = 'not_approved'
            block_msg = "Workspace not approved."
        elif not ws.is_operational:
            block_reason = 'inactive'
            block_msg = "Workspace inactive."

        # Token
        token = None
        if block_reason is None:
            now = datetime.now(dt_timezone.utc)
            exp = now + timedelta(minutes=30)
            payload = {
                'bot_id': bot.id,
                'public_key': public_key,
                'iat': int(now.timestamp()),
                'exp': int(exp.timestamp()),
            }
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')

        # Welcome text
        default_welcome = "Hi! I'm {name}. How can I help you?"
        welcome_raw = bot.ui_welcome_message or default_welcome
        welcome_text = welcome_raw.replace("{name}", bot.name)

        cfg = {
            'jwt': token or '',
            'botId': bot.id,
            'botName': bot.name,
            'publicKey': public_key,
            'origin': origin,
            'sound': bool(bot.ui_sound_enabled),
            'workspace_enable_reset_button': getattr(ws, 'enable_reset_button', False),
            'primary_color': bot.ui_primary_color or '',
            'bg_color': bot.ui_bg_color or '',
            'font_family': bot.ui_font_family or '',
            'font_size': bot.ui_font_size or 14,
            'animation_speed': bot.ui_animation_speed or 'normal',
            'widget_position': bot.ui_widget_position or 'bottom-right',
        }

        footer = None
        try:
            if getattr(ws, 'bot_footer', False):
                footer = getattr(ws, 'bot_footers', None)
                if footer: footer = footer.first()
        except: pass

        enquiry_form_enabled = getattr(ws, 'enable_enquiry_form', False)

        response = render(request, 'embed/qa.html', {
            'public_key': public_key,
            'bot': bot,
            'workspace': ws,
            'bot_footer': footer,
            'enquiry_form_enabled': enquiry_form_enabled,
            'jwt': token,
            'blocked': bool(block_reason),
            'block_reason': block_reason,
            'block_msg': block_msg,
            'origin': origin,
            'welcome_text': welcome_text,
            'cfg': cfg,
            'debug_on': settings.DEBUG,
        })
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    except Bot.DoesNotExist:
        return HttpResponse("Bot not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@csrf_exempt
def qa_data_api(request, public_key):
    """
    Returns JSON of Q&A pairs for the bot.
    Can accept ?parent_id=... to fetch children, or defaults to root.
    """
    try:
        bot = Bot.objects.get(public_key=public_key)
        parent_id = request.GET.get('parent_id')
        
        from knowledge.models import QAPair
        if parent_id:
            pairs = QAPair.objects.filter(bot=bot, parent_id=parent_id).order_by('order', 'created_at')
        else:
            pairs = QAPair.objects.filter(bot=bot, parent__isnull=True).order_by('order', 'created_at')
            
        data = []
        for p in pairs:
            # Check if it has children
            has_children = p.children.exists()
            data.append({
                'id': p.id,
                'question': p.question,
                'answer': p.answer,
                'has_children': has_children
            })
            
        return JsonResponse({'pairs': data})
    except Bot.DoesNotExist:
        return JsonResponse({'error': 'Bot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)